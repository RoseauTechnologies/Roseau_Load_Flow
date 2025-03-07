"""
This module is not for public use.

Use the `ElectricalNetwork.from_dict` and `ElectricalNetwork.to_dict` methods to serialize networks
from and to dictionaries, or the methods `ElectricalNetwork.from_json` and `ElectricalNetwork.to_json`
to read and write networks from and to JSON files.
"""

import copy
import logging
import warnings
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np

from roseau.load_flow.converters import _calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.common import NetworkElements
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
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
from roseau.load_flow.types import Insulator, Material
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import find_stack_level

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork

logger = logging.getLogger(__name__)

NETWORK_JSON_VERSION = 4
"""The current version of the network JSON file format."""


def network_from_dict(data: JsonDict, *, include_results: bool = True) -> tuple[NetworkElements, bool]:  # noqa: C901
    """Create the electrical network elements from a dictionary.

    Args:
        data:
            The dictionary containing the network data.

        include_results:
            If True (default) and the results of the load flow are included in the dictionary,
            the results are also loaded into the network.

    Returns:
        The buses, lines, transformers, switches, loads, sources, grounds, potential refs and ground
        connections to construct the electrical network and a boolean indicating if the network has
        results.
    """
    data = copy.deepcopy(data)  # Make a copy to avoid modifying the original

    version = data.get("version", 0)
    if version <= 3:
        warnings.warn(
            f"Got an outdated network file (version {version}), trying to update to the current format "
            f"(version {NETWORK_JSON_VERSION}). Please save the network again.",
            category=UserWarning,
            stacklevel=find_stack_level(),
        )
        if version <= 0:
            data = v0_to_v1_converter(data)
            include_results = False  # V0 network dictionaries didn't have results
        if version <= 1:
            data = v1_to_v2_converter(data)
        if version <= 2:
            data = v2_to_v3_converter(data)
        if version <= 3:
            data = v3_to_v4_converter(data)
    else:
        # If we arrive here, we dealt with all legacy versions, it must be the current one
        assert version == NETWORK_JSON_VERSION, f"Unsupported network file version {version}."

    # Check that the network is multiphase
    is_multiphase = data.get("is_multiphase", True)
    assert is_multiphase, f"Unsupported phase selection {is_multiphase=}."

    # Track if ALL results are included in the network
    has_results = include_results

    # Lines and transformers parameters
    lines_params = {
        lp["id"]: LineParameters.from_dict(data=lp, include_results=include_results) for lp in data["lines_params"]
    }
    transformers_params = {
        tp["id"]: TransformerParameters.from_dict(data=tp, include_results=include_results)
        for tp in data["transformers_params"]
    }

    # Grounds
    grounds: dict[Id, Ground] = {}
    for ground_data in data["grounds"]:
        ground = Ground.from_dict(data=ground_data, include_results=include_results)
        grounds[ground.id] = ground
        has_results = has_results and not ground._no_results

    # Buses, loads and sources
    buses: dict[Id, Bus] = {}
    for bus_data in data["buses"]:
        bus = Bus.from_dict(data=bus_data, include_results=include_results)
        buses[bus.id] = bus
        has_results = has_results and not bus._no_results
    loads: dict[Id, AbstractLoad] = {}
    for load_data in data["loads"]:
        load_data["bus"] = buses[load_data["bus"]]
        load = AbstractLoad.from_dict(data=load_data, include_results=include_results)
        loads[load.id] = load
        has_results = has_results and not load._no_results
    sources: dict[Id, VoltageSource] = {}
    for source_data in data["sources"]:
        source_data["bus"] = buses[source_data["bus"]]
        source = VoltageSource.from_dict(data=source_data, include_results=include_results)
        sources[source.id] = source
        has_results = has_results and not source._no_results

    # Potential refs
    potential_refs: dict[Id, PotentialRef] = {}
    for pref_data in data["potential_refs"]:
        if "bus" in pref_data:
            pref_data["element"] = buses[pref_data.pop("bus")]
        elif "ground" in pref_data:
            pref_data["element"] = grounds[pref_data.pop("ground")]
        else:
            msg = f"Potential reference data {pref_data['id']} missing bus or ground."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_PREF_INVALID)
        p_ref = PotentialRef.from_dict(data=pref_data, include_results=include_results)
        potential_refs[p_ref.id] = p_ref
        has_results = has_results and not p_ref._no_results

    # Lines
    lines: dict[Id, Line] = {}
    for line_data in data["lines"]:
        line_data["bus1"] = buses[line_data["bus1"]]
        line_data["bus2"] = buses[line_data["bus2"]]
        line_data["parameters"] = lines_params[line_data.pop("params_id")]
        if (ground_id := line_data.pop("ground", None)) is not None:
            line_data["ground"] = grounds[ground_id]
        line = Line.from_dict(data=line_data, include_results=include_results)
        lines[line.id] = line
        has_results = has_results and not line._no_results

    # Transformers
    transformers: dict[Id, Transformer] = {}
    for transformer_data in data["transformers"]:
        transformer_data["bus_hv"] = buses[transformer_data["bus_hv"]]
        transformer_data["bus_lv"] = buses[transformer_data["bus_lv"]]
        transformer_data["parameters"] = transformers_params[transformer_data.pop("params_id")]
        transformer = Transformer.from_dict(data=transformer_data, include_results=include_results)
        transformers[transformer.id] = transformer
        has_results = has_results and not transformer._no_results

    # Switches
    switches: dict[Id, Switch] = {}
    for switch_data in data["switches"]:
        switch_data["bus1"] = buses[switch_data["bus1"]]
        switch_data["bus2"] = buses[switch_data["bus2"]]
        switch = Switch.from_dict(data=switch_data, include_results=include_results)
        switches[switch.id] = switch
        has_results = has_results and not switch._no_results

    # Ground connections
    ground_connections: dict[Id, GroundConnection] = {}
    for gc_data in data["ground_connections"]:
        element = gc_data.pop("element")
        gc_data["ground"] = grounds[gc_data.pop("ground")]
        match element["type"]:
            case "bus":
                gc_data["element"] = buses[element["id"]]
            case "load":
                gc_data["element"] = loads[element["id"]]
            case "source":
                gc_data["element"] = sources[element["id"]]
            case "line":
                gc_data["element"] = lines[element["id"]]
            case "transformer":
                gc_data["element"] = transformers[element["id"]]
            case "switch":
                gc_data["element"] = switches[element["id"]]
            case what:
                raise AssertionError(f"Unknown element type {what!r} for ground connection {gc_data['id']!r}.")
        gc = GroundConnection.from_dict(data=gc_data, include_results=include_results)
        ground_connections[gc.id] = gc
        has_results = has_results and not gc._no_results

    # Short-circuits
    short_circuits = data.get("short_circuits")
    if short_circuits is not None:
        for sc in short_circuits:
            ground_id = sc["short_circuit"]["ground"]
            ground = grounds[ground_id] if ground_id is not None else None
            buses[sc["bus_id"]].add_short_circuit(*sc["short_circuit"]["phases"], ground=ground)

    return (
        {
            "buses": buses,
            "lines": lines,
            "transformers": transformers,
            "switches": switches,
            "loads": loads,
            "sources": sources,
            "grounds": grounds,
            "potential_refs": potential_refs,
            "ground_connections": ground_connections,
        },
        has_results,
    )


