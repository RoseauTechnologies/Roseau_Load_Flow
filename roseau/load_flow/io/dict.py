"""
This module is not for public use.

Use the `ElectricalNetwork.from_dict` and `ElectricalNetwork.to_dict` methods to serialize networks
from and to dictionaries, or the methods `ElectricalNetwork.from_json` and `ElectricalNetwork.to_json`
to read and write networks from and to JSON files.
"""
import copy
import logging
from typing import TYPE_CHECKING

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

NETWORK_JSON_VERSION = 1
"""The current version of the network JSON file format."""


def network_from_dict(  # noqa: C901
    data: JsonDict, *, include_results: bool = True
) -> tuple[
    dict[Id, Bus],
    dict[Id, AbstractBranch],
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
        The buses, branches, loads, sources, grounds and potential refs to construct the electrical
        network and a boolean indicating if the network has results.
    """
    version = data.get("version", 0)
    if version == 0:
        logger.warning(
            f"Got an outdated network file (version 0), trying to update to the current format "
            f"(version {NETWORK_JSON_VERSION}). Please save the network again."
        )
        data = v0_to_v1_converter(data)
        include_results = False  # V0 network dictionaries didn't have results
    else:
        # If we arrive here, we dealt with all legacy versions, it must be the current one
        assert version == NETWORK_JSON_VERSION, f"Unsupported network file version {version}."

    data = copy.deepcopy(data)  # Make a copy to avoid modifying the original

    # Track if ALL results are included in the network
    has_results = include_results

    # Lines and transformers parameters
    lines_params = {
        lp["id"]: LineParameters.from_dict(lp, include_results=include_results) for lp in data["lines_params"]
    }
    transformers_params = {
        tp["id"]: TransformerParameters.from_dict(tp, include_results=include_results)
        for tp in data["transformers_params"]
    }

    # Buses, loads and sources
    buses: dict[Id, Bus] = {}
    for bus_data in data["buses"]:
        bus = Bus.from_dict(bus_data, include_results=include_results)
        buses[bus.id] = bus
        has_results = has_results and not bus._no_results
    loads: dict[Id, AbstractLoad] = {}
    for load_data in data["loads"]:
        load_data["bus"] = buses[load_data["bus"]]
        load = AbstractLoad.from_dict(load_data, include_results=include_results)
        loads[load.id] = load
        has_results = has_results and not load._no_results
    sources: dict[Id, VoltageSource] = {}
    for source_data in data["sources"]:
        source_data["bus"] = buses[source_data["bus"]]
        source = VoltageSource.from_dict(source_data, include_results=include_results)
        sources[source.id] = source
        has_results = has_results and not source._no_results

    # Grounds and potential refs
    grounds: dict[Id, Ground] = {}
    for ground_data in data["grounds"]:
        for ground_bus_data in ground_data["buses"]:
            ground_bus_data["bus"] = buses[ground_bus_data.pop("id")]
        ground = Ground.from_dict(ground_data, include_results=include_results)
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
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.JSON_PREF_INVALID)
        p_ref = PotentialRef.from_dict(pref_data, include_results=include_results)
        potential_refs[p_ref.id] = p_ref
        has_results = has_results and not p_ref._no_results

    # Branches
    branches_dict: dict[Id, AbstractBranch] = {}
    for branch_data in data["branches"]:
        id = branch_data["id"]
        phases1 = branch_data["phases1"]
        phases2 = branch_data["phases2"]
        bus1 = buses[branch_data["bus1"]]
        bus2 = buses[branch_data["bus2"]]
        geometry = AbstractBranch._parse_geometry(branch_data.get("geometry"))
        branch: AbstractBranch
        if branch_data["type"] == "line":
            assert phases1 == phases2, "Line phases1 and phases2 must be the same"
            length = branch_data["length"]
            lp = lines_params[branch_data["params_id"]]
            gid = branch_data.get("ground")
            ground = grounds[gid] if gid is not None else None
            branch = Line(
                id, bus1, bus2, parameters=lp, phases=phases1, length=length, ground=ground, geometry=geometry
            )
        elif branch_data["type"] == "transformer":
            tp = transformers_params[branch_data["params_id"]]
            branch = Transformer(id, bus1, bus2, parameters=tp, phases1=phases1, phases2=phases2, geometry=geometry)
        elif branch_data["type"] == "switch":
            assert phases1 == phases2, "Switch phases1 and phases2 must be the same"
            branch = Switch(id, bus1, bus2, phases=phases1, geometry=geometry)
        else:
            msg = f"Unknown branch type for branch {id}: {branch_data['type']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)
        if include_results and "results" in branch_data:
            currents1 = np.array(
                [complex(i[0], i[1]) for i in branch_data["results"]["currents1"]], dtype=np.complex128
            )
            currents2 = np.array(
                [complex(i[0], i[1]) for i in branch_data["results"]["currents2"]], dtype=np.complex128
            )
            branch._res_currents = (currents1, currents2)
            branch._fetch_results = False
            branch._no_results = False
        branches_dict[id] = branch
        has_results = has_results and not branch._no_results

    # Short-circuits
    short_circuits = data.get("short_circuits")
    if short_circuits is not None:
        for sc in short_circuits:
            ground_id = sc["short_circuit"]["ground"]
            ground = grounds[ground_id] if ground_id is not None else None
            buses[sc["bus_id"]].add_short_circuit(*sc["short_circuit"]["phases"], ground=ground)

    return buses, branches_dict, loads, sources, grounds, potential_refs, has_results


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

    # Export the branches with their parameters
    branches: list[JsonDict] = []
    lines_params_dict: dict[Id, LineParameters] = {}
    transformers_params_dict: dict[Id, TransformerParameters] = {}
    for branch in en.branches.values():
        branches.append(branch.to_dict(include_results=include_results))
        if isinstance(branch, Line):
            params_id = branch.parameters.id
            if params_id in lines_params_dict and branch.parameters != lines_params_dict[params_id]:
                msg = f"There are multiple line parameters with id {params_id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_LINE_PARAMETERS_DUPLICATES)
            lines_params_dict[branch.parameters.id] = branch.parameters
        elif isinstance(branch, Transformer):
            params_id = branch.parameters.id
            if params_id in transformers_params_dict and branch.parameters != transformers_params_dict[params_id]:
                msg = f"There are multiple transformer parameters with id {params_id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(
                    msg=msg, code=RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_PARAMETERS_DUPLICATES
                )
            transformers_params_dict[params_id] = branch.parameters

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
        "grounds": grounds,
        "potential_refs": potential_refs,
        "buses": buses,
        "branches": branches,
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
            "id": transformer_type["name"],
            "sn": transformer_type["sn"],
            "uhv": transformer_type["uhv"],
            "ulv": transformer_type["ulv"],
            "i0": transformer_type["i0"],
            "p0": transformer_type["p0"],
            "psc": transformer_type["psc"],
            "vsc": transformer_type["vsc"],
            "type": transformer_type["type"],
        }
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
        "version": NETWORK_JSON_VERSION,
        "grounds": grounds,
        "potential_refs": potential_refs,
        "buses": list(buses.values()),
        "branches": branches,
        "loads": loads,
        "sources": sources,
        "lines_params": list(lines_params.values()),
        "transformers_params": list(transformers_params.values()),
    }
