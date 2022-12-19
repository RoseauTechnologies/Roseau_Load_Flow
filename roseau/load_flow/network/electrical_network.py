import json
import logging
import re
from collections.abc import Sequence, Sized
from pathlib import Path
from typing import Any, Optional, Union
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
    AbstractLoad,
    Bus,
    Element,
    FlexibleLoad,
    Ground,
    PotentialRef,
    PowerLoad,
    Transformer,
    VoltageSource,
)
from roseau.load_flow.utils import ureg

logger = logging.getLogger(__name__)

# Phases dtype for all data frames
_PHASE_DTYPE = pd.CategoricalDtype(categories=["a", "b", "c", "n"], ordered=True)
# Phases dtype for voltage data frames
_VOLTAGE_PHASES_DTYPE = pd.CategoricalDtype(["an", "bn", "cn", "ab", "bc", "ca"], ordered=True)


class ElectricalNetwork:
    DEFAULT_PRECISION: float = 1e-6
    DEFAULT_MAX_ITERATIONS: int = 20
    DEFAULT_BASE_URL = "https://load-flow-api.roseautechnologies.com/"

    # Default classes to use
    branch_class = AbstractBranch
    load_class = AbstractLoad
    voltage_source_class = VoltageSource
    bus_class = Bus
    ground_class = Ground
    pref_class = PotentialRef

    #
    # Methods to build an electrical network
    #
    def __init__(
        self,
        buses: Union[list[Bus], dict[Any, Bus]],
        branches: Union[list[AbstractBranch], dict[Any, AbstractBranch]],
        loads: Union[list[AbstractLoad], dict[Any, AbstractLoad]],
        voltage_sources: Union[list[VoltageSource], dict[Any, VoltageSource]],
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

            voltage_sources:
                The voltage sources of the network

            special_elements:
                The other elements (special, ground...)
        """
        if isinstance(buses, list):
            buses_dict = {}
            for bus in buses:
                if bus.id in buses_dict:
                    msg = f"Duplicate id for a bus in this network: {bus.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DUPLICATE_BUS_ID)
                buses_dict[bus.id] = bus
            buses = buses_dict
        if isinstance(branches, list):
            branches_dict = {}
            for branch in branches:
                if branch.id in branches_dict:
                    msg = f"Duplicate id for a branch in this network: {branch.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DUPLICATE_BRANCH_ID)
                branches_dict[branch.id] = branch
            branches = branches_dict
        if isinstance(loads, list):
            loads_dict = {}
            for load in loads:
                if load.id in loads_dict:
                    msg = f"Duplicate id for a load in this network: {load.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DUPLICATE_LOAD_ID)
                loads_dict[load.id] = load
            loads = loads_dict

        if isinstance(voltage_sources, list):
            sources_dict = {}
            for voltage_source in voltage_sources:
                if voltage_source.id in sources_dict:
                    msg = f"Duplicate id for a voltage source in this network: {voltage_source.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DUPLICATE_VOLTAGE_SOURCE_ID)
                sources_dict[voltage_source.id] = voltage_source
            voltage_sources = sources_dict

        self.buses: dict[Any, Bus] = buses
        self.branches: dict[Any, AbstractBranch] = branches
        self.loads: dict[Any, AbstractLoad] = loads
        self.voltage_sources: dict[Any, VoltageSource] = voltage_sources
        self.special_elements: list[Element] = special_elements

        self._check_validity(constructed=False)
        self._create_network()
        self._valid = True
        self._results_info: dict[str, Any] = {}

    def __repr__(self) -> str:
        def count_repr(__o: Sized, /, singular: str, plural: Optional[str] = None) -> str:
            """Singular/plural count representation: `1 bus` or `2 buses`."""
            n = len(__o)
            if n == 1:
                return f"{n} {singular}"
            return f"{n} {plural if plural is not None else singular+'s'}"

        return (
            f"<{type(self).__name__}:"
            f" {count_repr(self.buses, 'bus', 'buses')},"
            f" {count_repr(self.branches, 'branch', 'branches')},"
            f" {count_repr(self.loads, 'load', 'loads')},"
            f" {count_repr(self.voltage_sources, 'voltage source')},"
            f" {count_repr(self.special_elements, 'special element')}"
            f">"
        )

    @classmethod
    def from_element(cls, initial_bus: Bus) -> "ElectricalNetwork":
        """ElectricalNetwork constructor. Construct the network from only one element and add the others automatically

        Args:
            initial_bus:
                Any bus of the network
        """
        buses: list[Bus] = []
        branches: list[AbstractBranch] = []
        loads: list[AbstractLoad] = []
        voltage_sources: list[VoltageSource] = []
        specials: list[Element] = []
        elements: list[Element] = [initial_bus]
        visited_elements: list[Element] = []
        while elements:
            e = elements.pop(-1)
            visited_elements.append(e)
            if isinstance(e, Bus):
                buses.append(e)
            elif isinstance(e, AbstractBranch):
                branches.append(e)
            elif isinstance(e, AbstractLoad):
                loads.append(e)
            elif isinstance(e, VoltageSource):
                voltage_sources.append(e)
            else:
                specials.append(e)
            for connected_element in e.connected_elements:
                if connected_element not in visited_elements and connected_element not in elements:
                    elements.append(connected_element)
        return cls(
            buses=buses,
            branches=branches,
            loads=loads,
            voltage_sources=voltage_sources,
            special_elements=specials,
        )

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
                data=[(bus_id, bus.phases, bus.geometry) for bus_id, bus in self.buses.items()],
                columns=["id", "phases", "geometry"],
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
                        branch.phases1,
                        branch.phases2,
                        branch.connected_elements[0].id,
                        branch.connected_elements[1].id,
                        branch.geometry,
                    )
                    for branch_id, branch in self.branches.items()
                ],
                columns=["id", "branch_type", "phases1", "phases2", "bus1_id", "bus2_id", "geometry"],
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
            data=[(load_id, load.phases, load.bus.id) for load_id, load in self.loads.items()],
            columns=["id", "phases", "bus_id"],
            index="id",
        )

    @property
    def voltage_sources_frame(self) -> pd.DataFrame:
        """A dataframe of the voltage sources."""
        return pd.DataFrame.from_records(
            data=[(source_id, source.phases, source.bus.id) for source_id, source in self.voltage_sources.items()],
            columns=["id", "phases", "bus_id"],
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
        code = RoseauLoadFlowExceptionCode.BAD_REQUEST
        if response.status_code == 401:
            msg = "Authentication failed."
        else:
            msg = f"There is a problem in the request. Error code {response.status_code}."
            if content_type == "application/json":
                result_dict: dict[str, Any] = response.json()
                if "msg" in result_dict and "code" in result_dict:
                    # If we have a valid Roseau Load Flow Exception, raise it
                    try:
                        code = RoseauLoadFlowExceptionCode.from_string(result_dict["code"])
                    except Exception:
                        msg += f" {result_dict['code']!r} - {result_dict['msg']!r}"
                    else:
                        msg = result_dict["msg"]
                else:
                    # Otherwise, raise a generic "Bad request"
                    msg += response.text
            else:
                # Non JSON response, raise a generic "Bad request"
                msg += response.text
        logger.error(msg=msg)
        raise RoseauLoadFlowException(msg=msg, code=code)

    def _dispatch_results(self, result_dict: dict[str, Any]) -> None:
        """Dispatch the results to all the elements of the network.

        Args:
            result_dict:
                The results returned by the solver.
        """
        for bus_data in result_dict["buses"]:
            bus = self.buses[bus_data["id"]]
            bus.potentials = self._dispatch_value(bus_data["potentials"], bus.phases, "v")
        for branch_data in result_dict["branches"]:
            branch = self.branches[branch_data["id"]]
            currents1 = self._dispatch_value(branch_data["currents1"], branch.phases1, "i")
            currents2 = self._dispatch_value(branch_data["currents2"], branch.phases2, "i")
            branch.currents = (currents1, currents2)
        for load_data in result_dict["loads"]:
            load = self.loads[load_data["id"]]
            if isinstance(load, FlexibleLoad):
                load.powers = self._dispatch_value(load_data["powers"], load.phases, "s")
            currents = self._dispatch_value(load_data["currents"], load.phases, "i")
            load.currents = currents

    @staticmethod
    def _dispatch_value(value: dict[str, tuple[float, float]], phases: str, t: str) -> np.ndarray:
        """Dispatch the load flow results from a dictionary to an array.

        Args:
            value:
                The dictionary value to dispatch.

            phases:
                The phases of the element.

            t:
                The type of value ("i", "v" or "s").

        Returns:
            The complex final value.
        """
        return np.array([complex(*value[t + p]) for p in phases])

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
        potentials_dict = {"bus_id": [], "phase": [], "potential": []}
        for bus_id, bus in self.buses.items():
            potentials = bus.potentials.m_as("V")
            for potential, phase in zip(potentials, bus.phases):
                potentials_dict["bus_id"].append(bus_id)
                potentials_dict["phase"].append(phase)
                potentials_dict["potential"].append(potential)
        potentials_df = (
            pd.DataFrame.from_dict(potentials_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "potential": complex})
            .set_index(["bus_id", "phase"])
        )
        return potentials_df

    def buses_voltages(self, as_magnitude_angle: bool = False) -> pd.DataFrame:
        """Get the 3-phase voltages of the buses.

        Args:
            as_magnitude_angle:
                If True, the voltages are returned as magnitude and angle. Otherwise, they are
                returned as complex values. Default is False.

        Returns:
            The dataframe of voltages of buses after a load flow has been solved.

        Examples:

            >>> net
            <ElectricalNetwork: 2 buses, 1 branch, 1 load, 2 special elements>

            >>> net.buses_voltages()
                                             voltage
            bus_id phase
            vs     an     200000000000.0+0.00000000j
                   bn    -10000.000000-17320.508076j
                   cn    -10000.000000+17320.508076j
            bus    an     19999.00000095+0.00000000j
                   bn     -9999.975000-17320.464775j
                   cn     -9999.975000+17320.464775j

            >>> net.buses_voltages(as_magnitude_angle=True)
                          voltage_magnitude  voltage_angle
            bus_id phase
            vs     an              20000.00            0.0
                   bn              20000.00         -120.0
                   cn              20000.00          120.0
            bus    an              19999.95            0.0
                   bn              19999.95         -120.0
                   cn              19999.95          120.0

            To get the symmetrical components of the voltages:

            >>> from roseau.load_flow.utils.converters import series_phasor_to_sym
            >>> voltage_series = net.buses_voltages()
            >>> voltage_symmetrical = series_phasor_to_sym(voltage_series)
            >>> voltage_symmetrical
            bus_id  sequence
            bus     zero        3.183231e-12-9.094947e-13j
                    pos         1.999995e+04+3.283594e-12j
                    neg        -1.796870e-07-2.728484e-12j
            vs      zero        5.002221e-12-9.094947e-13j
                    pos         2.000000e+04+3.283596e-12j
                    neg        -1.796880e-07-1.818989e-12j
            Name: voltage, dtype: complex128

            To access one of the symmetrical components sequences, say the positive sequence:

            >>> voltage_symmetrical.loc[:, "pos"]
            bus_id
            bus    19999.95+0.00j
            vs     200000.0+0.00j
            Name: voltage, dtype: complex128
        """
        voltages_dict = {"bus_id": [], "phase": [], "voltage": []}
        for bus_id, bus in self.buses.items():
            voltages = bus.voltages.m_as("V")
            for voltage, phase in zip(voltages, bus.voltage_phases):
                voltages_dict["bus_id"].append(bus_id)
                voltages_dict["phase"].append(phase)
                voltages_dict["voltage"].append(voltage)
        voltages_df = (
            pd.DataFrame.from_dict(voltages_dict, orient="columns")
            .astype({"phase": _VOLTAGE_PHASES_DTYPE, "voltage": complex})
            .set_index(["bus_id", "phase"])
        )
        if as_magnitude_angle:
            voltages_df["voltage_magnitude"] = np.abs(voltages_df["voltage"])
            voltages_df["voltage_angle"] = np.angle(voltages_df["voltage"], deg=True)
            voltages_df.drop(columns=["voltage"], inplace=True)
        return voltages_df

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
        # Old implementation does not work anymore because phases 1 & 2 are not necessarily the same
        currents_list = []
        for branch_id, branch in self.branches.items():
            currents1, currents2 = branch.currents
            currents_list.extend(
                {"branch_id": branch_id, "phase": phase, "current1": i1, "current2": None}
                for i1, phase in zip(currents1.m_as("A"), branch.phases1)
            )
            currents_list.extend(
                {"branch_id": branch_id, "phase": phase, "current1": None, "current2": i2}
                for i2, phase in zip(currents2.m_as("A"), branch.phases2)
            )

        currents_df = (
            pd.DataFrame.from_records(currents_list)
            .astype({"phase": _PHASE_DTYPE, "current1": complex, "current2": complex})
            .groupby(["branch_id", "phase"])  # aggregate current1 and current2 for the same phase
            .mean()  # 2 values only one is not nan -> keep it
            .dropna(how="all")  # if all values are nan -> drop the row (the phase does not exist)
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
        loads_dict = {"load_id": [], "phase": [], "current": []}
        for load_id, load in self.loads.items():
            currents = load.currents.m_as("A")
            for current, phase in zip(currents, load.phases):
                loads_dict["load_id"].append(load_id)
                loads_dict["phase"].append(phase)
                loads_dict["current"].append(current)
        currents_df = (
            pd.DataFrame.from_dict(loads_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "current": complex})
            .set_index(["load_id", "phase"])
        )
        return currents_df

    @property
    def loads_powers(self) -> pd.DataFrame:
        """Get the powers of the loads after a load flow has been solved. Only for flexible loads.

        Returns:
            The data frame of the powers of the loads of the electrical network.
        """
        loads_dict = {"load_id": [], "phase": [], "power": []}
        for load_id, load in self.loads.items():
            if isinstance(load, FlexibleLoad):
                powers = load.powers.m_as("VA")
                for power, phase in zip(powers, load.phases):
                    loads_dict["load_id"].append(load_id)
                    loads_dict["phase"].append(phase)
                    loads_dict["power"].append(power)
        powers_df = (
            pd.DataFrame.from_dict(loads_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "power": complex})
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
            load = self.loads[load_id]
            if isinstance(load, PowerLoad) or isinstance(load, FlexibleLoad):
                load.update_powers(value)
            else:
                msg = "Only power loads can be updated yet..."
                logger.error(msg)
                raise NotImplementedError(msg)

    def set_source_voltages(self, voltages: dict[Any, Sequence[complex]]) -> None:
        """Set new voltages for the voltage source(s).

        Args:
            voltages:
                A dictionary voltage_source_id -> voltages to update.
        """
        for vs_id, value in voltages.items():
            voltage_source = self.voltage_sources[vs_id]
            voltage_source.update_voltages(value)

    def add_element(self, element: Element) -> None:
        """Add an element to the network (the C++ electrical network and the tape will be recomputed).

        Args:
            element:
                The element to add.
        """
        if isinstance(element, Bus):
            self.buses[element.id] = element
        elif isinstance(element, AbstractLoad):
            self.loads[element.id] = element
        elif isinstance(element, AbstractBranch):
            self.branches[element.id] = element
        elif isinstance(element, VoltageSource):
            self.voltage_sources[element.id] = element
        else:
            msg = "Only lines, loads, buses and voltage sources can be added to the network."
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
        elif id in self.voltage_sources:
            source = self.voltage_sources.pop(id)
            source.disconnect()
        elif id in self.branches:
            branch = self.branches.pop(id)
            branch.disconnect()
        else:
            msg = f"{id!r} is not a valid bus, branch, load or voltage source id."
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
        elements += list(self.voltage_sources.values())
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
                break
        if not found_source:
            msg = "There is no voltage source provided in the network, you must provide at least one."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE)

        self._check_ref(elements)

    @staticmethod
    def _check_ref(elements: list[Element]) -> None:
        """Check the number of potential references to avoid having a singular jacobian matrix"""
        visited_elements: list[Element] = []
        for initial_element in elements:
            if initial_element in visited_elements or isinstance(initial_element, Transformer):
                continue
            visited_elements.append(initial_element)
            connected_component: list[Element] = []
            to_visit = [initial_element]
            while to_visit:
                element = to_visit.pop(-1)
                connected_component.append(element)
                for connected_element in element.connected_elements:
                    if connected_element not in visited_elements and not isinstance(connected_element, Transformer):
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
        buses_dict, branches_dict, loads_dict, sources_dict, special_elements = network_from_dict(
            data=data, en_class=cls
        )
        return cls(
            buses=buses_dict,
            branches=branches_dict,
            loads=loads_dict,
            voltage_sources=sources_dict,
            special_elements=special_elements,
        )

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
        buses_results: list[dict[str, Any]] = []
        for bus_id, bus in self.buses.items():
            potentials_dict = {
                f"v{phase}": [potential.real.magnitude, potential.imag.magnitude]
                for potential, phase in zip(bus.potentials, bus.phases)
            }
            buses_results.append({"id": bus_id, "potentials": potentials_dict})

        branches_results: list[dict[str, Any]] = []
        for branch_id, branch in self.branches.items():
            currents1, currents2 = branch.currents
            currents_dict1 = {
                f"i{phase}": [current.real.magnitude, current.imag.magnitude]
                for current, phase in zip(currents1, branch.phases1)
            }
            currents_dict2 = {
                f"i{phase}": [current.real.magnitude, current.imag.magnitude]
                for current, phase in zip(currents2, branch.phases2)
            }
            branches_results.append({"id": branch_id, "currents1": currents_dict1, "currents2": currents_dict2})

        loads_results: list[dict[str, Any]] = []
        for load_id, load in self.loads.items():
            currents_dict = {
                f"i{phase}": [current.real.magnitude, current.imag.magnitude]
                for current, phase in zip(load.currents, load.phases)
            }
            if isinstance(load, FlexibleLoad):
                powers_dict = {
                    f"s{phase}": [power.real.magnitude, power.imag.magnitude]
                    for power, phase in zip(load.powers, load.phases)
                }
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
            The path it has been written in.
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
        buses_dict, branches_dict, loads_dict, sources_dict, special_elements = network_from_dgs(filename=path)
        return cls(
            buses=buses_dict,
            branches=branches_dict,
            loads=loads_dict,
            voltage_sources=sources_dict,
            special_elements=special_elements,
        )
