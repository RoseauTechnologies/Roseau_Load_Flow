import logging
from typing import TYPE_CHECKING

from roseau.load_flow.aliases import Id, JsonDict
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    Element,
    Ground,
    Line,
    LineCharacteristics,
    PotentialRef,
    Transformer,
    TransformerCharacteristics,
    VoltageSource,
)

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork

logger = logging.getLogger(__name__)


def network_from_dict(
    data: JsonDict, en_class: type["ElectricalNetwork"]
) -> tuple[dict[str, Bus], dict[str, AbstractBranch], dict[str, AbstractLoad], dict[str, VoltageSource], list[Element]]:
    """Create the electrical elements from a dictionary to create an electrical network.

    Args:
        data:
            The dictionary containing the network data.

        en_class:
            The ElectricalNetwork class to create

    Returns:
        The buses, branches, loads, sources and special elements to construct the electrical network.
    """
    line_types: dict[str, LineCharacteristics] = {}
    for line_data in data["line_types"]:
        type_id = line_data["id"]
        line_types[type_id] = LineCharacteristics.from_dict(line_data)

    transformer_types: dict[str, TransformerCharacteristics] = {}
    for transformer_data in data["transformer_types"]:
        type_id = transformer_data["id"]
        transformer_types[type_id] = TransformerCharacteristics.from_dict(transformer_data)

    grounds: dict[Id:Ground] = {}  # en_class.ground_class()
    potential_refs: dict[Id:PotentialRef] = {}  # en_class.pref_class()
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
            ground.connect_to_bus(buses_dict[bus_id], phase)
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

    branches_dict: dict[str, AbstractBranch] = {}
    for branch_data in data["branches"]:
        bus1 = buses_dict[branch_data["bus1"]]
        bus2 = buses_dict[branch_data["bus2"]]
        ground = grounds[branch_data["ground"]] if branch_data.get("ground") is not None else None
        branches_dict[branch_data["id"]] = en_class.branch_class.from_dict(
            branch_data,
            bus1,
            bus2,
            ground,
            line_types,
            transformer_types,
        )
    special_elements = list(grounds.values()) + list(potential_refs.values())
    return buses_dict, branches_dict, loads_dict, sources_dict, special_elements


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
    for se in en.special_elements:
        if isinstance(se, Ground):
            grounds.append(se.to_dict())
        elif isinstance(se, PotentialRef):
            potential_refs.append(se.to_dict())

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

    # Export the branches with their characteristics
    branches: list[JsonDict] = []
    line_characteristics_dict: dict[Id, LineCharacteristics] = {}
    transformer_characteristics_dict: dict[Id, TransformerCharacteristics] = {}
    for branch in en.branches.values():
        branches.append(branch.to_dict())
        if isinstance(branch, Line):
            type_id = branch.line_characteristics.id
            if (
                type_id in line_characteristics_dict
                and branch.line_characteristics != line_characteristics_dict[type_id]
            ):
                msg = f"There are multiple line characteristics with {type_id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(
                    msg=msg, code=RoseauLoadFlowExceptionCode.JSON_LINE_CHARACTERISTICS_DUPLICATES
                )
            line_characteristics_dict[branch.line_characteristics.id] = branch.line_characteristics
        elif isinstance(branch, Transformer):
            type_id = branch.transformer_characteristics.id
            if (
                type_id in transformer_characteristics_dict
                and branch.transformer_characteristics != transformer_characteristics_dict[type_id]
            ):
                msg = f"There are multiple transformer characteristics with {type_id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(
                    msg=msg, code=RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_CHARACTERISTICS_DUPLICATES
                )
            transformer_characteristics_dict[type_id] = branch.transformer_characteristics

    # Line characteristics
    line_characteristics: list[JsonDict] = []
    for lc in line_characteristics_dict.values():
        line_characteristics.append(lc.to_dict())
    line_characteristics.sort(key=lambda x: x["id"])  # Always keep the same order

    # Transformer characteristics
    transformer_characteristics: list[JsonDict] = []
    for tc in transformer_characteristics_dict.values():
        transformer_characteristics.append(tc.to_dict())
    transformer_characteristics.sort(key=lambda x: x["id"])  # Always keep the same order

    return {
        "grounds": grounds,
        "potential_refs": potential_refs,
        "buses": buses,
        "branches": branches,
        "line_types": line_characteristics,
        "transformer_types": transformer_characteristics,
    }
