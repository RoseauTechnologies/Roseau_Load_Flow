"""
This module is not for public use.

Use the `ElectricalNetwork.from_dict` and `ElectricalNetwork.to_dict` methods to serialize networks
from and to dictionaries, or the methods `ElectricalNetwork.from_json` and `ElectricalNetwork.to_json`
to read and write networks from and to JSON files.
"""

import copy
import logging
from typing import TYPE_CHECKING, TypeVar

import numpy as np

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.typing import Id, JsonDict

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork

logger = logging.getLogger(__name__)

NETWORK_JSON_VERSION = 2
"""The current version of the network JSON file format."""

_T = TypeVar("_T", bound=AbstractBranch)


def _assign_branch_currents(branch: _T, branch_data: JsonDict) -> _T:
    """Small helper to assign the currents results to a branch object.

    Args:
        branch:
            The object to assign the results.

        branch_data:
            The data of the branch which may contain the results.

    Returns:
        The updated `branch` object.
    """
    if "results" in branch_data:
        currents1 = np.array([complex(i[0], i[1]) for i in branch_data["results"]["currents1"]], dtype=np.complex128)
        currents2 = np.array([complex(i[0], i[1]) for i in branch_data["results"]["currents2"]], dtype=np.complex128)
        branch._res_currents = (currents1, currents2)
        branch._fetch_results = False
        branch._no_results = False

    return branch


def network_from_dict(  # noqa: C901
    data: JsonDict, *, include_results: bool = True
) -> tuple[
    dict[Id, Bus],
    dict[Id, Line],
    dict[Id, Transformer],
    dict[Id, Switch],
    dict[Id, AbstractLoad],
    dict[Id, VoltageSource],
    dict[Id, Ground],
    dict[Id, PotentialRef],
    bool,
]:
    """Create the electrical network elements from a dictionary.

    Args:
        data:
            The dictionary containing the network data.

        include_results:
            If True (default) and the results of the load flow are included in the dictionary,
            the results are also loaded into the network.

    Returns:
        The buses, lines, transformers, switches, loads, sources, grounds and potential refs to construct the electrical
        network and a boolean indicating if the network has results.
    """
    data = copy.deepcopy(data)  # Make a copy to avoid modifying the original

    version = data.get("version", 0)
    if version <= 1:
        logger.warning(
            f"Got an outdated network file (version {version}), trying to update to the current format "
            f"(version {NETWORK_JSON_VERSION}). Please save the network again."
        )
        if version == 0:
            data = v0_to_v1_converter(data)
            include_results = False  # V0 network dictionaries didn't have results
        if version == 1:
            data = v1_to_v2_converter(data)
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

    # Grounds and potential refs
    grounds: dict[Id, Ground] = {}
    for ground_data in data["grounds"]:
        for ground_bus_data in ground_data["buses"]:
            ground_bus_data["bus"] = buses[ground_bus_data.pop("id")]
        ground = Ground.from_dict(data=ground_data, include_results=include_results)
        grounds[ground.id] = ground
        has_results = has_results and not ground._no_results

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
    lines_dict: dict[Id, Line] = {}
    for line_data in data["lines"]:
        id = line_data["id"]
        phases = line_data["phases"]
        bus1 = buses[line_data["bus1"]]
        bus2 = buses[line_data["bus2"]]
        geometry = Line._parse_geometry(line_data.get("geometry"))
        length = line_data["length"]
        lp = lines_params[line_data["params_id"]]
        gid = line_data.get("ground")
        ground = grounds[gid] if gid is not None else None
        line = Line(
            id=id, bus1=bus1, bus2=bus2, parameters=lp, phases=phases, length=length, ground=ground, geometry=geometry
        )
        if include_results:
            line = _assign_branch_currents(branch=line, branch_data=line_data)

        has_results = has_results and not line._no_results
        lines_dict[id] = line

    # Transformers
    transformers_dict: dict[Id, Transformer] = {}
    for transformer_data in data["transformers"]:
        id = transformer_data["id"]
        phases1 = transformer_data["phases1"]
        phases2 = transformer_data["phases2"]
        bus1 = buses[transformer_data["bus1"]]
        bus2 = buses[transformer_data["bus2"]]
        geometry = Transformer._parse_geometry(transformer_data.get("geometry"))
        tp = transformers_params[transformer_data["params_id"]]
        transformer = Transformer(
            id=id, bus1=bus1, bus2=bus2, parameters=tp, phases1=phases1, phases2=phases2, geometry=geometry
        )
        if include_results:
            transformer = _assign_branch_currents(branch=transformer, branch_data=transformer_data)

        has_results = has_results and not transformer._no_results
        transformers_dict[id] = transformer

    # Switches
    switches_dict: dict[Id, Switch] = {}
    for switch_data in data["switches"]:
        id = switch_data["id"]
        phases = switch_data["phases"]
        bus1 = buses[switch_data["bus1"]]
        bus2 = buses[switch_data["bus2"]]
        geometry = Switch._parse_geometry(switch_data.get("geometry"))
        switch = Switch(id=id, bus1=bus1, bus2=bus2, phases=phases, geometry=geometry)
        if include_results:
            switch = _assign_branch_currents(branch=switch, branch_data=switch_data)

        has_results = has_results and not switch._no_results
        switches_dict[id] = switch

    # Short-circuits
    short_circuits = data.get("short_circuits")
    if short_circuits is not None:
        for sc in short_circuits:
            ground_id = sc["short_circuit"]["ground"]
            ground = grounds[ground_id] if ground_id is not None else None
            buses[sc["bus_id"]].add_short_circuit(*sc["short_circuit"]["phases"], ground=ground)

    return buses, lines_dict, transformers_dict, switches_dict, loads, sources, grounds, potential_refs, has_results


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
    line_params.sort(key=lambda x: x["id"])  # Always keep the same order

    # Transformer parameters
    transformer_params: list[JsonDict] = []
    for tp in transformers_params_dict.values():
        transformer_params.append(tp.to_dict(include_results=include_results))
    transformer_params.sort(key=lambda x: x["id"])  # Always keep the same order

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
        z2, ym = TransformerParameters._compute_zy(**tp)
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
            w1, w2, _ = TransformerParameters.extract_windings(transformers_params[params_id]["type"])
            phases1 = "abcn" if ("y" in w1.lower() or "z" in w1.lower()) else "abc"
            phases2 = "abcn" if ("y" in w2.lower() or "z" in w2.lower()) else "abc"
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