def network_to_dict(en: "ElectricalNetwork", *, include_results: bool) -> JsonDict:
    """Return a dictionary of the current network data.

    Args:
        en:
            The electrical network.

        include_results:
            If True (default), the results of the load flow are included in the dictionary.
            If no results are available, this option is ignored.

    Returns:
        The created dictionary.
    """
    # Export the grounds and the pref
    grounds = [ground.to_dict(include_results=include_results) for ground in en.grounds.values()]
    potential_refs = [p_ref.to_dict(include_results=include_results) for p_ref in en.potential_refs.values()]
    ground_connections = [gc.to_dict(include_results=include_results) for gc in en.ground_connections.values()]

    # Export the buses, loads and sources
    buses: list[JsonDict] = []
    loads: list[JsonDict] = []
    sources: list[JsonDict] = []
    short_circuits: list[JsonDict] = []
    for bus in en.buses.values():
        buses.append(bus.to_dict(include_results=include_results))
        for element in bus._connected_elements:
            if isinstance(element, AbstractLoad):
                assert element.bus is bus
                loads.append(element.to_dict(include_results=include_results))
            elif isinstance(element, VoltageSource):
                assert element.bus is bus
                sources.append(element.to_dict(include_results=include_results))
        for sc in bus.short_circuits:
            short_circuits.append({"bus_id": bus.id, "short_circuit": sc})

    # Export the lines with their parameters
    lines: list[JsonDict] = []
    lines_params_dict: dict[Id, LineParameters] = {}
    for line in en.lines.values():
        lines.append(line.to_dict(include_results=include_results))
        params_id = line.parameters.id
        if params_id in lines_params_dict and line.parameters != lines_params_dict[params_id]:
            msg = f"There are multiple line parameters with id {params_id!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_LINE_PARAMETERS_DUPLICATES)
        lines_params_dict[line.parameters.id] = line.parameters

    # Export the transformers with their parameters
    transformers: list[JsonDict] = []
    transformers_params_dict: dict[Id, TransformerParameters] = {}
    for transformer in en.transformers.values():
        transformers.append(transformer.to_dict(include_results=include_results))
        params_id = transformer.parameters.id
        if params_id in transformers_params_dict and transformer.parameters != transformers_params_dict[params_id]:
            msg = f"There are multiple transformer parameters with id {params_id!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(
                msg=msg, code=RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_PARAMETERS_DUPLICATES
            )
        transformers_params_dict[params_id] = transformer.parameters

    # Export the switches
    switches = [switch.to_dict(include_results=include_results) for switch in en.switches.values()]

    # Line parameters
    line_params: list[JsonDict] = []
    for lp in lines_params_dict.values():
        line_params.append(lp.to_dict(include_results=include_results))
    line_params.sort(key=lambda x: (type(x["id"]).__name__, str(x["id"])))  # Always keep the same order

    # Transformer parameters
    transformer_params: list[JsonDict] = []
    for tp in transformers_params_dict.values():
        transformer_params.append(tp.to_dict(include_results=include_results))
    transformer_params.sort(key=lambda x: (type(x["id"]).__name__, str(x["id"])))  # Always keep the same order

    res = {
        "version": NETWORK_JSON_VERSION,
        "is_multiphase": True,
        "grounds": grounds,
        "potential_refs": potential_refs,
        "buses": buses,
        "lines": lines,
        "transformers": transformers,
        "switches": switches,
        "loads": loads,
        "sources": sources,
        "lines_params": line_params,
        "transformers_params": transformer_params,
        "ground_connections": ground_connections,
    }
    if short_circuits:
        res["short_circuits"] = short_circuits
    return res


