"""
This module is not for public use.

Use the `ElectricalNetwork.from_dgs` method to read a network from a dgs file.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from roseau.load_flow.io.dgs.utils import (
    DGSData,
    FIDCounter,
    dgs_dict_to_df,
    get_id_to_fid_map,
    has_typ_lne,
    has_typ_tr2,
    iter_dgs_values,
    parse_dgs_version,
)
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow_single.io.common import NetworkElements
from roseau.load_flow_single.io.dgs.buses import buses_to_elm_term, elm_term_to_buses
from roseau.load_flow_single.io.dgs.lines import elm_lne_to_lines, lines_to_elm_lne, lp_to_typ_lne, typ_lne_to_lp
from roseau.load_flow_single.io.dgs.loads import elm_lod_all_to_loads, loads_to_elm_lod
from roseau.load_flow_single.io.dgs.pwf import (
    STA_CUBIC_ATTRIBUTES,
    add_sta_cubic_value,
    create_graphic_net,
    create_grid,
    create_study_case,
)
from roseau.load_flow_single.io.dgs.sources import elm_xnet_to_sources, sources_to_elm_xnet
from roseau.load_flow_single.io.dgs.switches import elm_coup_to_switches, switches_to_elm_coup
from roseau.load_flow_single.io.dgs.transformers import (
    elm_tr2_to_transformers,
    tp_to_typ_tr2,
    transformers_to_elm_tr2,
    typ_tr2_to_tp,
)
from roseau.load_flow_single.models import (
    AbstractLoad,
    Bus,
    Line,
    LineParameters,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)

if TYPE_CHECKING:
    from roseau.load_flow_single.network import ElectricalNetwork

logger = logging.getLogger(__name__)


def network_from_dgs(data: Mapping[str, Any], /, use_name_as_id: bool = False) -> NetworkElements:
    """Create the electrical elements from a JSON file in DGS format.

    Args:
        data:
            The dictionary containing the network DGS data.

        use_name_as_id:
            If True, use the name of the elements (the ``loc_name`` field) as their id. Otherwise,
            use the id from the DGS file (the ``FID`` field). Only use if you are sure the names are
            unique. Default is False.

    Returns:
        The elements of the network.
    """
    parse_dgs_version(data)
    index_col = "loc_name" if use_name_as_id else "FID"

    # Create dataframes from JSON file
    # StaCubic is always indexed by its ID
    sta_cubic = dgs_dict_to_df(data, "StaCubic", "FID")  # Cubicles
    # Read the elements of the network, index by FID or loc_name
    elm_term = dgs_dict_to_df(data, "ElmTerm", index_col)  # Terminals (buses)
    typ_lne = dgs_dict_to_df(data, "TypLne", index_col) if "TypLne" in data else None  # Line types
    typ_tr2 = dgs_dict_to_df(data, "TypTr2", index_col) if "TypTr2" in data else None  # Transformer types
    elm_xnet = dgs_dict_to_df(data, "ElmXnet", index_col)  # External sources
    elm_tr = dgs_dict_to_df(data, "ElmTr2", index_col) if "ElmTr2" in data else None  # Transformers
    elm_coup = dgs_dict_to_df(data, "ElmCoup", index_col) if "ElmCoup" in data else None  # Switches
    elm_lne = dgs_dict_to_df(data, "ElmLne", index_col) if "ElmLne" in data else None  # Lines
    elm_lod_lv = dgs_dict_to_df(data, "ElmLodLV", index_col) if "ElmLodLV" in data else None  # LV loads
    elm_lod_mv = dgs_dict_to_df(data, "ElmLodmv", index_col) if "ElmLodmv" in data else None  # MV loads
    elm_lod = dgs_dict_to_df(data, "ElmLod", index_col) if "ElmLod" in data else None  # General loads
    elm_gen_stat = dgs_dict_to_df(data, "ElmGenStat", index_col) if "ElmGenStat" in data else None  # Generators
    elm_pv_sys = dgs_dict_to_df(data, "ElmPvsys", index_col) if "ElmPvsys" in data else None  # LV generators

    # Reindex buses and types by their FID because they are needed elsewhere
    if use_name_as_id:
        elm_term = elm_term.reset_index(drop=False).set_index("FID")
        if typ_lne is not None:
            typ_lne = typ_lne.reset_index(drop=False).set_index("FID")
        if typ_tr2 is not None:
            typ_tr2 = typ_tr2.reset_index(drop=False).set_index("FID")

    # ElectricalNetwork elements
    buses: dict[str, Bus] = {}  # key is the FID
    sources: dict[Id, VoltageSource] = {}
    loads: dict[Id, AbstractLoad] = {}
    lines: dict[Id, Line] = {}
    transformers: dict[Id, Transformer] = {}
    switches: dict[Id, Switch] = {}

    # Buses
    elm_term_to_buses(elm_term=elm_term, buses=buses, use_name_as_id=use_name_as_id)

    # Sources
    elm_xnet_to_sources(elm_xnet=elm_xnet, sources=sources, buses=buses, sta_cubic=sta_cubic)

    # Loads
    if elm_lod is not None:  # General loads
        elm_lod_all_to_loads(
            elm_lod=elm_lod, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e6, load_type="General"
        )
    if elm_lod_mv is not None:  # MV loads
        elm_lod_all_to_loads(
            elm_lod=elm_lod_mv, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e6, load_type="MV"
        )
    if elm_lod_lv is not None:  # LV loads
        elm_lod_all_to_loads(
            elm_lod=elm_lod_lv, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e3, load_type="LV"
        )
    if elm_pv_sys is not None:  # PV systems
        elm_lod_all_to_loads(
            elm_lod=elm_pv_sys, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e3, load_type="PV"
        )
    if elm_gen_stat is not None:  # Static generators
        elm_lod_all_to_loads(
            elm_lod=elm_gen_stat, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e6, load_type="GenStat"
        )

    # Lines
    if elm_lne is not None:
        line_params: dict[str, LineParameters] = {}  # key is the FID
        if has_typ_lne(typ_lne):
            typ_lne_to_lp(typ_lne=typ_lne, line_params=line_params, use_name_as_id=use_name_as_id)
        elm_lne_to_lines(elm_lne=elm_lne, lines=lines, buses=buses, sta_cubic=sta_cubic, line_params=line_params)

    # Transformers
    if elm_tr is not None:
        tr_params: dict[str, TransformerParameters] = {}  # key is the FID
        tr_taps: dict[str, float] = {}  # key is the type's FID
        if has_typ_tr2(typ_tr2):
            typ_tr2_to_tp(typ_tr=typ_tr2, tr_params=tr_params, tr_taps=tr_taps, use_name_as_id=use_name_as_id)
        elm_tr2_to_transformers(
            elm_tr=elm_tr,
            transformers=transformers,
            buses=buses,
            sta_cubic=sta_cubic,
            tr_taps=tr_taps,
            tr_params=tr_params,
        )

    # Switches
    if elm_coup is not None:
        elm_coup_to_switches(elm_coup=elm_coup, switches=switches, buses=buses, sta_cubic=sta_cubic)

    return {
        "buses": {bus.id: bus for bus in buses.values()},
        "lines": lines,
        "transformers": transformers,
        "switches": switches,
        "loads": loads,
        "sources": sources,
        "crs": None,  # TODO check if the CRS can be stored in the DGS file
    }


def network_to_dgs(en: "ElectricalNetwork") -> JsonDict:
    fid_counter = FIDCounter()
    general: JsonDict = {
        "Attributes": ["FID", "Descr", "Val"],
        "Values": [[next(fid_counter), "Version", "7.0"]],
    }

    # PowerFactory data
    int_case = create_study_case(fid_counter)
    int_grf_net = create_graphic_net(fid_counter)
    grf_net_fid: str = next(iter_dgs_values(int_grf_net, "FID"))
    elm_net = create_grid(fid_counter, grf_net_fid)
    net_fid: str = next(iter_dgs_values(elm_net, "FID"))

    # Buses
    elm_term = buses_to_elm_term(en.buses.values(), fid_counter=fid_counter, fold_id=net_fid)
    term_fid_by_id = get_id_to_fid_map(elm_term)

    # Types
    ln_params: list[LineParameters] = []
    ln_params_uns: list[set[float]] = []
    tr_params: list[TransformerParameters] = []
    for ln in en.lines.values():
        un = (
            ln.bus1.nominal_voltage.m_as("kV")
            if ln.bus1.nominal_voltage is not None
            else ln.bus2.nominal_voltage.m_as("kV")
            if ln.bus2.nominal_voltage is not None
            else None
        )
        if ln.parameters in ln_params:
            if un is not None:
                idx = ln_params.index(ln.parameters)
                ln_params_uns[idx].add(un)
        else:
            ln_params.append(ln.parameters)
            uns = {un} if un is not None else set()
            ln_params_uns.append(uns)
    for tr in en.transformers.values():
        if tr.parameters in tr_params:
            continue
        tr_params.append(tr.parameters)
    typ_lne = lp_to_typ_lne(ln_params, ln_params_uns, fid_counter)
    typ_tr2 = tp_to_typ_tr2(tr_params, fid_counter)

    # Elements and their static cubics (order matters)
    sta_cubic: DGSData = {"Attributes": STA_CUBIC_ATTRIBUTES[:], "Values": []}
    lne_sta_cubic = {
        ln.id: (
            add_sta_cubic_value(term_fid_by_id[ln.bus1.id], 0, "abc", fid_counter, sta_cubic),
            add_sta_cubic_value(term_fid_by_id[ln.bus2.id], 1, "abc", fid_counter, sta_cubic),
        )
        for ln in en.lines.values()
    }
    tr2_sta_cubic = {
        tr.id: (
            add_sta_cubic_value(term_fid_by_id[tr.bus_hv.id], 0, "abc", fid_counter, sta_cubic),
            add_sta_cubic_value(term_fid_by_id[tr.bus_lv.id], 1, "abc", fid_counter, sta_cubic),
        )
        for tr in en.transformers.values()
    }
    coup_sta_cubic = {
        sw.id: (
            add_sta_cubic_value(term_fid_by_id[sw.bus1.id], 0, "abc", fid_counter, sta_cubic),
            add_sta_cubic_value(term_fid_by_id[sw.bus2.id], 1, "abc", fid_counter, sta_cubic),
        )
        for sw in en.switches.values()
    }
    xnet_sta_cubic = {
        src.id: add_sta_cubic_value(term_fid_by_id[src.bus.id], 0, "abc", fid_counter, sta_cubic)
        for src in en.sources.values()
    }
    lod_sta_cubic = {
        ld.id: add_sta_cubic_value(term_fid_by_id[ld.bus.id], 0, "abc", fid_counter, sta_cubic)
        for ld in en.loads.values()
    }

    elm_lne = lines_to_elm_lne(
        en.lines.values(), typ_lne, fid_counter=fid_counter, sta_cubic=lne_sta_cubic, fold_id=net_fid
    )
    elm_tr2 = transformers_to_elm_tr2(
        en.transformers.values(), typ_tr2, fid_counter=fid_counter, sta_cubic=tr2_sta_cubic, fold_id=net_fid
    )
    elm_coup = switches_to_elm_coup(en.switches.values(), fid_counter=fid_counter, sta_cubic=coup_sta_cubic)
    elm_xnet = sources_to_elm_xnet(
        en.sources.values(), fid_counter=fid_counter, sta_cubic=xnet_sta_cubic, fold_id=net_fid
    )
    elm_lod = loads_to_elm_lod(en.loads.values(), fid_counter=fid_counter, sta_cubic=lod_sta_cubic)

    return {
        "General": general,
        "IntCase": int_case,
        "IntGrfnet": int_grf_net,
        "ElmNet": elm_net,
        "TypLne": typ_lne,
        "TypTr2": typ_tr2,
        "ElmTerm": elm_term,
        "StaCubic": sta_cubic,
        "ElmLne": elm_lne,
        "ElmCoup": elm_coup,
        "ElmTr2": elm_tr2,
        "ElmXnet": elm_xnet,
        "ElmLod": elm_lod,
        # TODO check if the CRS can be stored in the DGS file
    }
