import logging
from typing import Any, TYPE_CHECKING

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractBus,
    AbstractLine,
    AbstractLoad,
    AbstractTransformer,
    Element,
    LineCharacteristics,
    TransformerCharacteristics,
)

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork

logger = logging.getLogger(__name__)


def network_from_dict(
    data: dict[str, Any], en_class: type["ElectricalNetwork"]
) -> tuple[dict[str, AbstractBus], dict[str, AbstractBranch], dict[str, AbstractLoad], list[Element]]:
    """Create the electrical elements from a dictionary to create an electrical network.

    Args:
        data:
            The dictionary containing the network data.

        en_class:
            The ElectricalNetwork class to create

    Returns:
        The buses, branches, loads and special elements to construct the electrical network.
    """
    line_types = dict()
    for line_data in data["line_types"]:
        type_name = line_data["name"]
        line_types[type_name] = LineCharacteristics.from_dict(line_data)

    transformer_types = dict()
    for transformer_data in data["transformer_types"]:
        type_name = transformer_data["name"]
        transformer_types[type_name] = TransformerCharacteristics.from_dict(transformer_data)

    ground = en_class.ground_class()
    special_elements = [ground, en_class.pref_class(element=ground)]
    buses_dict = dict()
    loads_dict = dict()
    for bus_data in data["buses"]:
        buses_dict[bus_data["id"]] = en_class.bus_class.from_dict(bus_data, ground)
        for load_data in bus_data["loads"]:
            loads_dict[load_data["id"]] = en_class.load_class.from_dict(load_data, buses_dict[bus_data["id"]])

    branches_dict = dict()
    for branch_data in data["branches"]:
        bus1 = buses_dict[branch_data["bus1"]]
        bus2 = buses_dict[branch_data["bus2"]]
        branches_dict[branch_data["id"]] = en_class.branch_class.from_dict(
            branch_data,
            bus1,
            bus2,
            ground,
            line_types,
            transformer_types,
        )
        if isinstance(branches_dict[branch_data["id"]], AbstractTransformer):
            if bus2.n == 4:
                ground.connect(bus2)
            else:
                special_elements.append(en_class.pref_class(element=bus2))

    return buses_dict, branches_dict, loads_dict, special_elements


def network_to_dict(en: "ElectricalNetwork") -> dict[str, Any]:
    """Return a dictionary of the current network data.

    Args:
        en:
            The electrical network.

    Returns:
        The created dictionary.
    """
    # Export the buses and the loads
    buses = list()
    for bus in en.buses.values():
        bus_dict = bus.to_dict()
        for load in bus.connected_elements:
            if isinstance(load, AbstractLoad):
                bus_dict["loads"].append(load.to_dict())
        buses.append(bus_dict)

    # Export the branches with their characteristics
    branches = list()
    line_characteristics_dict = dict()
    transformer_characteristics_dict = dict()
    for branch in en.branches.values():
        branches.append(branch.to_dict())
        if isinstance(branch, AbstractLine):
            type_name = branch.line_characteristics.type_name
            if (
                type_name in line_characteristics_dict
                and branch.line_characteristics != line_characteristics_dict[type_name]
            ):
                msg = f"There are line characteristics duplicates: {type_name}"
                logger.error(msg)
                raise RoseauLoadFlowException(
                    msg=msg, code=RoseauLoadFlowExceptionCode.JSON_LINE_CHARACTERISTICS_DUPLICATES
                )
            line_characteristics_dict[branch.line_characteristics.type_name] = branch.line_characteristics
        elif isinstance(branch, AbstractTransformer):
            type_name = branch.transformer_characteristics.type_name
            if (
                type_name in transformer_characteristics_dict
                and branch.transformer_characteristics != transformer_characteristics_dict[type_name]
            ):
                msg = f"There are transformer characteristics duplicates: {type_name}"
                logger.error(msg)
                raise RoseauLoadFlowException(
                    msg=msg, code=RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_CHARACTERISTICS_DUPLICATES
                )
            transformer_characteristics_dict[type_name] = branch.transformer_characteristics

    # Line characteristics
    line_characteristics = list()
    for lc in line_characteristics_dict.values():
        line_characteristics.append(lc.to_dict())
    line_characteristics.sort(key=lambda x: x["name"])  # Always keep the same order

    # Transformer characteristics
    transformer_characteristics = list()
    for tc in transformer_characteristics_dict.values():
        transformer_characteristics.append(tc.to_dict())
    transformer_characteristics.sort(key=lambda x: x["name"])  # Always keep the same order

    return {
        "buses": buses,
        "branches": branches,
        "line_types": line_characteristics,
        "transformer_types": transformer_characteristics,
    }