def v0_to_v1_converter(data: JsonDict) -> JsonDict:  # noqa: C901
    """Convert a v0 network dict to a v1 network dict.

    Args:
        data:
            The v0 network data.

    Returns:
        The v1 network data.
    """
    # V0 had only 3-phase networks
    assert data.get("version", 0) == 0, data["version"]

    # Only one ground in V0
    ground = {"id": "ground", "buses": []}
    grounds = [ground]

    # There is always a potential ref connected to ground in V0
    potential_refs = [{"id": "pref", "ground": ground["id"]}]
    used_potential_refs_ids = {"pref"}

    # Buses, loads and sources
    loads = []
    sources = []
    buses = {}
    for old_bus in data["buses"]:
        bus_id = old_bus["id"]
        bus = {"id": bus_id}
        if old_bus["type"] == "slack":
            # Old slack bus is a bus with a voltage source, it has "abcn" phases
            source = {
                "id": bus_id,  # We didn't have sources in V0, set source id to bus id
                "bus": bus_id,
                "phases": "abcn",
                "voltages": list(old_bus["voltages"].values()),
            }
            sources.append(source)
            phases = "abcn"
            ground["buses"].append({"id": bus_id, "phase": "n"})  # All slack buses had a ground in V0
        elif old_bus["type"] == "bus_neutral":
            phases = "abcn"
        else:
            assert old_bus["type"] == "bus"
            phases = "abc"
        bus["phases"] = phases
        # buses in V0 didn't have (initial) potentials, they were ignored
        if "geometry" in old_bus:  # geometry is optional
            bus["geometry"] = Bus._parse_geometry(old_bus["geometry"]).__geo_interface__
        buses[bus_id] = bus

        for old_load in old_bus["loads"]:
            func = old_load["function"]
            flexible_params = None
            if func.startswith("y"):  # Star loads
                load_phases = "abcn"
                if func.endswith("_neutral"):
                    assert phases == "abcn"  # y*_neutral loads are only for buses with neutral
                else:
                    assert phases == "abc"  # y* loads are only for buses without neutral
            elif func.startswith("d"):  # Delta loads
                load_phases = "abc"
            else:  # Flexible loads
                assert func == "flexible"
                assert "powers" in old_load
                load_phases = "abcn"
                flexible_params = old_load["parameters"]

            load = {"id": old_load["id"], "bus": bus_id, "phases": load_phases}
            load_powers = old_load.get("powers")
            load_currents = old_load.get("currents")
            load_impedances = old_load.get("impedances")
            if load_powers is not None:
                assert load_currents is None
                assert load_impedances is None
                load["powers"] = list(load_powers.values())
                if flexible_params is not None:
                    load["flexible_params"] = flexible_params
            elif load_currents is not None:
                assert load_impedances is None
                load["currents"] = list(load_currents.values())
            else:
                assert load_impedances is not None
                load["impedances"] = list(load_impedances.values())
            loads.append(load)
    assert sources, "No slack bus found"

    # Branches
    branches = []
    lines_params = {}
    transformers_params = {}
    for line_type in data["line_types"]:
        lp = {"id": line_type["name"], "model": line_type["model"], "z_line": line_type["z_line"]}
        if "y_shunt" in line_type:
            lp["y_shunt"] = line_type["y_shunt"]
        lines_params[lp["id"]] = lp
    for transformer_type in data["transformer_types"]:
        tp = {
            "sn": transformer_type["sn"],
            "uhv": transformer_type["uhv"],
            "ulv": transformer_type["ulv"],
            "i0": transformer_type["i0"],
            "p0": transformer_type["p0"],
            "psc": transformer_type["psc"],
            "vsc": transformer_type["vsc"],
            "type": transformer_type["type"],
        }
        z2, ym = TransformerParameters._compute_zy(
            vg=tp["type"],
            uhv=tp["uhv"],
            ulv=tp["ulv"],
            sn=tp["sn"],
            p0=tp["p0"],
            i0=tp["i0"],
            psc=tp["psc"],
            vsc=tp["vsc"],
        )
        tp["id"] = transformer_type["name"]
        tp["z2"] = [z2.real, z2.imag]
        tp["ym"] = [ym.real, ym.imag]
        transformers_params[tp["id"]] = tp
    for old_branch in data["branches"]:
        branch_id = old_branch["id"]
        bus1_id = old_branch["bus1"]
        bus2_id = old_branch["bus2"]
        branch_type = old_branch["type"]
        branch = {"id": branch_id, "bus1": bus1_id, "bus2": bus2_id}
        if "geometry" in old_branch:
            branch["geometry"] = AbstractBranch._parse_geometry(old_branch["geometry"]).__geo_interface__
        if branch_type == "line":
            params_id = old_branch["type_name"]
            branch["length"] = old_branch["length"]
            branch["params_id"] = params_id
            branch["type"] = branch_type
            # Lines have no phases information, we need to infer it from the line parameters
            n = len(lines_params[params_id]["z_line"][0])  # Size of the line resistance matrix
            phases1 = phases2 = "abcn" if n == 4 else "abc"
            if "y_shunt" in lines_params[params_id]:
                branch["ground"] = ground["id"]  # Shunt lines all connected to the same ground
        elif branch_type == "transformer":
            params_id = old_branch["type_name"]
            branch["params_id"] = params_id
            branch["tap"] = old_branch["tap"]
            branch["type"] = branch_type
            # Transformers have no phases information, we need to infer it from the windings
            whv, wlv, _ = TransformerParameters.extract_windings(transformers_params[params_id]["type"])
            phases1 = "abcn" if ("y" in whv.lower() or "z" in whv.lower()) else "abc"
            phases2 = "abcn" if ("y" in wlv.lower() or "z" in wlv.lower()) else "abc"
            # Determine the "special element" connected to bus2 of the transformer
            if phases2 == "abcn":  # ground if it has neutral
                ground["buses"].append({"id": bus2_id, "phase": "n"})
            else:  # potential reference if it has no neutral
                # Construct a unique id for the potential ref
                pref_id = f"{branch_id}{bus2_id}"
                i = 2
                while pref_id in used_potential_refs_ids:
                    pref_id = f"{branch_id}{bus2_id}-{i}"
                    i += 1
                used_potential_refs_ids.add(pref_id)
                pref = {"id": pref_id, "bus": bus2_id, "phases": None}
                potential_refs.append(pref)
        else:
            assert branch_type == "switch"
            branch["type"] = branch_type
            # Switches have no phases information, we need to infer it from the buses
            if buses[bus1_id]["phases"] == buses[bus2_id]["phases"] == "abcn":
                # Only if both buses have neutral the switch has neutral
                phases1 = phases2 = "abcn"
            else:
                phases1 = phases2 = "abc"
        branch["phases1"] = phases1
        branch["phases2"] = phases2
        branches.append(branch)

    return {
        "version": 1,
        "grounds": grounds,
        "potential_refs": potential_refs,
        "buses": list(buses.values()),
        "branches": branches,
        "loads": loads,
        "sources": sources,
        "lines_params": list(lines_params.values()),
        "transformers_params": list(transformers_params.values()),
    }


