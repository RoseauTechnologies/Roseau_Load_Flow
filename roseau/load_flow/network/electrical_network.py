import json
import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Union
from urllib.parse import urljoin

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from pyproj import CRS
from requests import Response
from requests.auth import HTTPBasicAuth

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io import network_from_dgs, network_from_dict, network_to_dict
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractBus,
    AbstractLoad,
    AbstractTransformer,
    Element,
    FlexibleLoad,
    Ground,
    PotentialRef,
    PowerLoad,
    VoltageSource,
)
from roseau.load_flow.utils import ureg

logger = logging.getLogger(__name__)


class ElectricalNetwork:
    DEFAULT_PRECISION: float = 1e-6
    DEFAULT_MAX_ITERATIONS: int = 20
    DEFAULT_BASE_URL = "https://load-flow-api.roseautechnologies.com/"

    # Default classes to use
    branch_class = AbstractBranch
    load_class = AbstractLoad
    bus_class = AbstractBus
    ground_class = Ground
    pref_class = PotentialRef

    #
    # Methods to build an electrical network
    #
    def __init__(
        self,
        buses: Union[list[AbstractBus], dict[Any, AbstractBus]],
        branches: Union[list[AbstractBranch], dict[Any, AbstractBranch]],
        loads: Union[list[AbstractLoad], dict[Any, AbstractLoad]],
        special_elements: list[Element],
        **kwargs,
    ) -> None:
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

        self._check_validity(constructed=False)
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
    # Methods to access the data
    #
    @property
    def buses_frame(self) -> gpd.GeoDataFrame:
        """A property to get a geo dataframe of the buses.

        Returns:
            The geo dataframe of buses.
        """
        return gpd.GeoDataFrame(
            data=pd.DataFrame.from_records(
                data=[(bus_id, bus.n, bus.geometry) for bus_id, bus in self.buses.items()],
                columns=["id", "n", "geometry"],
                index="id",
            ),
            geometry="geometry",
            crs=CRS("EPSG:4326"),
        )

    @property
    def branches_frame(self) -> gpd.GeoDataFrame:
        """A property to get a geo dataframe of the branches.

        Returns:
            The geo dataframe of branches.
        """
        return gpd.GeoDataFrame(
            data=pd.DataFrame.from_records(
                data=[
                    (
                        branch_id,
                        branch.branch_type,
                        branch.n1,
                        branch.n2,
                        branch.connected_elements[0].id,
                        branch.connected_elements[1].id,
                        branch.geometry,
                    )
                    for branch_id, branch in self.branches.items()
                ],
                columns=["id", "branch_type", "n1", "n2", "bus1_id", "bus2_id", "geometry"],
                index="id",
            ),
            geometry="geometry",
            crs=CRS("EPSG:4326"),
        )

    @property
    def loads_frame(self) -> pd.DataFrame:
        """A property to get a dataframe of the loads.

        Returns:
            The dataframe of loads.
        """
        return pd.DataFrame.from_records(
            data=[(load_id, load.n, load.bus.id) for load_id, load in self.loads.items()],
            columns=["id", "n", "bus_id"],
            index="id",
        )

    #
    # Method to solve a load flow
    #
    def solve_load_flow(
        self,
        auth: Union[tuple[str, str], HTTPBasicAuth],
        base_url: str = DEFAULT_BASE_URL,
        precision: float = DEFAULT_PRECISION,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> int:
        """Execute a newton algorithm for load flow calculation. In order to get the results of the load flow, please
        use the `results` method or call the elements directly.

        Args:
            auth:
                The login and password for the roseau load flow api.

            base_url:
                The base url to request the load flow solver.

            precision:
                Precision needed for the convergence

            max_iterations:
                The maximum number of allowed iterations

        Returns:
            The number of iterations taken
        """
        if not self._valid:
            self._check_validity(constructed=True)
            self._create_network()

        # Get the data
        network_data = self.to_dict()

        # Request the server
        params = {"max_iterations": max_iterations, "precision": precision}
        response = requests.post(
            url=urljoin(base_url, "solve/"),
            params=params,
            json=network_data,
            auth=auth,
            headers={"accept": "application/json"},
        )

        # Read the response
        # HTTP 4xx,5xx
        if not response.ok:
            self._parse_error(response=response)

        # HTTP 200
        result_dict: dict[str, Any] = response.json()
        info = result_dict["info"]
        if info["status"] != "success":
            msg = (
                f"The load flow did not converge after {info['iterations']} iterations. The norm of the residuals is "
                f"{info['finalError']:.5n}"
            )
            logger.error(msg=msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE)

        logger.info(
            f"The load flow converged after {info['iterations']} iterations (final error={info['finalError']:.5n})."
        )

        # Dispatch the results
        self._dispatch_results(result_dict=result_dict)

        return info["iterations"]

    @staticmethod
    def _parse_error(response: Response):
        """Parse a response when its status is not "ok".

        Args:
            response:
                The response to parse
        """
        content_type = response.headers.get("content-type", None)
        if response.status_code == 401:
            msg = "Authentication failed."
            logger.error(msg=msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REQUEST)
        else:
            msg = f"There is a problem in the request. Error code {response.status_code}."
            if content_type == "application/json":
                result_dict: dict[str, Any] = response.json()

                # If we have a valid Roseau Load Flow Exception, raise it
                if "msg" in result_dict and "code" in result_dict:
                    try:
                        code = RoseauLoadFlowExceptionCode.from_string(result_dict["code"])
                    except Exception:
                        msg += f" {result_dict['code']} - {result_dict['msg']}"
                    else:
                        msg = result_dict["msg"]
                        logger.error(msg)
                        raise RoseauLoadFlowException(msg=msg, code=code)
            else:
                msg += response.text

            # Otherwise, raise a generic "Bad request"
            logger.error(msg=msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REQUEST)

    def _dispatch_results(self, result_dict: dict[str, Any]) -> None:
        """Dispatch the results to all the elements of the network.

        Args:
            result_dict:
                The results returned by the solver.
        """
        for bus_data in result_dict["buses"]:
            bus_id = bus_data["id"]
            self.buses[bus_id].potentials = self._dispatch_value(bus_data["potentials"], "v")
        for branch_data in result_dict["branches"]:
            branch_id = branch_data["id"]
            currents1 = self._dispatch_value(branch_data["currents1"], "i")
            currents2 = self._dispatch_value(branch_data["currents2"], "i")
            self.branches[branch_id].currents = [currents1, currents2]
        for load_data in result_dict["loads"]:
            load_id = load_data["id"]
            load = self.loads[load_id]
            if isinstance(load, FlexibleLoad):
                load.powers = self._dispatch_value(load_data["powers"], "s")
            currents = self._dispatch_value(load_data["currents"], "i")
            load.currents = currents

    @staticmethod
    def _dispatch_value(value: dict[str, tuple[float, float]], t: str) -> np.ndarray:
        """Dispatch the currents from a dictionary to a list.

        Args:
            value:
                The dictionary value to dispatch.

            t:
                The type of value ("i", "v" or "s").

        Returns:
            The complex final value.
        """
        if t + "n" in value:
            res = [
                value[t + "a"][0] + 1j * value[t + "a"][1],
                value[t + "b"][0] + 1j * value[t + "b"][1],
                value[t + "c"][0] + 1j * value[t + "c"][1],
                value[t + "n"][0] + 1j * value[t + "n"][1],
            ]
        else:
            res = [
                value[t + "a"][0] + 1j * value[t + "a"][1],
                value[t + "b"][0] + 1j * value[t + "b"][1],
                value[t + "c"][0] + 1j * value[t + "c"][1],
            ]
        return np.asarray(res)

    #
    # Getter for the load flow results
    #
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

    @property
    def buses_potentials(self) -> pd.DataFrame:
        """Get the potentials of buses after a load flow has been solved.

        Returns:
            The data frame of the potentials of the buses of the electrical network.
        """
        phases = ["a", "b", "c", "n"]
        potentials_dict = {"bus_id": [], "phase": [], "potential": []}
        for bus_id, bus in self.buses.items():
            potentials: np.ndarray = bus.potentials
            for i in range(len(potentials)):
                potentials_dict["bus_id"].append(bus_id)
                potentials_dict["phase"].append(phases[i])
                potentials_dict["potential"].append(potentials[i].m_as("V"))
        potentials_df: pd.DataFrame = (
            pd.DataFrame.from_dict(potentials_dict, orient="columns")
            .astype({"phase": pd.CategoricalDtype(categories=phases, ordered=True), "potential": complex})
            .set_index(["bus_id", "phase"])
        )
        return potentials_df

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

    @property
    def branches_currents(self) -> pd.DataFrame:
        """Get the currents of the branches after a load flow has been solved.

        Returns:
            The data frame of the currents of the branches of the electrical network.
        """
        phases = ["a", "b", "c", "n"]
        currents_dict = {"branch_id": [], "phase": [], "current1": [], "current2": []}
        for branch_id, branch in self.branches.items():
            currents1, currents2 = branch.currents
            nb_currents1, nb_currents2 = len(currents1), len(currents2)
            for j in range(max(nb_currents1, nb_currents2)):
                currents_dict["branch_id"].append(branch_id)
                currents_dict["phase"].append(phases[j])
                try:
                    currents_dict["current1"].append(currents1[j].m_as("A"))
                except IndexError:
                    currents_dict["current1"].append(np.nan)
                try:
                    currents_dict["current2"].append(currents2[j].m_as("A"))
                except IndexError:
                    currents_dict["current2"].append(np.nan)
        currents_df = (
            pd.DataFrame.from_dict(currents_dict, orient="columns")
            .astype(
                {
                    "phase": pd.CategoricalDtype(categories=phases, ordered=True),
                    "current1": complex,
                    "current2": complex,
                }
            )
            .set_index(["branch_id", "phase"])
        )
        return currents_df

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

    @property
    def loads_currents(self) -> pd.DataFrame:
        """Get the currents of the loads after a load flow has been solved.

        Returns:
            The data frame of the currents of the loads of the electrical network.
        """
        phases = ["a", "b", "c", "n"]
        loads_dict = {"load_id": [], "phase": [], "current": []}
        for load_id, load in self.loads.items():
            currents = load.currents
            for i in range(len(currents)):
                loads_dict["load_id"].append(load_id)
                loads_dict["phase"].append(phases[i])
                loads_dict["current"].append(currents[i].m_as("A"))
        currents_df: pd.DataFrame = (
            pd.DataFrame.from_dict(loads_dict, orient="columns")
            .astype({"phase": pd.CategoricalDtype(categories=phases, ordered=True), "current": complex})
            .set_index(["load_id", "phase"])
        )
        return currents_df

    @property
    def loads_powers(self) -> pd.DataFrame:
        """Get the powers of the loads after a load flow has been solved. Only for FlexibleLoads.

        Returns:
            The data frame of the powers of the loads of the electrical network.
        """
        phases = ["a", "b", "c", "n"]
        loads_dict = {"load_id": [], "phase": [], "power": []}
        for load_id, load in self.loads.items():
            if isinstance(load, FlexibleLoad):
                powers = load.powers
                for i in range(len(powers)):
                    loads_dict["load_id"].append(load_id)
                    loads_dict["phase"].append(phases[i])
                    loads_dict["power"].append(powers[i].m_as("VA"))
        powers_df: pd.DataFrame = (
            pd.DataFrame.from_dict(loads_dict, orient="columns")
            .astype({"phase": pd.CategoricalDtype(categories=phases, ordered=True), "power": complex})
            .set_index(["load_id", "phase"])
        )
        return powers_df

    #
    # Set the dynamic parameters.
    #
    def set_load_point(self, load_point: dict[Any, Sequence[complex]]) -> None:
        """Set a new load point to the network

        Args:
            load_point:
                The new load point
        """
        for load_id, value in load_point.items():
            load: AbstractLoad = self.loads[load_id]
            if isinstance(load, PowerLoad) or isinstance(load, FlexibleLoad):
                load.update_powers(value)
            else:
                msg = "Only power loads can be updated yet..."
                logger.error(msg)
                raise NotImplementedError(msg)

    def set_source_voltages(self, voltages: dict[Any, Sequence[complex]]) -> None:
        """Set new voltages for the voltage source

        Args:
            voltages:
                A dictionary voltage_source_id -> voltages to update
        """
        for bus_id, value in voltages.items():
            voltage_source = self.buses[bus_id]
            if not isinstance(voltage_source, VoltageSource):
                msg = "Only voltage sources can have their voltages updated."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
            voltage_source.update_source_voltages(source_voltages=value)

    def add_element(self, element: Element) -> None:
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

    def remove_element(self, id: Any) -> None:
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

    def _create_network(self) -> None:
        """Create the Cython and C++ electrical network of all the passed elements"""
        self._valid = True

    def _check_validity(self, constructed: bool) -> None:
        """Check the validity of the network to avoid having a singular jacobian matrix

        Args:
            constructed:
                True if the network is already constructed and we have added an element, False otherwise
        """
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
                    if constructed:
                        msg = (
                            f"The element {adj_id!r} is connected to {element_id!r} but is not in the "
                            f"ElectricalNetwork constructor."
                        )
                    else:
                        msg = (
                            f"The element {adj_id!r} is connected to {element_id!r} but has not been added to the "
                            f"network, you should add it with 'add_element'."
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
    def _check_ref(elements) -> None:
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
                if isinstance(element, PotentialRef):
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
        buses_dict, branches_dict, loads_dict, special_elements = network_from_dict(data=data, en_class=cls)
        return cls(buses=buses_dict, branches=branches_dict, loads=loads_dict, special_elements=special_elements)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "ElectricalNetwork":
        """ElectricalNetwork constructor from json.

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

    def to_json(self, path: Union[str, Path]) -> None:
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
    # Output of results
    #
    def results_to_dict(self) -> dict[str, Any]:
        """Get the voltages and currents computed by the load flow and return them as dict.

        Returns:
            The dictionary of the voltages of the buses, and the dictionary of the current flowing through the branches.
        """
        phases = ["a", "b", "c", "n"]
        buses_results = list()
        for bus_id, bus in self.buses.items():
            potentials: np.ndarray = bus.potentials
            potentials_dict = dict()
            for i in range(len(potentials)):
                potentials_dict[f"v{phases[i]}"] = [potentials[i].real.magnitude, potentials[i].imag.magnitude]
            buses_results.append({"id": bus_id, "potentials": potentials_dict})

        branches_results = list()
        for branch_id, branch in self.branches.items():
            currents1: np.ndarray = branch.currents[0]
            currents2: np.ndarray = branch.currents[1]
            currents_dict1 = dict()
            currents_dict2 = dict()
            for i in range(len(currents1)):
                currents_dict1[f"i{phases[i]}"] = [currents1[i].real.magnitude, currents1[i].imag.magnitude]
            for i in range(len(currents2)):
                currents_dict2[f"i{phases[i]}"] = [currents2[i].real.magnitude, currents2[i].imag.magnitude]
            branches_results.append({"id": branch_id, "currents1": currents_dict1, "currents2": currents_dict2})

        loads_results = list()
        for load_id, load in self.loads.items():
            currents: np.ndarray = load.currents
            currents_dict = dict()
            for i in range(len(currents)):
                currents_dict[f"i{phases[i]}"] = [currents[i].real.magnitude, currents[i].imag.magnitude]
            if isinstance(load, FlexibleLoad):
                powers: np.ndarray = load.powers
                powers_dict = dict()
                for i in range(len(powers)):
                    powers_dict[f"s{phases[i]}"] = [powers[i].real.magnitude, powers[i].imag.magnitude]
                loads_results.append({"id": load_id, "powers": powers_dict, "currents": currents_dict})
            else:
                loads_results.append({"id": load_id, "currents": currents_dict})

        return {
            "info": self._results_info,
            "buses": buses_results,
            "branches": branches_results,
            "loads": loads_results,
        }

    def results_to_json(self, path: Union[str, Path]) -> Path:
        """Write a json containing the voltages and currents results.

        Args:
            path:
                The path to write the json.

        Returns:
            The path it has been writen in.
        """
        if isinstance(path, str):
            path = Path(path).expanduser().resolve()

        dict_results = self.results_to_dict()
        output = json.dumps(dict_results, indent=4)
        output = re.sub(r"\[\s+(.*),\s+(.*)\s+]", r"[\1, \2]", output)
        path.write_text(output)
        return path

    #
    # DGS interface
    #
    @classmethod
    def from_dgs(cls, path: Union[str, Path]) -> "ElectricalNetwork":
        """ElectricalNetwork constructor from json dgs file (PowerFactory).

        Args:
            path:
                The path to the network data.

        Returns:
            The constructed network.
        """
        buses_dict, branches_dict, loads_dict, special_elements = network_from_dgs(filename=path)
        return cls(buses=buses_dict, branches=branches_dict, loads=loads_dict, special_elements=special_elements)
