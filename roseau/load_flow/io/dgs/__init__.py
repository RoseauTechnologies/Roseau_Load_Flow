"""
This module is not for public use.

Use the `ElectricalNetwork.from_dgs_file` method to read a network from a dgs file.
"""

import logging
from collections.abc import Iterable, Mapping
from itertools import chain, islice
from typing import Any

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.common import NetworkElements
from roseau.load_flow.io.dgs.buses import elm_term_to_buses
from roseau.load_flow.io.dgs.lines import elm_lne_to_lines, typ_lne_to_lp
from roseau.load_flow.io.dgs.loads import elm_lod_all_to_loads
from roseau.load_flow.io.dgs.sources import elm_xnet_to_sources
from roseau.load_flow.io.dgs.switches import elm_coup_to_switches
from roseau.load_flow.io.dgs.transformers import elm_tr2_to_transformers, typ_tr2_to_tp
from roseau.load_flow.io.dgs.utils import dgs_dict_to_df, has_typ_lne, has_typ_tr2, parse_dgs_version
from roseau.load_flow.models import (
    AbstractLoad,
    Bus,
    Element,
    Ground,
    GroundConnection,
    Line,
    LineParameters,
    PotentialRef,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def network_from_dgs(data: Mapping[str, Any], /, use_name_as_id: bool = False) -> NetworkElements:
    """Create the electrical elements from a JSON file in DGS format.

    Args:
        filename:
            Name of the JSON file.

        use_name_as_id:
            If True, use the name of the elements (the ``loc_name`` field) as their id. Otherwise,
            use the id from the DGS file (the ``FID`` field). Only use if you are sure the names are
            unique. Default is False.

    Returns:
        The elements of the network.
    """
    # Create dataframes from JSON file
    parse_dgs_version(data)

    index_col = "loc_name" if use_name_as_id else "FID"

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
    grounds: dict[Id, Ground] = {}
    potential_refs: dict[Id, PotentialRef] = {}
    ground_connections: dict[Id, GroundConnection] = {}

    # Ground and potential reference
    ground = Ground("ground")
    p_ref = PotentialRef(id="pref (ground)", element=ground)

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
        elm_lne_to_lines(
            elm_lne=elm_lne, lines=lines, buses=buses, sta_cubic=sta_cubic, line_params=line_params, ground=ground
        )

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

    _add_potential_refs_and_ground_connections(
        buses=buses.values(),
        lines=lines.values(),
        transformers=transformers.values(),
        switches=switches.values(),
        sources=sources,
        potential_refs=potential_refs,
        ground_connections=ground_connections,
        ground=ground,
    )

    if len(ground._connected_elements) > 1:  # Is the ground used? (Are there connected elements aside from pref)
        grounds[ground.id] = ground
        potential_refs[p_ref.id] = p_ref

    return {
        "buses": {bus.id: bus for bus in buses.values()},
        "lines": lines,
        "transformers": transformers,
        "switches": switches,
        "loads": loads,
        "sources": sources,
        "grounds": grounds,
        "potential_refs": potential_refs,
        "ground_connections": ground_connections,
        "crs": None,  # TODO check if the CRS can be stored in the DGS file
    }


def _add_potential_refs_and_ground_connections(  # noqa: C901
    buses: Iterable[Bus],
    lines: Iterable[Line],
    transformers: Iterable[Transformer],
    switches: Iterable[Switch],
    sources: dict[Id, VoltageSource],
    potential_refs: dict[Id, PotentialRef],
    ground_connections: dict[Id, GroundConnection],
    ground: Ground,
) -> None:
    """Add potential reference(s) to a DGS network."""
    # Note this function is adapted from the ElectricalNetwork._check_ref method
    elements = chain(buses, lines, transformers, switches)
    visited_elements: set[Element] = set()
    for initial_element in elements:
        if initial_element in visited_elements:
            continue
        if isinstance(initial_element, Transformer):
            continue
        visited_elements.add(initial_element)
        connected_component: set[Element] = set()
        has_potential_ref = False
        transformer = None
        to_visit: list[Element] = [initial_element]
        while to_visit:
            element = to_visit.pop(-1)
            connected_component.add(element)
            if isinstance(element, PotentialRef):
                has_potential_ref = True
            for connected_element in element._connected_elements:
                if isinstance(connected_element, Transformer):
                    transformer = connected_element
                elif connected_element not in visited_elements:
                    to_visit.append(connected_element)
                    visited_elements.add(connected_element)

        if not has_potential_ref:
            # This subnetwork does not have a potential reference, create a new one
            for vs in sources.values():
                # First: prefer creating the reference at a source (if any)
                if vs.bus in connected_component:
                    if "n" in vs.bus._phases:
                        gc = GroundConnection(id=f"gc (source {vs.id!r})", element=vs.bus, ground=ground)
                        ground_connections[gc.id] = gc
                    else:
                        pref = PotentialRef(id=f"pref (source {vs.id!r})", element=vs.bus)
                        potential_refs[pref.id] = pref
                    has_potential_ref = True
                    break
            else:
                # No sources in this subnetwork
                for element in connected_component:
                    # Second: prefer connecting a bus with neutral to the ground (if any)
                    if not isinstance(element, Bus):
                        continue
                    if "n" in element._phases:
                        gc = GroundConnection(id=f"gc (bus {element.id!r})", element=element, ground=ground)
                        ground_connections[gc.id] = gc
                        has_potential_ref = True
                        break
                else:
                    # No buses with neutral
                    if transformer is not None:
                        # Third: prefer creating the reference at a transformer bus (if any)
                        transformer_bus = (
                            transformer.bus2 if transformer.bus2 in connected_component else transformer.bus1
                        )
                        assert transformer_bus in connected_component
                        if "n" in transformer_bus._phases:
                            gc = GroundConnection(
                                id=f"gc (transformer {transformer.id!r})", element=transformer_bus, ground=ground
                            )
                            ground_connections[gc.id] = gc
                        else:
                            pref = PotentialRef(id=f"pref (transformer {transformer.id!r})", element=transformer_bus)
                            potential_refs[pref.id] = pref
                        has_potential_ref = True
                    else:
                        # Fourth: create the reference at the first bus in the subnetwork
                        first_bus = next(
                            element
                            for element in sorted(connected_component, key=lambda e: str(e.id))
                            if isinstance(element, Bus)
                        )
                        pref = PotentialRef(id=f"pref (bus {first_bus.id!r})", element=first_bus)
                        potential_refs[pref.id] = pref
                        has_potential_ref = True
        # At this point we have a potential ref, do a sanity check with clear error message
        if not has_potential_ref:
            buses_without_pref = list(islice((e.id for e in connected_component if isinstance(e, Bus)), 10))
            msg = (
                f"Internal error: failed to assign a potential reference to elements connected to "
                f"buses {buses_without_pref}. Please open an issue on GitHub."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE)