def v1_to_v2_converter(data: JsonDict) -> JsonDict:
    """Convert a v1 network dict to a v2 network dict.

    Args:
        data:
            The v1 network data.

    Returns:
        The v2 network data.
    """
    assert data.get("version", 0) == 1, data["version"]

    # In the results of flexible PowerLoad, the key "powers" is renamed "flexible_powers"
    # The potentials of loads are always stored in the results part of loads
    # The key "type" is added
    buses = data.get("buses", [])
    buses_dict = {b["id"]: b for b in buses}
    old_loads = data.get("loads", [])
    loads = []
    for load_data in old_loads:
        # Add the type
        if "powers" in load_data:
            load_data["type"] = "power"
        elif "currents" in load_data:
            load_data["type"] = "current"
        elif "impedances" in load_data:
            load_data["type"] = "impedance"
        else:
            msg = f"Unknown load type for load {load_data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)

        # Add the connect_neutral key
        load_data["connect_neutral"] = None

        # Modify the results
        load_data_result = load_data.get("results", None)
        if load_data_result is not None:
            if "potentials" not in load_data_result:
                bus_data = buses_dict[load_data["bus"]]
                bus_phases = bus_data["phases"]
                bus_potentials = bus_data["results"]["potentials"]
                load_phases = load_data["phases"]
                load_data_result["potentials"] = [bus_potentials[bus_phases.index(p)] for p in load_phases]
            if "powers" in load_data_result:
                load_data_result["flexible_powers"] = load_data_result.pop("powers")
        loads.append(load_data)

    # The potentials of sources are always stored in the results part of sources
    old_sources = data.get("sources", [])
    sources = []
    for source_data in old_sources:
        # Add the connect_neutral key
        source_data["connect_neutral"] = None

        # Modify the results
        source_data_result = source_data.get("results", None)
        if source_data_result is not None and "potentials" not in source_data_result:
            bus_data = buses_dict[source_data["bus"]]
            bus_phases = bus_data["phases"]
            bus_potentials = bus_data["results"]["potentials"]
            source_phases = source_data["phases"]
            source_data_result["potentials"] = [bus_potentials[bus_phases.index(p)] for p in source_phases]
        sources.append(source_data)

    # The old key "branches" is replaced by the keys "lines", "transformers" and "switches"
    # The key "branch_type" is not necessary anymore
    # For switches and lines, "phases1" and "phases2" are replaced by the key "phases"
    old_branches = data.get("branches", [])
    transformers = []
    lines = []
    switches = []
    for branch_data in old_branches:
        branch_type = branch_data.pop("type")
        match branch_type:
            case "transformer":
                transformers.append(branch_data)
            case "line":
                phases1 = branch_data.pop("phases1")
                phases2 = branch_data.pop("phases2")
                assert phases1 == phases2, f"The phases 1 and 2 of the line {branch_data['id']} should be equal."
                branch_data["phases"] = phases1
                lines.append(branch_data)
            case "switch":
                phases1 = branch_data.pop("phases1")
                phases2 = branch_data.pop("phases2")
                assert phases1 == phases2, f"The phases 1 and 2 of the switch {branch_data['id']} should be equal."
                branch_data["phases"] = phases1
                switches.append(branch_data)
            case _:
                msg = f"Unknown branch type for branch {branch_data['id']}: {branch_type}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)

    results = {
        "version": 2,
        "is_multiphase": True,  # Always True before the version 2
        "grounds": data["grounds"],  # Unchanged
        "potential_refs": data["potential_refs"],  # Unchanged
        "buses": data["buses"],  # Unchanged
        "lines": lines,
        "switches": switches,
        "transformers": transformers,
        "loads": loads,
        "sources": sources,
        "lines_params": data["lines_params"],  # Unchanged
        "transformers_params": data["transformers_params"],  # Unchanged
    }
    if "short_circuits" in data:
        results["short_circuits"] = data["short_circuits"]  # Unchanged

    return results


