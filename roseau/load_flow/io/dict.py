import functools
import logging
import os
import platform
import sys
from importlib.metadata import version
from typing import TYPE_CHECKING

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.typing import Id, JsonDict

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _get_system_info() -> JsonDict:
    from roseau.load_flow import __version__  # circular import

    return {
        # RLF version (for compatibility checks)
        # --------------------------------------
        "version": __version__,
        # System information (useful for debugging)
        # -----------------------------------------
        "os_name": os.name,  # posix, nt etc.
        "platform": sys.platform,  # linux, win32, darwin etc.
        "machine": platform.machine(),  # x86_64, amd64, i386 etc.
        # Python environment (useful for debugging)
        # -----------------------------------------
        # Only packages that may affect the json data are included
        "python_version": sys.version_info,
        "numpy_version": version("numpy"),
        "pint_version": version("pint"),
        "shapely_version": version("shapely"),
    }


def network_from_dict(
    data: JsonDict, en_class: type["ElectricalNetwork"]
) -> tuple[
    dict[Id, Bus],
    dict[Id, AbstractBranch],
    dict[Id, AbstractLoad],
    dict[Id, VoltageSource],
    dict[Id, Ground],
    dict[Id, PotentialRef],
]:
    """Create the electrical network elements from a dictionary.

    Args:
        data:
            The dictionary containing the network data.

        en_class:
            The ElectricalNetwork class to create.

    Returns:
        The buses, branches, loads, sources, grounds and potential refs to construct the electrical
        network.
    """
    # Lines and transformers parameters
    lines_params = {lp["id"]: LineParameters.from_dict(lp) for lp in data["lines_params"]}
    transformers_params = {tp["id"]: TransformerParameters.from_dict(tp) for tp in data["transformers_params"]}

    # Buses, loads and sources
    buses = {bd["id"]: en_class.bus_class.from_dict(bd) for bd in data["buses"]}
    loads = {ld["id"]: en_class.load_class.from_dict(ld | {"bus": buses[ld["bus"]]}) for ld in data["loads"]}
    sources = {
        sd["id"]: en_class.voltage_source_class.from_dict(sd | {"bus": buses[sd["bus"]]}) for sd in data["sources"]
    }

    # Grounds and potential refs
    grounds: dict[Id, Ground] = {}
    for ground_data in data["grounds"]:
        ground = en_class.ground_class(ground_data["id"])
        for bus_id, phase in ground_data["buses"].items():
            ground.connect(buses[bus_id], phase)
        grounds[ground_data["id"]] = ground
    potential_refs: dict[Id, PotentialRef] = {}
    for pref_data in data["potential_refs"]:
        if "bus" in pref_data:
            bus_or_ground = buses[pref_data["bus"]]
        elif "ground" in pref_data:
            bus_or_ground = grounds[pref_data["ground"]]
        else:
            msg = f"Potential reference data {pref_data['id']} missing bus or ground."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.JSON_PREF_INVALID)
        potential_refs[pref_data["id"]] = en_class.pref_class(
            pref_data["id"], element=bus_or_ground, phase=pref_data.get("phases")
        )

    # Branches
    branches_dict: dict[Id, AbstractBranch] = {}
    for branch_data in data["branches"]:
        id = branch_data["id"]
        phases1 = branch_data["phases1"]
        phases2 = branch_data["phases2"]
        bus1 = buses[branch_data["bus1"]]
        bus2 = buses[branch_data["bus2"]]
        geometry = AbstractBranch._parse_geometry(branch_data.get("geometry"))
        if branch_data["type"] == "line":
            assert phases1 == phases2
            length = branch_data["length"]
            lp = lines_params[branch_data["params_id"]]
            gid = branch_data.get("ground")
            ground = grounds[gid] if gid is not None else None
            branches_dict[branch_data["id"]] = en_class.line_class(
                id, bus1, bus2, parameters=lp, phases=phases1, length=length, ground=ground, geometry=geometry
            )
        elif branch_data["type"] == "transformer":
            tp = transformers_params[branch_data["params_id"]]
            branches_dict[id] = en_class.transformer_class(
                id, bus1, bus2, parameters=tp, phases1=phases1, phases2=phases2, geometry=geometry
            )
        elif branch_data["type"] == "switch":
            assert phases1 == phases2
            branches_dict[id] = en_class.switch_class(id, bus1, bus2, phases=phases1, geometry=geometry)
        else:
            msg = f"Unknown branch type for branch {id}: {branch_data['type']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)
    return buses, branches_dict, loads, sources, grounds, potential_refs


def network_to_dict(en: "ElectricalNetwork") -> JsonDict:
    """Return a dictionary of the current network data.

    Args:
        en:
            The electrical network.

    Returns:
        The created dictionary.
    """
    # Export the grounds and the pref
    grounds = [ground.to_dict() for ground in en.grounds.values()]
    potential_refs = [p_ref.to_dict() for p_ref in en.potential_refs.values()]

    # Export the buses, loads and sources
    buses: list[JsonDict] = []
    loads: list[JsonDict] = []
    sources: list[JsonDict] = []
    for bus in en.buses.values():
        buses.append(bus.to_dict())
        for element in bus.connected_elements:
            if isinstance(element, AbstractLoad):
                assert element.bus is bus
                loads.append(element.to_dict())
            elif isinstance(element, VoltageSource):
                assert element.bus is bus
                sources.append(element.to_dict())

    # Export the branches with their parameters
    branches: list[JsonDict] = []
    lines_params_dict: dict[Id, LineParameters] = {}
    transformers_params_dict: dict[Id, TransformerParameters] = {}
    for branch in en.branches.values():
        branches.append(branch.to_dict())
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
        line_params.append(lp.to_dict())
    line_params.sort(key=lambda x: x["id"])  # Always keep the same order

    # Transformer parameters
    transformer_params: list[JsonDict] = []
    for tp in transformers_params_dict.values():
        transformer_params.append(tp.to_dict())
    transformer_params.sort(key=lambda x: x["id"])  # Always keep the same order

    return {
        "system_info": _get_system_info(),
        "grounds": grounds,
        "potential_refs": potential_refs,
        "buses": buses,
        "branches": branches,
        "loads": loads,
        "sources": sources,
        "lines_params": line_params,
        "transformers_params": transformer_params,
    }
