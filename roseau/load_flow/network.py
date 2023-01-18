import json
import logging
import re
import warnings
from collections.abc import Sequence, Sized
from pathlib import Path
from typing import NoReturn, Optional, TypeVar, Union
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
    Ground,
    Line,
    PotentialRef,
    PowerLoad,
    Switch,
    Transformer,
    VoltageSource,
)
from roseau.load_flow.typing import Id, JsonDict, StrPath

logger = logging.getLogger(__name__)

# Phases dtype for all data frames
_PHASE_DTYPE = pd.CategoricalDtype(categories=["a", "b", "c", "n"], ordered=True)
# Phases dtype for voltage data frames
_VOLTAGE_PHASES_DTYPE = pd.CategoricalDtype(["an", "bn", "cn", "ab", "bc", "ca"], ordered=True)

_T = TypeVar("_T", bound=Element)


class ElectricalNetwork:
    DEFAULT_PRECISION: float = 1e-6
    DEFAULT_MAX_ITERATIONS: int = 20
    DEFAULT_BASE_URL = "https://load-flow-api.roseautechnologies.com/"

    # Default classes to use
    branch_class = AbstractBranch
    line_class = Line
    transformer_class = Transformer
    switch_class = Switch
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
        buses: Union[list[Bus], dict[Id, Bus]],
        branches: Union[list[AbstractBranch], dict[Id, AbstractBranch]],
        loads: Union[list[AbstractLoad], dict[Id, AbstractLoad]],
        voltage_sources: Union[list[VoltageSource], dict[Id, VoltageSource]],
        grounds: Union[list[Ground], dict[Id, Ground]],
        potential_refs: Union[list[PotentialRef], dict[Id, PotentialRef]],
        **kwargs,
    ) -> None:
        """ElectricalNetwork constructor.

        Args:
            buses:
                The buses of the network. Either a list of buses or a dictionary of buses with
                their IDs as keys.

            branches:
                The branches of the network. Either a list of branches or a dictionary of branches
                with their IDs as keys.

            loads:
                The loads of the network. Either a list of loads or a dictionary of loads with their
                IDs as keys.

            voltage_sources:
                The voltage sources of the network. Either a list of voltage sources or a dictionary
                of voltage sources with their IDs as keys.

            grounds:
                The grounds of the network. Either a list of grounds or a dictionary of grounds with
                their IDs as keys. A small network typically has only one ground.

            potential_refs:
                The potential references of the network. Either a list of potential references or a
                dictionary of potential references with their IDs as keys. A potential reference
                per galvanically isolated section of the network is expected.
        """
        self.buses = self._elements_as_dict(buses, RoseauLoadFlowExceptionCode.DUPLICATE_BUS_ID)
        self.branches = self._elements_as_dict(branches, RoseauLoadFlowExceptionCode.DUPLICATE_BRANCH_ID)
        self.loads = self._elements_as_dict(loads, RoseauLoadFlowExceptionCode.DUPLICATE_LOAD_ID)
        self.voltage_sources = self._elements_as_dict(
            voltage_sources, RoseauLoadFlowExceptionCode.DUPLICATE_VOLTAGE_SOURCE_ID
        )
        self.grounds = self._elements_as_dict(grounds, RoseauLoadFlowExceptionCode.DUPLICATE_GROUND_ID)
        self.potential_refs = self._elements_as_dict(
            potential_refs, RoseauLoadFlowExceptionCode.DUPLICATE_POTENTIAL_REF_ID
        )

        self._check_validity(constructed=False)
        self._create_network()
        self._valid = True
        self._results_valid: bool = False
        self.results_info: JsonDict = {}  # TODO: Add doc on this field

    def __repr__(self) -> str:
        def count_repr(__o: Sized, /, singular: str, plural: Optional[str] = None) -> str:
            """Singular/plural count representation: `1 bus` or `2 buses`."""
            n = len(__o)
            if n == 1:
                return f"{n} {singular}"
            return f"{n} {plural if plural is not None else singular + 's'}"

        return (
            f"<{type(self).__name__}:"
            f" {count_repr(self.buses, 'bus', 'buses')},"
            f" {count_repr(self.branches, 'branch', 'branches')},"
            f" {count_repr(self.loads, 'load', 'loads')},"
            f" {count_repr(self.voltage_sources, 'voltage source')},"
            f" {count_repr(self.grounds, 'ground')},"
            f" {count_repr(self.potential_refs, 'potential ref')}"
            f">"
        )

    @staticmethod
    def _elements_as_dict(
        elements: Union[list[_T], dict[Id, _T]], error_code: RoseauLoadFlowExceptionCode
    ) -> dict[Id, _T]:
        """Convert a list of elements to a dictionary of elements with their IDs as keys."""
        if isinstance(elements, dict):
            return elements
        elements_dict: dict[Id, _T] = {}
        for element in elements:
            if element.id in elements_dict:
                name = error_code.name.removeprefix("DUPLICATE_").removesuffix("_ID").replace("_", " ").lower()
                msg = f"Duplicate id for an {name} in this network: {element.id!r}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, code=error_code)
            elements_dict[element.id] = element
        return elements_dict

    @classmethod
    def from_element(cls, initial_bus: Bus) -> "ElectricalNetwork":
        """Construct the network from only one element and add the others automatically.

        Args:
            initial_bus:
                Any bus of the network.
        """
        buses: list[Bus] = []
        branches: list[AbstractBranch] = []
        loads: list[AbstractLoad] = []
        voltage_sources: list[VoltageSource] = []
        grounds: list[Ground] = []
        potential_refs: list[PotentialRef] = []

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
            elif isinstance(e, Ground):
                grounds.append(e)
            elif isinstance(e, PotentialRef):
                potential_refs.append(e)
            for connected_element in e.connected_elements:
                if connected_element not in visited_elements and connected_element not in elements:
                    elements.append(connected_element)
        return cls(
            buses=buses,
            branches=branches,
            loads=loads,
            voltage_sources=voltage_sources,
            grounds=grounds,
            potential_refs=potential_refs,
        )

    #
    # Properties to access the data as dataframes
    #
    @property
    def buses_frame(self) -> gpd.GeoDataFrame:
        """A geo dataframe of the network buses."""
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
        """A geo dataframe of the network branches."""
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
        """A dataframe of the network loads."""
        return pd.DataFrame.from_records(
            data=[(load_id, load.phases, load.bus.id) for load_id, load in self.loads.items()],
            columns=["id", "phases", "bus_id"],
            index="id",
        )

    @property
    def voltage_sources_frame(self) -> pd.DataFrame:
        """A dataframe of the network voltage sources."""
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
        """Solve the load flow for this network.

        Execute a newton algorithm for load flow calculation. In order to get the results of the
        load flow, please use the `results` method or call the elements directly.

        Args:
            auth:
                The login and password for the roseau load flow api.

            base_url:
                The base url to request the load flow solver.

            precision:
                Precision needed for the convergence.

            max_iterations:
                The maximum number of allowed iterations.

        Returns:
            The number of iterations taken.
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
        result_dict: JsonDict = response.json()
        self.results_info = result_dict["info"]
        if self.results_info["status"] != "success":
            msg = (
                f"The load flow did not converge after {self.results_info['iterations']} iterations. The norm of the "
                f"residuals is {self.results_info['finalError']:.5n}"
            )
            logger.error(msg=msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE)

        logger.info(
            f"The load flow converged after {self.results_info['iterations']} iterations (final error="
            f"{self.results_info['finalError']:.5n})."
        )

        # Dispatch the results
        self._dispatch_results(result_dict=result_dict)

        # The results are now valid
        self._results_valid = True

        return self.results_info["iterations"]

    @staticmethod
    def _parse_error(response: Response) -> NoReturn:
        """Parse a response when its status is not "ok".

        Args:
            response:
                The response to parse.
        """
        content_type = response.headers.get("content-type", None)
        code = RoseauLoadFlowExceptionCode.BAD_REQUEST
        if response.status_code == 401:
            msg = "Authentication failed."
        else:
            msg = f"There is a problem in the request. Error code {response.status_code}."
            if content_type == "application/json":
                result_dict: JsonDict = response.json()
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

    def _dispatch_results(self, result_dict: JsonDict) -> None:
        """Dispatch the results to all the elements of the network.

        Args:
            result_dict:
                The results returned by the solver.
        """
        for bus_data in result_dict["buses"]:
            bus = self.buses[bus_data["id"]]
            bus._res_potentials = np.array([complex(v[0], v[1]) for v in bus_data["potentials"]], dtype=complex)
        for branch_data in result_dict["branches"]:
            branch = self.branches[branch_data["id"]]
            currents1 = np.array([complex(i[0], i[1]) for i in branch_data["currents1"]], dtype=complex)
            currents2 = np.array([complex(i[0], i[1]) for i in branch_data["currents2"]], dtype=complex)
            branch._res_currents = (currents1, currents2)
        for load_data in result_dict["loads"]:
            load = self.loads[load_data["id"]]
            load._res_currents = np.array([complex(i[0], i[1]) for i in load_data["currents"]], dtype=complex)
            if isinstance(load, PowerLoad) and load.is_flexible:
                load._res_flexible_powers = np.array([complex(p[0], p[1]) for p in load_data["powers"]], dtype=complex)

    #
    # Getters for the load flow results
    #
    def _warn_invalid_results(self) -> None:
        """Warn when the network is invalid."""
        if not self._results_valid:
            warnings.warn(
                message="The results of this network may be outdated. Please re-run a load flow to ensure the "
                "validity of results.",
                category=UserWarning,
            )

    @property
    def res_buses_potentials(self) -> pd.DataFrame:
        """The load flow results of the potentials of the buses (V) as a dataframe."""
        self._warn_invalid_results()
        potentials_dict = {"bus_id": [], "phase": [], "potential": []}
        for bus_id, bus in self.buses.items():
            for potential, phase in zip(bus._res_potentials_getter(warning=False), bus.phases):
                potentials_dict["bus_id"].append(bus_id)
                potentials_dict["phase"].append(phase)
                potentials_dict["potential"].append(potential)
        potentials_df = (
            pd.DataFrame.from_dict(potentials_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "potential": complex})
            .set_index(["bus_id", "phase"])
        )
        return potentials_df

    @property
    def res_buses_voltages(self) -> pd.DataFrame:
        """The load flow results of the voltages of the buses (V) as a dataframe.

        The voltages are computed from the potentials of the buses. If the bus has a neutral, the
        voltage is the line-to-neutral voltage. Otherwise, the voltage is the line-to-line voltage.
        The result dataframe has a ``phase`` index that depicts this behavior.

        Examples:

            >>> net
            <ElectricalNetwork: 2 buses, 1 branch, 1 load, 1 ground, 1 potential ref>

            >>> net.res_buses_voltages
                                             voltage
            bus_id phase
            s_bus  an     200000000000.0+0.00000000j
                   bn    -10000.000000-17320.508076j
                   cn    -10000.000000+17320.508076j
            l_bus  an     19999.00000095+0.00000000j
                   bn     -9999.975000-17320.464775j
                   cn     -9999.975000+17320.464775j

            To get the magnitude and angle of the voltages:

            >>> net.res_buses_voltages.transform([np.abs, np.angle])
                           voltage
                          absolute     angle
            bus_id phase
            s_bus  an     20000.00  0.000000
                   bn     20000.00 -2.094395
                   cn     20000.00  2.094395
            l_bus  an     19999.95  0.000000
                   bn     19999.95 -2.094395
                   cn     19999.95  2.094395

            To get the symmetrical components of the voltages:

            >>> from roseau.load_flow.utils.converters import series_phasor_to_sym
            >>> voltage_series = net.res_buses_voltages["voltage"]
            >>> voltage_symmetrical = series_phasor_to_sym(voltage_series)
            >>> voltage_symmetrical
            bus_id  sequence
            l_bus   zero        3.183231e-12-9.094947e-13j
                    pos         1.999995e+04+3.283594e-12j
                    neg        -1.796870e-07-2.728484e-12j
            s_bus   zero        5.002221e-12-9.094947e-13j
                    pos         2.000000e+04+3.283596e-12j
                    neg        -1.796880e-07-1.818989e-12j
            Name: voltage, dtype: complex128

            To access one of the symmetrical components sequences, say the positive sequence:

            >>> voltage_symmetrical.loc[:, "pos"]
            bus_id
            l_bus  19999.95+0.00j
            s_bus  200000.0+0.00j
            Name: voltage, dtype: complex128
        """
        self._warn_invalid_results()
        voltages_dict = {"bus_id": [], "phase": [], "voltage": []}
        for bus_id, bus in self.buses.items():
            for voltage, phase in zip(bus._res_voltages_getter(warning=False), bus.voltage_phases):
                voltages_dict["bus_id"].append(bus_id)
                voltages_dict["phase"].append(phase)
                voltages_dict["voltage"].append(voltage)
        voltages_df = (
            pd.DataFrame.from_dict(voltages_dict, orient="columns")
            .astype({"phase": _VOLTAGE_PHASES_DTYPE, "voltage": complex})
            .set_index(["bus_id", "phase"])
        )
        return voltages_df

    @property
    def res_branches_currents(self) -> pd.DataFrame:
        """The load flow results of the currents of the branches (A) as a dataframe."""
        self._warn_invalid_results()
        currents_list = []
        for branch_id, branch in self.branches.items():
            currents1, currents2 = branch._res_currents_getter(warning=False)
            currents_list.extend(
                {"branch_id": branch_id, "phase": phase, "current1": i1, "current2": None}
                for i1, phase in zip(currents1, branch.phases1)
            )
            currents_list.extend(
                {"branch_id": branch_id, "phase": phase, "current1": None, "current2": i2}
                for i2, phase in zip(currents2, branch.phases2)
            )

        currents_df = (
            pd.DataFrame.from_records(currents_list)
            .astype({"phase": _PHASE_DTYPE, "current1": complex, "current2": complex})
            .groupby(["branch_id", "phase"])  # aggregate current1 and current2 for the same phase
            .mean()  # 2 values; only one is not nan -> keep it
            .dropna(how="all")  # if all values are nan -> drop the row (the phase does not exist)
        )
        return currents_df

    @property
    def res_loads_currents(self) -> pd.DataFrame:
        """The load flow results of the currents of the loads (A) as a dataframe."""
        self._warn_invalid_results()
        loads_dict = {"load_id": [], "phase": [], "current": []}
        for load_id, load in self.loads.items():
            for current, phase in zip(load._res_currents_getter(warning=False), load.phases):
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
    def res_loads_powers(self) -> pd.DataFrame:
        """The load flow results of the powers of the loads (VA) as a dataframe."""
        loads_dict = {"load_id": [], "phase": [], "power": []}
        for load_id, load in self.loads.items():
            for power, phase in zip(load.res_powers, load.phases):
                loads_dict["load_id"].append(load_id)
                loads_dict["phase"].append(phase)
                loads_dict["power"].append(power)
        currents_df = (
            pd.DataFrame.from_dict(loads_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "power": complex})
            .set_index(["load_id", "phase"])
        )
        return currents_df

    @property
    def res_loads_flexible_powers(self) -> pd.DataFrame:
        """The load flow results of the flexible powers of the "flexible" loads (A) as a dataframe."""
        self._warn_invalid_results()
        loads_dict = {"load_id": [], "phase": [], "power": []}
        for load_id, load in self.loads.items():
            if isinstance(load, PowerLoad) and load.is_flexible:
                for power, phase in zip(load._res_flexible_powers_getter(warning=False), load.phases):
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
    def set_load_point(self, load_point: dict[Id, Sequence[complex]]) -> None:
        """Set a new load point to the network.

        Args:
            load_point:
                The new load points to set indexed by the load id.
        """
        for load_id, value in load_point.items():
            load = self.loads[load_id]
            if isinstance(load, PowerLoad):
                load.powers = value
            else:
                msg = "Only power loads can be updated for now..."
                logger.error(msg)
                raise NotImplementedError(msg)

    def set_source_voltages(self, voltages: dict[Id, Sequence[complex]]) -> None:
        """Set new voltages for the voltage source(s).

        Args:
            voltages:
                The new voltages to set indexed by the voltage source id.
        """
        for vs_id, value in voltages.items():
            voltage_source = self.voltage_sources[vs_id]
            voltage_source.voltages = value

    def _connect_element(self, element: Element) -> None:
        """Connect an element to the network.

        When an element is added to the network, extra processing is done to keep the network
        valid. Always use this method to add new elements to the network after creating it.

        Args:
            element:
                The element to add. Only lines, loads, buses and voltage sources can be added.
        """
        # The C++ electrical network and the tape will be recomputed
        if element.network is not None and element.network != self:
            element._raise_several_network()

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
        element._network = self
        self._valid = False
        self._results_valid = False

    def _disconnect_element(self, element: Element) -> None:
        """Remove an element of the network.

        When an element is removed from the network, extra processing is needed to keep the network
        valid.

        Args:
            element:
                The element to remove.
        """
        # The C++ electrical network and the tape will be recomputed
        if isinstance(element, (Bus, AbstractBranch)):
            msg = f"{element!r} is a {type(element).__name__} and it can not be disconnected from a network."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        elif isinstance(element, AbstractLoad):
            self.loads.pop(element.id)
        elif isinstance(element, VoltageSource):
            self.voltage_sources.pop(element.id)
        else:
            msg = f"{element!r} is not a valid load or voltage source."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        element._network = None
        self._valid = False
        self._results_valid = False

    def _create_network(self) -> None:
        """Create the Cython and C++ electrical network of all the passed elements."""
        self._valid = True

    def _check_validity(self, constructed: bool) -> None:
        """Check the validity of the network to avoid having a singular jacobian matrix. It also assigns the `self`
        to the network field of elements.

        Args:
            constructed:
                True if the network is already constructed, and we have added an element, False
                otherwise.
        """
        elements: list[Element] = []
        elements.extend(self.buses.values())
        elements.extend(self.branches.values())
        elements.extend(self.loads.values())
        elements.extend(self.voltage_sources.values())
        elements.extend(self.grounds.values())
        elements.extend(self.potential_refs.values())

        found_source = False
        for element in elements:
            # Check connected elements and check network assignment
            for adj_element in element.connected_elements:
                if adj_element not in elements:
                    msg = (
                        f"{type(adj_element).__name__} element ({adj_element.id!r}) is connected "
                        f"to {type(element).__name__} element ({element.id!r}) but "
                    )
                    if constructed:
                        msg += "was not passed to the ElectricalNetwork constructor."
                    else:
                        msg += "has not been added to the network. It must be added with 'add_element'."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT)

            # Check that there is at least a `VoltageSource` element in the network
            if isinstance(element, VoltageSource):
                found_source = True

        # Raises an error if no voltage sources
        if not found_source:
            msg = "There is no voltage source provided in the network, you must provide at least one."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE)

        # Check the potential references
        self._check_ref(elements)

        # Assign the network
        for element in elements:
            if element.network is None:
                element._network = self
            elif element.network != self:
                element._raise_several_network()

    @staticmethod
    def _check_ref(elements: list[Element]) -> None:
        """Check the number of potential references to avoid having a singular jacobian matrix."""
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
    def from_dict(cls, data: JsonDict) -> "ElectricalNetwork":
        """Construct an electrical network from a dict created with ``ElectricalNetwork(...).to_dict()``.

        Args:
            data:
                The dictionary containing the network data.

        Returns:
            The constructed network.
        """
        buses, branches, loads, sources, grounds, p_refs = network_from_dict(data, en_class=cls)
        return cls(
            buses=buses,
            branches=branches,
            loads=loads,
            voltage_sources=sources,
            grounds=grounds,
            potential_refs=p_refs,
        )

    @classmethod
    def from_json(cls, path: StrPath) -> "ElectricalNetwork":
        """Construct an electrical network from a json file.

        Args:
            path:
                The path to the network data file.

        Returns:
            The constructed network.
        """
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data=data)

    def to_dict(self) -> JsonDict:
        """Convert the electrical network to a dictionary."""
        return network_to_dict(self)

    def to_json(self, path: StrPath) -> None:
        """Save the current network to a json file.

        Args:
            path:
                The path for the network output.
        """
        res = self.to_dict()
        output = json.dumps(res, ensure_ascii=False, indent=4)
        output = re.sub(r"\[\s+(.*),\s+(.*)\s+]", r"[\1, \2]", output)
        if not output.endswith("\n"):
            output += "\n"
        Path(path).write_text(output)

    #
    # Output of results
    #
    def results_to_dict(self) -> JsonDict:
        """Get the voltages and currents computed by the load flow and return them as a dict."""
        buses_results: list[JsonDict] = [
            {"id": bus.id, "phases": bus.phases, "potentials": [[v.real, v.imag] for v in bus.res_potentials]}
            for bus in self.buses.values()
        ]

        branches_results: list[JsonDict] = []
        for branch in self.branches.values():
            currents1, currents2 = branch.res_currents
            branches_results.append(
                {
                    "id": branch.id,
                    "phases1": branch.phases1,
                    "phases2": branch.phases1,
                    "currents1": [[i.real, i.imag] for i in currents1],
                    "currents2": [[i.real, i.imag] for i in currents2],
                }
            )

        loads_results: list[JsonDict] = []
        for load in self.loads.values():
            res = {"id": load.id, "phases": load.phases, "currents": [[i.real, i.imag] for i in load.res_currents]}
            if isinstance(load, PowerLoad) and load.is_flexible:
                res["powers"] = [[s.real, s.imag] for s in load.res_flexible_powers]
            loads_results.append(res)

        return {
            "info": self.results_info,
            "buses": buses_results,
            "branches": branches_results,
            "loads": loads_results,
        }

    def results_to_json(self, path: StrPath) -> Path:
        """Write the results of the load flow to a json file.

        .. warning::
            If the file exists, it will be overwritten.

        Args:
            path:
                The path to the json file.

        Returns:
            The resolved and normalized path of the written file.
        """
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
    def from_dgs(cls, path: StrPath) -> "ElectricalNetwork":
        """Construct an electrical network from json DGS file (PowerFactory).

        Args:
            path:
                The path to the network DGS data file.

        Returns:
            The constructed network.
        """
        buses, branches, loads, voltage_sources, grounds, potential_refs = network_from_dgs(path)
        return cls(
            buses=buses,
            branches=branches,
            loads=loads,
            voltage_sources=voltage_sources,
            grounds=grounds,
            potential_refs=potential_refs,
        )