def v2_to_v3_converter(data: JsonDict) -> JsonDict:  # noqa: C901
    """Convert a v2 network dict to a v3 network dict.

    Args:
        data:
            The v2 network data.

    Returns:
        The v3 network data.
    """
    assert data.get("version", 0) == 2, data["version"]

    # The name of min_voltage and max_voltage have changed so they are not usable anymore.
    old_buses = data.get("buses", [])
    buses = []
    bus_warning_emitted: bool = False
    for bus_data in old_buses:
        for key in ("min_voltage", "max_voltage"):
            if bus_data.pop(key, None) is not None and not bus_warning_emitted:
                warnings.warn(
                    "Starting with version 0.11.0 of roseau-load-flow (JSON file v3), `min_voltage` and "
                    "`max_voltage` are replaced with `min_voltage_level`, `max_voltage_level` and `nominal_voltage`. "
                    "The found values of `min_voltage` or `max_voltage` are dropped.",
                    stacklevel=find_stack_level(),
                )
                bus_warning_emitted = True
        buses.append(bus_data)

    # Remove `max_power`
    # Rename `type` to `vg`
    old_transformers_params = data.get("transformers_params", [])
    transformers_params = []
    transformers_params_max_loading = {}
    for transformer_param_data in old_transformers_params:
        vg = transformer_param_data.pop("type")
        if vg == "single":
            vg = "Ii0"
        elif vg == "center":
            vg = "Iii0"
        transformer_param_data["vg"] = vg
        if (max_power := transformer_param_data.pop("max_power", None)) is not None:
            loading = max_power / transformer_param_data["sn"]
        else:
            loading = 1
        transformers_params_max_loading[transformer_param_data["id"]] = loading
        transformers_params.append(transformer_param_data)

    # Rename `maximal_current` to `ampacities` and use array
    # Rename `section` to `sections` and use array
    # Rename `insulator_type` to `insulators` and use array. `Unknown` is deleted
    # Rename `material` to `materials` and use array
    old_lines_params = data.get("lines_params", [])
    lines_params = []
    for line_param_data in old_lines_params:
        size = len(line_param_data["z_line"][0])
        if (maximal_current := line_param_data.pop("max_current", None)) is not None:
            line_param_data["ampacities"] = [maximal_current] * size
        if (section := line_param_data.pop("section", None)) is not None:
            line_param_data["sections"] = [section] * size
        if (conductor_type := line_param_data.pop("conductor_type", None)) is not None:
            line_param_data["materials"] = [conductor_type] * size
        if (
            (insulator_type := line_param_data.pop("insulator_type", None)) is not None
        ) and insulator_type.lower() != "unknown":
            line_param_data["insulators"] = [insulator_type] * size
        lines_params.append(line_param_data)

    # Add max_loading to lines
    old_lines = data.get("lines", [])
    lines = []
    for line_data in old_lines:
        line_data["max_loading"] = 1
        lines.append(line_data)

    # Add max_loading to transformers
    old_transformers = data.get("transformers", [])
    transformers = []
    for transformer_data in old_transformers:
        transformer_data["max_loading"] = transformers_params_max_loading[transformer_data["params_id"]]
        transformers.append(transformer_data)

    results = {
        "version": 3,
        "is_multiphase": data["is_multiphase"],  # Unchanged
        "grounds": data["grounds"],  # Unchanged
        "potential_refs": data["potential_refs"],  # Unchanged
        "buses": buses,  # <---- Changed
        "lines": lines,  # <---- Changed
        "switches": data["switches"],  # Unchanged
        "transformers": transformers,  # <---- Changed
        "loads": data["loads"],  # Unchanged
        "sources": data["sources"],  # Unchanged
        "lines_params": lines_params,  # <---- Changed
        "transformers_params": transformers_params,  # <---- Changed
    }
    if "short_circuits" in data:
        results["short_circuits"] = data["short_circuits"]  # Unchanged

    return results


