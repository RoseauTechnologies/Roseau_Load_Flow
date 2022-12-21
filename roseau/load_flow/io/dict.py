import logging
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
    lines_params = {lp["id"]: LineParameters.from_dict(lp) for lp in data["lines_params"]}
    transformers_params = {tp["id"]: TransformerParameters.from_dict(tp) for tp in data["transformers_params"]}

    grounds: dict[Id, Ground] = {}
    potential_refs: dict[Id, PotentialRef] = {}
    buses_dict: dict[Id, Bus] = {}
    loads_dict: dict[Id, AbstractLoad] = {}
    sources_dict: dict[Id, VoltageSource] = {}
    for bus_data in data["buses"]:
        buses_dict[bus_data["id"]] = en_class.bus_class.from_dict(bus_data)
        for load_data in bus_data["loads"]:
            loads_dict[load_data["id"]] = en_class.load_class.from_dict(load_data, buses_dict[bus_data["id"]])
        for source_data in bus_data["sources"]:
            sources_dict[source_data["id"]] = en_class.voltage_source_class.from_dict(
                source_data, buses_dict[bus_data["id"]]
            )
    for ground_data in data["grounds"]:
        ground = en_class.ground_class.from_dict(ground_data)
        for bus_id, phase in ground_data["buses"].items():
            ground.connect(buses_dict[bus_id], phase)
        grounds[ground_data["id"]] = ground
    for pref_data in data["potential_refs"]:
        if "bus" in pref_data:
            bus_or_ground = buses_dict[pref_data.pop("bus")]
        elif "ground" in pref_data:
            bus_or_ground = grounds[pref_data.pop("ground")]
        else:
            msg = f"Potential reference data {pref_data['id']} missing bus or ground."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.JSON_PREF_INVALID)
        pref_data["element"] = bus_or_ground
        potential_refs[pref_data["id"]] = en_class.pref_class.from_dict(pref_data)

    branches_dict: dict[Id, AbstractBranch] = {}
    for branch_data in data["branches"]:
        bus1 = buses_dict[branch_data["bus1"]]
        bus2 = buses_dict[branch_data["bus2"]]
        ground = grounds[branch_data["ground"]] if branch_data.get("ground") is not None else None
        branches_dict[branch_data["id"]] = en_class.branch_class.from_dict(
            branch_data,
            bus1,
            bus2,
            ground,
            lines_params,
            transformers_params,
        )
    return buses_dict, branches_dict, loads_dict, sources_dict, grounds, potential_refs


def network_to_dict(en: "ElectricalNetwork") -> JsonDict:
    """Return a dictionary of the current network data.

    Args:
        en:
            The electrical network.

    Returns:
        The created dictionary.
    """
    # Export the grounds and the pref
    grounds: list[JsonDict] = []
    potential_refs: list[JsonDict] = []
    for ground in en.grounds.values():
        grounds.append(ground.to_dict())
    for p_ref in en.potential_refs.values():
        potential_refs.append(p_ref.to_dict())

    # Export the buses and the loads
    buses: list[JsonDict] = []
    for bus in en.buses.values():
        bus_dict = bus.to_dict()
        for element in bus.connected_elements:
            if isinstance(element, AbstractLoad):
                bus_dict["loads"].append(element.to_dict())
            elif isinstance(element, VoltageSource):
                bus_dict["sources"].append(element.to_dict())
        buses.append(bus_dict)

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
        "grounds": grounds,
        "potential_refs": potential_refs,
        "buses": buses,
        "branches": branches,
        "lines_params": line_params,
        "transformers_params": transformer_params,
    }
