"""
This module is not for public use.

Use the `ElectricalNetwork.from_dgs` method to read a network from a dgs file.
"""

import json
import logging
import warnings
from itertools import chain, islice
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
    AbstractLoad,
    Bus,
    Element,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.typing import Id, StrPath

logger = logging.getLogger(__name__)


def network_from_dgs(
    filename: StrPath,
) -> tuple[
    dict[Id, Bus],
    dict[Id, Line],
    dict[Id, Transformer],
    dict[Id, Switch],
    dict[Id, AbstractLoad],
    dict[Id, VoltageSource],
    dict[Id, Ground],
    dict[Id, PotentialRef],
]:
    """Create the electrical elements from a JSON file in DGS format.

    Args:
        filename: name of the JSON file

    Returns:
        The elements of the network -- buses, lines, transformers, switches, loads, sources, grounds and potential refs.
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
    grounds: dict[Id, Ground] = {}
    buses: dict[Id, Bus] = {}
    potential_refs: dict[Id, PotentialRef] = {}
    sources: dict[Id, VoltageSource] = {}
    loads: dict[Id, AbstractLoad] = {}
    lines: dict[Id, Line] = {}
    transformers: dict[Id, Transformer] = {}
    switches: dict[Id, Switch] = {}

    # Ground and potential reference
    ground = Ground("ground")
    p_ref = PotentialRef(id="pref (ground)", element=ground)

    # Buses
    generate_buses(elm_term=elm_term, buses=buses)

    # Sources
    generate_sources(elm_xnet=elm_xnet, sources=sources, buses=buses, sta_cubic=sta_cubic, elm_term=elm_term)

    # Loads
    if elm_lod is not None:  # General loads
        generate_loads(elm_lod=elm_lod, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e6, load_type="General")
    if elm_lod_mv is not None:  # MV loads
        generate_loads(elm_lod=elm_lod_mv, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e6, load_type="MV")
    if elm_lod_lv is not None:  # LV loads
        generate_loads(elm_lod=elm_lod_lv, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e3, load_type="LV")
    if elm_pv_sys is not None:  # PV systems
        generate_loads(elm_lod=elm_pv_sys, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e3, load_type="PV")
    if elm_gen_stat is not None:  # Static generators
        generate_loads(
            elm_lod=elm_gen_stat, loads=loads, buses=buses, sta_cubic=sta_cubic, factor=1e6, load_type="GenStat"
        )

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
        generate_lines(
            elm_lne=elm_lne, lines=lines, buses=buses, sta_cubic=sta_cubic, lines_params=lines_params, ground=ground
        )

    # Transformers
    if elm_tr is not None:
        transformers_params: dict[Id, TransformerParameters] = {}
        transformers_tap: dict[Id, float] = {}
        if typ_tr is None:
            msg = (
                "The network contains transformers but is missing transformer types (TypTr2). Please copy all "
                "transformer types from the library to the project before exporting and try again."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)
        else:
            generate_typ_tr(typ_tr=typ_tr, transformers_params=transformers_params, transformers_tap=transformers_tap)
        generate_transformers(
            elm_tr=elm_tr,
            transformers=transformers,
            buses=buses,
            sta_cubic=sta_cubic,
            transformers_tap=transformers_tap,
            transformers_params=transformers_params,
        )

    # Switches
    if elm_coup is not None:
        generate_switches(elm_coup=elm_coup, switches=switches, buses=buses, sta_cubic=sta_cubic)

    _add_potential_refs(
        buses=buses,
        lines=lines,
        transformers=transformers,
        switches=switches,
        sources=sources,
        potential_refs=potential_refs,
        ground=ground,
    )

    if len(ground._connected_elements) > 1:  # Is the ground used? (Are there connected elements aside from pref)
        grounds[ground.id] = ground
        potential_refs[p_ref.id] = p_ref

    return buses, lines, transformers, switches, loads, sources, grounds, potential_refs


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


def _add_potential_refs(  # noqa: C901
    buses: dict[Id, Bus],
    lines: dict[Id, Line],
    transformers: dict[Id, Transformer],
    switches: dict[Id, Switch],
    sources: dict[Id, VoltageSource],
    potential_refs: dict[Id, PotentialRef],
    ground: Ground,
) -> None:
    """Add potential reference(s) to a DGS network."""
    # Note this function is adapted from the ElectricalNetwork._check_ref method
    elements = chain(buses.values(), lines.values(), transformers.values(), switches.values())
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
                        ground.connect(vs.bus)
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
                        ground.connect(element)
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
                            ground.connect(transformer_bus)
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
