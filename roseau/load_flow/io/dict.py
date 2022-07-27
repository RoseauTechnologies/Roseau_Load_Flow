import collections
import logging
from typing import Any, TYPE_CHECKING

from roseau.load_flow import (
    AbstractBranch,
    AbstractBus,
    AbstractTransformer,
    Ground,
    Line,
    LineCharacteristics,
    PotentialReference,
    TransformerCharacteristics,
)
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.loads.loads import AbstractLoad
from roseau.load_flow.utils.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork

logger = logging.getLogger(__name__)


def network_from_dict(
    data: dict[str, Any]
) -> tuple[dict[str, AbstractBus], dict[str, AbstractBranch], dict[str, AbstractLoad], list[Element]]:
    """Create the electrical elements from a dictionary to create an electrical network.

    Args:
        data:
            The dictionary containing the network data.

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

    ground = Ground()
    special_elements = [ground, PotentialReference(element=ground)]
    buses_dict = dict()
    loads_dict = dict()
    for bus_data in data["buses"]:
        buses_dict[bus_data["id"]] = AbstractBus.from_dict(bus_data, ground)
        for load_data in bus_data["loads"]:
            loads_dict[load_data["id"]] = AbstractLoad.from_dict(load_data, buses_dict[bus_data["id"]])

    branches_dict = dict()
    for branch_data in data["branches"]:
        bus1 = buses_dict[branch_data["bus1"]]
        bus2 = buses_dict[branch_data["bus2"]]
        branches_dict[branch_data["id"]] = AbstractBranch.from_dict(
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
                special_elements.append(PotentialReference(element=bus2))

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
    line_characteristics_set = set()
    transformer_characteristics_set = set()
    for branch in en.branches.values():
        branches.append(branch.to_dict())
        if isinstance(branch, Line):
            line_characteristics_set.add(branch.line_characteristics)
        elif isinstance(branch, AbstractTransformer):
            transformer_characteristics_set.add(branch.transformer_characteristics)

    # Line characteristics
    line_characteristics = list()
    for lc in line_characteristics_set:
        line_characteristics.append(lc.to_dict())
    line_characteristics.sort(key=lambda x: x["name"])  # Always keep the same order
    line_characteristic_names = [lc.type_name for lc in line_characteristics_set]
    if len(line_characteristic_names) > len(set(line_characteristic_names)):
        duplicates = ", ".join(
            [repr(str(item)) for item, count in collections.Counter(line_characteristic_names).items() if count > 1]
        )
        msg = f"There are line characteristics type name duplicates: {duplicates}"
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_LINE_CHARACTERISTICS_DUPLICATES)

    # Transformer characteristics
    transformer_characteristics = list()
    for tc in transformer_characteristics_set:
        transformer_characteristics.append(tc.to_dict())
    transformer_characteristics.sort(key=lambda x: x["name"])  # Always keep the same order
    transformer_characteristics_names = [tc.type_name for tc in transformer_characteristics_set]
    if len(transformer_characteristics) > len(set(transformer_characteristics_names)):
        duplicates = ", ".join(
            [
                repr(str(item))
                for item, count in collections.Counter(transformer_characteristics_names).items()
                if count > 1
            ]
        )
        msg = f"There are transformer characteristics type name duplicates: {duplicates}"
        logger.error(msg)
        raise RoseauLoadFlowException(
            msg=msg, code=RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_CHARACTERISTICS_DUPLICATES
        )

    return {
        "buses": buses,
        "branches": branches,
        "line_types": line_characteristics,
        "transformer_types": transformer_characteristics,
    }
