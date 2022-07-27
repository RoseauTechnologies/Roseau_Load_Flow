import json
import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Union

import numpy as np
import pandas as pd

from roseau.load_flow.io.dgs import network_from_dgs
from roseau.load_flow.io.dict import network_from_dict, network_to_dict
from roseau.load_flow.models.buses import AbstractBus, VoltageSource
from roseau.load_flow.models.core import AbstractBranch, Element, PotentialReference
from roseau.load_flow.models.loads.loads import AbstractLoad, PowerLoad
from roseau.load_flow.models.transformers.transformers import AbstractTransformer
from roseau.load_flow.utils import ureg
from roseau.load_flow.utils.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

logger = logging.getLogger(__name__)


class ElectricalNetwork:
    DEFAULT_PRECISION: float = 1e-6
    DEFAULT_MAX_ITERATIONS: int = 20

    def __init__(
        self,
        buses: Union[list[AbstractBus], dict[Any, AbstractBus]],
        branches: Union[list[AbstractBranch], dict[Any, AbstractBranch]],
        loads: Union[list[AbstractLoad], dict[Any, AbstractLoad]],
        special_elements: list[Element],
        **kwargs,
    ):
        """ElectricalNetwork constructor

        Args:
            buses:
                The buses of the network

            branches:
                The branches of the network

            loads:
                The loads of the network

            special_elements:
                The other elements (special, ground...)
        """
        if isinstance(buses, list):
            buses_dict = dict()
            for bus in buses:
                if bus.id in buses_dict:
                    msg = f"Duplicate id for a bus in this network: {bus.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DUPLICATE_BUS_ID)
                buses_dict[bus.id] = bus
            buses = buses_dict
        if isinstance(branches, list):
            branches_dict = dict()
            for branch in branches:
                if branch.id in branches_dict:
                    msg = f"Duplicate id for a branch in this network: {branch.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DUPLICATE_BRANCH_ID)
                branches_dict[branch.id] = branch
            branches = branches_dict
        if isinstance(loads, list):
            loads_dict = dict()
            for load in loads:
                if load.id in loads_dict:
                    msg = f"Duplicate id for a load in this network: {load.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DUPLICATE_LOAD_ID)
                loads_dict[load.id] = load
            loads = loads_dict

        self.buses: dict[Any, AbstractBus] = buses
        self.branches: dict[Any, AbstractBranch] = branches
        self.loads: dict[Any, AbstractLoad] = loads
        self.special_elements: list[Element] = special_elements

        self._create_network()
        self._valid = True
        self._results_info: dict[str, Any] = dict()

    @classmethod
    def from_element(cls, initial_bus: AbstractBus) -> "ElectricalNetwork":
        """ElectricalNetwork constructor. Construct the network from only one element and add the others automatically

        Args:
            initial_bus:
                Any bus of the network
        """
        buses = []
        branches = []
        loads = []
        specials = []
        elements = [initial_bus]
        visited_elements = []
        while elements:
            e = elements.pop(-1)
            visited_elements.append(e)
            if isinstance(e, AbstractBus):
                buses.append(e)
            elif isinstance(e, AbstractBranch):
                branches.append(e)
            elif isinstance(e, AbstractLoad):
                loads.append(e)
            else:
                specials.append(e)
            for connected_element in e.connected_elements:
                if connected_element not in visited_elements and connected_element not in elements:
                    elements.append(connected_element)
        return cls(buses=buses, branches=branches, loads=loads, special_elements=specials)

    #
    # Solve the load flow
    #
    def solve_load_flow(self, epsilon: float = DEFAULT_PRECISION, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> int:
        """Execute a newton algorithm for load flow calculation. In order to get the results of the load flow, please
        use the `get_results` method or call the elements directly.

        Args:
            epsilon:
                Precision needed for the convergence

            max_iterations:
                The maximum number of allowed iterations

        Returns:
            The number of iterations taken
        """
        # TODO Call requests ad store the results in the class and subsequents objects
        return 0

    #
    # Getter for the load flow results
    #
    @property
    def results(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get the voltages and currents computed by the load flow

        Returns:
            The DataFrame of the voltages of the buses indexed by the bus ids and the DataFrame of the current
            flowing through the branches indexed by the branch ids.
        """
        # TODO Retrieve the result objects
        # TODO use pint-pandas (?)
        raise NotImplementedError

    @ureg.wraps("V", (None, None), strict=False)
    def bus_potentials(self, id: Any) -> np.ndarray:
        """Compute the potential of a bus

        Args:
            id:
                The id of the bus

        Returns:
            The complex value of the bus potential
        """
        return self.buses[id].potentials

    @ureg.wraps(("A", "A"), (None, None), strict=False)
    def branch_currents(self, id: Any) -> tuple[np.ndarray, np.ndarray]:
        """Compute the current of a branch

        Args:
            id:
                The name of the branch

        Returns:
            The complex value of the branch current
        """
        return self.branches[id].currents

    @ureg.wraps("A", (None, None), strict=False)
    def load_currents(self, id: Any) -> np.ndarray:
        """Compute the currents of a load

        Args:
            id:
                The id of the load

        Returns:
            The complex value of the branch current
        """
        return self.loads[id].currents

    #
    # Set the dynamic parameters.
    #
    def set_load_point(self, load_point: dict[Any, Sequence[complex]]):
        """Set a new load point to the network

        Args:
            load_point:
                The new load point
        """
        for load_id, value in load_point.items():
            load: AbstractLoad = self.loads[load_id]
            if isinstance(load, PowerLoad):
                load.update_powers(value)
            else:
                msg = "Only power loads can be updated yet..."
                logger.error(msg)
                raise NotImplementedError(msg)

    def set_source_voltages(self, voltages: Sequence[complex]):
        """Set new voltages for the voltage source

        Args:
            voltages:
                The new voltages
        """
        # TODO: give an id here and apply the new voltage to this bus_id (or a dictionary as set_load_point)
        for bus in self.buses.values():
            if isinstance(bus, VoltageSource):
                bus.update_voltages(voltages=voltages)

    def add_element(self, element: Element):
        """Add an element to the network (the C++ electrical network and the tape will be recomputed).

        Args:
            element:
                The element to add.
        """
        if isinstance(element, AbstractBus):
            self.buses[element.id] = element
        elif isinstance(element, AbstractLoad):
            self.loads[element.id] = element
        elif isinstance(element, AbstractBranch):
            self.branches[element.id] = element
        else:
            msg = "Only lines, loads and buses can be added to the network."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        self._valid = False

    def remove_element(self, id: Any):
        """Remove an element of the network (the C++ electrical network and the tape will be recomputed).

        Args:
            id:
                The id of the element to remove.
        """
        if id in self.buses:
            bus = self.buses.pop(id)
            bus.disconnect()
        elif id in self.loads:
            load = self.loads.pop(id)
            load.disconnect()
        elif id in self.branches:
            branch = self.branches.pop(id)
            branch.disconnect()
        else:
            msg = f"{id!r} is not a valid bus, branch or load id."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_ID)
        self._valid = False

    def _create_network(self):
        """Create the Cython and C++ electrical network of all the passed elements"""
        self._check_validity()

    def _check_validity(self):
        """Check the validity of the network to avoid having a singular jacobian matrix"""
        elements: list[Element] = list(self.buses.values())
        elements += list(self.branches.values())
        elements += list(self.loads.values())
        elements += self.special_elements

        for element in elements:
            for adj_element in element.connected_elements:
                if adj_element not in elements:
                    try:
                        adj_id = adj_element.id
                    except AttributeError:
                        adj_id = type(adj_element).__name__
                    try:
                        element_id = element.id
                    except AttributeError:
                        element_id = type(element).__name__
                    msg = (
                        f"The element {adj_id!r} is connected to {element_id!r} but is not in the ElectricalNetwork "
                        f"constructor."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT)

        found_source = False
        for element in elements:
            if isinstance(element, VoltageSource):
                found_source = True
        if not found_source:
            msg = "There is no voltage source provided in the network, you must provide at least one."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE)

        self._check_ref(elements)

    @staticmethod
    def _check_ref(elements):
        """Check the number of potential references to avoid having a singular jacobian matrix"""
        visited_elements = []
        for initial_element in elements:
            if initial_element in visited_elements or isinstance(initial_element, AbstractTransformer):
                continue
            visited_elements.append(initial_element)
            connected_component = []
            to_visit = [initial_element]
            while to_visit:
                element = to_visit.pop(-1)
                connected_component.append(element)
                for connected_element in element.connected_elements:
                    if connected_element not in visited_elements and not isinstance(
                        connected_element, AbstractTransformer
                    ):
                        to_visit.append(connected_element)
                        visited_elements.append(connected_element)

            potential_ref = 0
            for element in connected_component:
                if isinstance(element, PotentialReference):
                    potential_ref += 1

            if potential_ref == 0:
                msg = (
                    f"The connected component containing the element {initial_element.id!r} does not have a "
                    f"potential reference."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE)
            elif potential_ref >= 2:
                msg = (
                    f"The connected component containing the element {initial_element.id!r} has {potential_ref} "
                    f"potential references, it should have only one."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.SEVERAL_POTENTIAL_REFERENCE)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ElectricalNetwork":
        """ElectricalNetwork constructor from dict.

        Args:
            data:
                The dictionary containing the network data.

        Returns:
            The constructed network.
        """
        buses_dict, branches_dict, loads_dict, special_elements = network_from_dict(data=data)
        return cls(buses=buses_dict, branches=branches_dict, loads=loads_dict, special_elements=special_elements)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "ElectricalNetwork":
        """ElectricalNetwork constructor from dict.

        Args:
            path:
                The path to the network data.

        Returns:
            The constructed network.
        """
        if not isinstance(path, Path):
            path = Path(path)
        data = json.loads(path.read_text())
        return cls.from_dict(data=data)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary of the current network data.

        Returns:
            The created dictionary.
        """
        return network_to_dict(self)

    def to_json(self, path: Union[str, Path]):
        """Save the current network to a json file.

        Args:
            path:
                The path for the network output.
        """
        res = self.to_dict()
        output = json.dumps(res, ensure_ascii=False, indent=4)
        output = re.sub(r"\[\s+(.*),\s+(.*)\s+]", r"[\1, \2]", output)
        if not isinstance(path, Path):
            path = Path(path)
        path.write_text(output)

    #
    # DGS interface
    #
    @classmethod
    def from_dgs(cls, path: Union[str, Path]):
        """ElectricalNetwork constructor from json dgs file (PowerFactory).

        Args:
            path:
                The path to the network data.

        Returns:
            The constructed network.
        """
        buses_dict, branches_dict, loads_dict, special_elements = network_from_dgs(filename=path)
        return cls(buses=buses_dict, branches=branches_dict, loads=loads_dict, special_elements=special_elements)
