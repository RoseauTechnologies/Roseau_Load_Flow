"""
This module is not for public use.

Use the `ElectricalNetwork.from_dgs` method to read a network from a dgs file.
"""

import json
import logging
import warnings
from typing import Any

import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.buses import generate_buses
from roseau.load_flow.io.dgs.lines import generate_lines, generate_typ_lne
from roseau.load_flow.io.dgs.loads import generate_loads
from roseau.load_flow.io.dgs.sources import generate_sources
from roseau.load_flow.io.dgs.switches import generate_switches
from roseau.load_flow.io.dgs.transformers import generate_transformers, generate_typ_tr
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    Ground,
    LineParameters,
    PotentialRef,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.typing import Id, StrPath

logger = logging.getLogger(__name__)


def network_from_dgs(
    filename: StrPath,
) -> tuple[
    dict[Id, Bus],
    dict[Id, AbstractBranch],
    dict[Id, AbstractLoad],
    dict[Id, VoltageSource],
    dict[Id, Ground],
    dict[Id, PotentialRef],
]:
    """Create the electrical elements from a JSON file in DGS format.

    Args:
        filename: name of the JSON file

    Returns:
        The elements of the network -- buses, branches, loads, sources, grounds and potential refs.
    """
    # Create dataframes from JSON file
    with open(filename, encoding="ISO-8859-10") as f:
        data = json.load(f)
    _parse_dgs_version(data)

    elm_xnet = _dgs_dict_to_df(data, "ElmXnet")  # External sources
    elm_term = _dgs_dict_to_df(data, "ElmTerm")  # Terminals (buses)
    sta_cubic = _dgs_dict_to_df(data, "StaCubic")  # Cubicles
    elm_tr = _dgs_dict_to_df(data, "ElmTr2") if "ElmTr2" in data else None  # Transformers
    typ_tr = _dgs_dict_to_df(data, "TypTr2") if "TypTr2" in data else None  # Transformer types
    elm_coup = _dgs_dict_to_df(data, "ElmCoup") if "ElmCoup" in data else None  # Switch
    elm_lne = _dgs_dict_to_df(data, "ElmLne") if "ElmLne" in data else None  # Lines
    typ_lne = _dgs_dict_to_df(data, "TypLne") if "TypLne" in data else None  # Line types
    elm_lod_lv = _dgs_dict_to_df(data, "ElmLodLV") if "ElmLodLV" in data else None  # LV loads
    elm_lod_mv = _dgs_dict_to_df(data, "ElmLodmv") if "ElmLodmv" in data else None  # MV loads
    elm_lod = _dgs_dict_to_df(data, "ElmLod") if "ElmLod" in data else None  # General loads
    elm_gen_stat = _dgs_dict_to_df(data, "ElmGenStat") if "ElmGenStat" in data else None  # Generators
    elm_pv_sys = _dgs_dict_to_df(data, "ElmPvsys") if "ElmPvsys" in data else None  # LV generators

    # ElectricalNetwork elements
    grounds: dict[Id, PotentialRef] = {}
    buses: dict[Id, Bus] = {}
    potential_refs: dict[Id, PotentialRef] = {}
    sources: dict[Id, VoltageSource] = {}
    loads: dict[Id, AbstractLoad] = {}
    branches: dict[Id, AbstractBranch] = {}

    # Ground and potential reference
    ground = Ground("ground")

    # Buses
    generate_buses(elm_term, buses)

    # Sources
    generate_sources(
        elm_xnet, sources, buses, potential_refs, sta_cubic, elm_term, ground, has_transfomers=elm_tr is not None
    )

    # Loads
    if elm_lod is not None:  # General loads
        generate_loads(elm_lod, loads, buses, sta_cubic, factor=1e6, load_type="General")
    if elm_lod_mv is not None:  # MV loads
        generate_loads(elm_lod_mv, loads, buses, sta_cubic, factor=1e6, load_type="MV")
    if elm_lod_lv is not None:  # LV loads
        generate_loads(elm_lod_lv, loads, buses, sta_cubic, factor=1e3, load_type="LV")
    if elm_pv_sys is not None:  # PV systems
        generate_loads(elm_pv_sys, loads, buses, sta_cubic, factor=1e3, load_type="PV")
    if elm_gen_stat is not None:  # Static generators
        generate_loads(elm_gen_stat, loads, buses, sta_cubic, factor=1e6, load_type="GenStat")

    # Lines
    if elm_lne is not None:
        lines_params: dict[Id, LineParameters] = {}
        if typ_lne is None:
            msg = (
                "The network contains lines but is missing line types (TypLne). Please copy all "
                "line types from the library to the project before exporting otherwise a "
                "LineParameter object will be created for each line."
            )
            warnings.warn(msg, stacklevel=3)
        else:
            generate_typ_lne(typ_lne=typ_lne, lines_params=lines_params)
        generate_lines(elm_lne, branches, buses, sta_cubic, lines_params, ground)

    # Transformers
    if elm_tr is not None:
        transformers_params: dict[Id, TransformerParameters] = {}
        transformers_tap: dict[Id, int] = {}
        if typ_tr is None:
            msg = (
                "The network contains transformers but is missing transformer types (TypTr2). Please copy all "
                "transformer types from the library to the project before exporting and try again."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, e=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)
        else:
            generate_typ_tr(typ_tr, transformers_params, transformers_tap)
        generate_transformers(elm_tr, branches, buses, sta_cubic, transformers_tap, transformers_params, ground)

    # Switches
    if elm_coup is not None:
        generate_switches(elm_coup, branches, buses, sta_cubic)

    if ground._connected_elements:  # Is the ground used?
        grounds[ground.id] = ground
        p_ref = PotentialRef("pref", element=ground)
        potential_refs[p_ref.id] = p_ref
    elif not potential_refs:  # No potential refs, define 1
        source_bus = buses[sources[next(iter(sources))].bus.id]
        p_ref = PotentialRef("pref", element=source_bus)
        potential_refs[p_ref.id] = p_ref

    return buses, branches, loads, sources, grounds, potential_refs


def _dgs_dict_to_df(data: dict[str, Any], name: str) -> pd.DataFrame:
    """Transform a DGS dictionary of elements into a dataframe indexed by the element ID."""
    return pd.DataFrame(columns=data[name]["Attributes"], data=data[name]["Values"]).set_index("FID")


def _parse_dgs_version(data: dict[str, Any]) -> tuple[int, ...]:
    """Parse the version of the DGS export, warn on old versions."""
    general_data = dict(zip(data["General"]["Attributes"], zip(*data["General"]["Values"], strict=True), strict=True))
    dgs_version = general_data["Val"][general_data["Descr"].index("Version")]
    dgs_version_tuple = tuple(map(int, dgs_version.split(".")))
    if dgs_version_tuple < (6, 0):
        msg = (
            f"The DGS version {dgs_version} is too old, this may cause conversion errors. Try "
            f"updating the version before exporting."
        )
        warnings.warn(msg, stacklevel=4)
    return dgs_version_tuple