def v3_to_v4_converter(data: JsonDict) -> JsonDict:  # noqa: C901
    """Convert a v3 network dict to a v4 network dict.

    Args:
        data:
            The v3 network data.

    Returns:
        The v4 network data.
    """
    assert data["version"] == 3, data["version"]

    grounds = []
    ground_connections = []
    gc_id = 1
    for ground in data["grounds"]:
        for gc_bus_data in ground.pop("buses"):
            gid = ground["id"]
            bid = gc_bus_data["id"]
            gc_data = {
                "id": str(gc_id) if isinstance(gid, str) else gc_id,
                "ground": gid,
                "element": {"id": bid, "type": "bus"},
                "phase": gc_bus_data["phase"],
                "side": None,
                "impedance": [0.0, 0.0],
                "on_connected": "raise",
            }
            if "results" in ground:
                gc_data["results"] = {"current": [0.0, 0.0]}
            gc_id += 1
            ground_connections.append(gc_data)
        grounds.append(ground)

    buses = []
    for bus in data["buses"]:
        # Rename potentials to initial_potentials
        if "potentials" in bus:
            bus["initial_potentials"] = bus.pop("potentials")
        buses.append(bus)

    sources = []
    for source in data["sources"]:
        # Add source type
        source["type"] = "voltage"
        sources.append(source)

    tr_phases_per_params = defaultdict(list)
    for tr in data["transformers"]:
        tr_phases_per_params[tr["params_id"]].append((tr["phases1"], tr["phases2"]))

    transformer_params = []
    for tp_data in data["transformers_params"]:
        whv, wlv, clock = TransformerParameters.extract_windings(tp_data["vg"])
        # Handle brought out neutrals that were not declared as such
        if whv in ("Y", "Z") and any(tr_phases[0] == "abcn" for tr_phases in tr_phases_per_params[tp_data["id"]]):
            whv += "N"
        if wlv in ("y", "z") and any(tr_phases[1] == "abcn" for tr_phases in tr_phases_per_params[tp_data["id"]]):
            wlv += "n"
        # Normalize the vector group (dyN11 -> Dyn11)
        tp_data["vg"] = f"{whv}{wlv}{clock}"
        transformer_params.append(tp_data)

    line_params = []
    for line_param_data in data["lines_params"]:
        # Normalize the insulator and material types
        if (materials := line_param_data.pop("materials", None)) is not None:
            line_param_data["materials"] = [Material(material).name for material in materials]
        if (insulators := line_param_data.pop("insulators", None)) is not None:
            line_param_data["insulators"] = [Insulator(insulator).name for insulator in insulators]
        line_params.append(line_param_data)

    buses_dict = {b["id"]: b for b in data["buses"]}

    def get_branch_potentials_from_bus(bus_id: Id, branch_phases: str) -> list[list[float]]:
        bus_data: JsonDict = buses_dict[bus_id]
        bus_phases: str = bus_data["phases"]
        bus_potentials: list[list[float]] = bus_data["results"]["potentials"]
        return [bus_potentials[bus_phases.index(p)] for p in branch_phases]

    transformers = []
    for tr_data in data["transformers"]:
        # Handle renamed keys
        tr_data["bus_hv"] = tr_data.pop("bus1")
        tr_data["bus_lv"] = tr_data.pop("bus2")
        tr_data["phases_hv"] = tr_data.pop("phases1")
        tr_data["phases_lv"] = tr_data.pop("phases2")
        if "results" in tr_data:
            tr_data["results"]["currents_hv"] = tr_data["results"].pop("currents1")
            tr_data["results"]["currents_lv"] = tr_data["results"].pop("currents2")
        # Handle missing results
        if "results" in tr_data:
            tr_data["results"]["potentials_hv"] = get_branch_potentials_from_bus(
                bus_id=tr_data["bus_hv"], branch_phases=tr_data["phases_hv"]
            )
            tr_data["results"]["potentials_lv"] = get_branch_potentials_from_bus(
                bus_id=tr_data["bus_lv"], branch_phases=tr_data["phases_lv"]
            )
        # Handle floating neutrals
        tr_data["connect_neutral_hv"] = None
        tr_data["connect_neutral_lv"] = None
        transformers.append(tr_data)

    lines = []
    for line_data in data["lines"]:
        # Handle missing results
        if "results" in line_data:
            line_data["results"]["potentials1"] = get_branch_potentials_from_bus(
                bus_id=line_data["bus1"], branch_phases=line_data["phases"]
            )
            line_data["results"]["potentials2"] = get_branch_potentials_from_bus(
                bus_id=line_data["bus2"], branch_phases=line_data["phases"]
            )
        lines.append(line_data)

    switches = []
    for switch_data in data["switches"]:
        # Handle missing results
        if "results" in switch_data:
            switch_data["results"]["potentials1"] = get_branch_potentials_from_bus(
                bus_id=switch_data["bus1"], branch_phases=switch_data["phases"]
            )
            switch_data["results"]["potentials2"] = get_branch_potentials_from_bus(
                bus_id=switch_data["bus2"], branch_phases=switch_data["phases"]
            )
        switches.append(switch_data)

    loads = []
    for load_data in data["loads"]:
        # Handle missing results
        if "results" in load_data:
            potentials = np.array([complex(*v) for v in load_data["results"]["potentials"]], dtype=np.complex128)
            voltages = _calculate_voltages(potentials, load_data["phases"])
            if load_data["type"] == "current":
                currents = np.array([complex(*z) for z in load_data["currents"]], dtype=np.complex128)
                inner_currents = currents * voltages / np.abs(voltages)
            elif load_data["type"] == "power":
                powers = np.array([complex(*z) for z in load_data["powers"]], dtype=np.complex128)
                inner_currents = np.conj(powers / voltages)
            else:
                assert load_data["type"] == "impedance"
                impedances = np.array([complex(*z) for z in load_data["impedances"]], dtype=np.complex128)
                inner_currents = voltages / impedances
            load_data["results"]["inner_currents"] = [[i.real, i.imag] for i in inner_currents]
        loads.append(load_data)

    results = {
        "version": 4,
        "is_multiphase": data["is_multiphase"],  # Unchanged
        "grounds": grounds,
        "potential_refs": data["potential_refs"],  # Unchanged
        "buses": buses,
        "lines": lines,
        "switches": switches,
        "transformers": transformers,
        "loads": loads,
        "sources": sources,
        "lines_params": line_params,
        "transformers_params": transformer_params,
        "ground_connections": ground_connections,
    }
    if "short_circuits" in data:
        results["short_circuits"] = data["short_circuits"]  # Unchanged

    return results
