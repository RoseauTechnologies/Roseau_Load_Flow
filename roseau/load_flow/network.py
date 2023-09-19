"""
This module defines the electrical network class.
"""
import json
import logging
import re
import textwrap
import warnings
from collections.abc import Sized
from importlib import resources
from pathlib import Path
from typing import NoReturn, Optional, TypeVar, Union
from urllib.parse import urljoin

import geopandas as gpd
import pandas as pd
import requests
from pyproj import CRS
from requests import Response
from requests.auth import HTTPBasicAuth
from rich.table import Table
from typing_extensions import Self

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
from roseau.load_flow.solvers import check_solver_params
from roseau.load_flow.typing import Id, JsonDict, Solver, StrPath
from roseau.load_flow.utils import CatalogueMixin, JsonMixin, console

logger = logging.getLogger(__name__)

# Phases dtype for all data frames
_PHASE_DTYPE = pd.CategoricalDtype(categories=["a", "b", "c", "n"], ordered=True)
# Phases dtype for voltage data frames
_VOLTAGE_PHASES_DTYPE = pd.CategoricalDtype(categories=["an", "bn", "cn", "ab", "bc", "ca"], ordered=True)

_T = TypeVar("_T", bound=Element)


class ElectricalNetwork(JsonMixin, CatalogueMixin[JsonDict]):
    """Electrical network class.

    This class represents an electrical network, its elements, and their connections. After
    creating the network, the load flow solver can be run on it using the
    :meth:`solve_load_flow` method.

    Args:
        buses:
            The buses of the network. Either a list of buses or a dictionary of buses with
            their IDs as keys. Buses are the nodes of the network. They connect other elements
            such as loads and sources. Buses can be connected together with branches.

        branches:
            The branches of the network. Either a list of branches or a dictionary of branches
            with their IDs as keys. Branches are the elements that connect two buses together.
            They can be lines, transformers, or switches.

        loads:
            The loads of the network. Either a list of loads or a dictionary of loads with their
            IDs as keys. There are three types of loads: constant power, constant current, and
            constant impedance.

        sources:
            The sources of the network. Either a list of sources or a dictionary of sources with
            their IDs as keys. A network must have at least one source. Note that two sources
            cannot be connected with a switch.

        grounds:
            The grounds of the network. Either a list of grounds or a dictionary of grounds with
            their IDs as keys. LV networks typically have one ground element connected to the
            neutral of the main source bus (secondary of the MV/LV transformer). HV networks
            may have one or more grounds connected to the shunt components of their lines.

        potential_refs:
            The potential references of the network. Either a list of potential references or a
            dictionary of potential references with their IDs as keys. As the name suggests, this
            element defines the reference of potentials of the network. A potential reference per
            galvanically isolated section of the network is expected. A potential reference can
            be connected to a bus or to a ground.

    Attributes:
        buses (dict[Id, roseau.load_flow.Bus]):
            Dictionary of buses of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<buses_frame>`.

        branches (dict[Id, roseau.load_flow.AbstractBranch]):
            Dictionary of branches of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<branches_frame>`.

        loads (dict[Id, roseau.load_flow.AbstractLoad]):
            Dictionary of loads of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<loads_frame>`.

        sources (dict[Id, roseau.load_flow.VoltageSource]):
            Dictionary of voltage sources of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<sources_frame>`.

        grounds (dict[Id, roseau.load_flow.Ground]):
            Dictionary of grounds of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<grounds_frame>`.

        potential_refs (dict[Id, roseau.load_flow.PotentialRef]):
            Dictionary of potential references of the network indexed by their IDs. Also available
            as a :attr:`DataFrame<potential_refs_frame>`.

        res_info (JsonDict):
            Dictionary containing solver information on the last run of the load flow analysis.
            Empty if the load flow analysis has not been run yet.
            Example::

                {
                    "solver": "newton",
                    "tolerance": 1e-06,
                    "max_iterations": 20,
                    "warm_start": True,
                    "status": "success",
                    "iterations": 2,
                    "residual": 1.8595619621919468e-07
                }
    """

    _DEFAULT_TOLERANCE: float = 1e-6
    _DEFAULT_MAX_ITERATIONS: int = 20
    _DEFAULT_BASE_URL: str = "https://load-flow-api-dev.roseautechnologies.com/"
    _DEFAULT_WARM_START: bool = True
    _DEFAULT_SOLVER: Solver = "newton_goldstein"

    # Elements classes (for internal use only)
    _branch_class = AbstractBranch
    _line_class = Line
    _transformer_class = Transformer
    _switch_class = Switch
    _load_class = AbstractLoad
    _voltage_source_class = VoltageSource
    _bus_class = Bus
    _ground_class = Ground
    _pref_class = PotentialRef

    #
    # Methods to build an electrical network
    #
    def __init__(
        self,
        buses: Union[list[Bus], dict[Id, Bus]],
        branches: Union[list[AbstractBranch], dict[Id, AbstractBranch]],
        loads: Union[list[AbstractLoad], dict[Id, AbstractLoad]],
        sources: Union[list[VoltageSource], dict[Id, VoltageSource]],
        grounds: Union[list[Ground], dict[Id, Ground]],
        potential_refs: Union[list[PotentialRef], dict[Id, PotentialRef]],
        **kwargs,
    ) -> None:
        self.buses = self._elements_as_dict(buses, RoseauLoadFlowExceptionCode.BAD_BUS_ID)
        self.branches = self._elements_as_dict(branches, RoseauLoadFlowExceptionCode.BAD_BRANCH_ID)
        self.loads = self._elements_as_dict(loads, RoseauLoadFlowExceptionCode.BAD_LOAD_ID)
        self.sources = self._elements_as_dict(sources, RoseauLoadFlowExceptionCode.BAD_SOURCE_ID)
        self.grounds = self._elements_as_dict(grounds, RoseauLoadFlowExceptionCode.BAD_GROUND_ID)
        self.potential_refs = self._elements_as_dict(potential_refs, RoseauLoadFlowExceptionCode.BAD_POTENTIAL_REF_ID)

        self._check_validity(constructed=False)
        self._create_network()
        self._valid = True
        self._results_valid: bool = False
        self.res_info: JsonDict = {}

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
            f" {count_repr(self.loads, 'load')},"
            f" {count_repr(self.sources, 'source')},"
            f" {count_repr(self.grounds, 'ground')},"
            f" {count_repr(self.potential_refs, 'potential ref')}"
            f">"
        )

    @staticmethod
    def _elements_as_dict(
        elements: Union[list[_T], dict[Id, _T]], error_code: RoseauLoadFlowExceptionCode
    ) -> dict[Id, _T]:
        """Convert a list of elements to a dictionary of elements with their IDs as keys."""
        typ = error_code.name.removeprefix("BAD_").removesuffix("_ID").replace("_", " ")
        if isinstance(elements, dict):
            for element_id, element in elements.items():
                if element.id != element_id:
                    msg = f"{typ.capitalize()} ID mismatch: {element_id!r} != {element.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg, code=error_code)
            return elements
        elements_dict: dict[Id, _T] = {}
        for element in elements:
            if element.id in elements_dict:
                msg = f"Duplicate ID for an {typ.lower()} in this network: {element.id!r}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, code=error_code)
            elements_dict[element.id] = element
        return elements_dict

    @classmethod
    def from_element(cls, initial_bus: Bus) -> Self:
        """Construct the network from only one element and add the others automatically.

        Args:
            initial_bus:
                Any bus of the network.
        """
        buses: list[Bus] = []
        branches: list[AbstractBranch] = []
        loads: list[AbstractLoad] = []
        sources: list[VoltageSource] = []
        grounds: list[Ground] = []
        potential_refs: list[PotentialRef] = []

        elements: list[Element] = [initial_bus]
        visited_elements: set[Element] = set()
        while elements:
            e = elements.pop(-1)
            visited_elements.add(e)
            if isinstance(e, Bus):
                buses.append(e)
            elif isinstance(e, AbstractBranch):
                branches.append(e)
            elif isinstance(e, AbstractLoad):
                loads.append(e)
            elif isinstance(e, VoltageSource):
                sources.append(e)
            elif isinstance(e, Ground):
                grounds.append(e)
            elif isinstance(e, PotentialRef):
                potential_refs.append(e)
            for connected_element in e._connected_elements:
                if connected_element not in visited_elements and connected_element not in elements:
                    elements.append(connected_element)
        return cls(
            buses=buses,
            branches=branches,
            loads=loads,
            sources=sources,
            grounds=grounds,
            potential_refs=potential_refs,
        )

    #
    # Properties to access the data as dataframes
    #
    @property
    def buses_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`buses` of the network as a geo dataframe."""
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
        """The :attr:`branches` of the network as a geo dataframe."""
        return gpd.GeoDataFrame(
            data=pd.DataFrame.from_records(
                data=[
                    (
                        branch_id,
                        branch.branch_type,
                        branch.phases1,
                        branch.phases2,
                        branch.bus1.id,
                        branch.bus2.id,
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
        """The :attr:`loads` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[(load_id, load.phases, load.bus.id) for load_id, load in self.loads.items()],
            columns=["id", "phases", "bus_id"],
            index="id",
        )

    @property
    def sources_frame(self) -> pd.DataFrame:
        """The :attr:`sources` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[(source_id, source.phases, source.bus.id) for source_id, source in self.sources.items()],
            columns=["id", "phases", "bus_id"],
            index="id",
        )

    @property
    def grounds_frame(self) -> pd.DataFrame:
        """The :attr:`grounds` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[
                (ground.id, bus_id, phase)
                for ground in self.grounds.values()
                for bus_id, phase in ground.connected_buses.items()
            ],
            columns=["id", "bus_id", "phase"],
            index=["id", "bus_id"],
        )

    @property
    def potential_refs_frame(self) -> pd.DataFrame:
        """The :attr:`potential references <potential_refs>` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[(pref.id, pref.phase, pref.element.id) for pref in self.potential_refs.values()],
            columns=["id", "phase", "element_id"],
            index="id",
        )

    @property
    def short_circuits_frame(self) -> pd.DataFrame:
        """The short-circuits of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[
                (bus.id, bus.phases, "".join(sorted(sc["phases"])), sc["ground"])
                for bus in self.buses.values()
                for sc in bus.short_circuits
            ],
            columns=["bus_id", "phases", "short_circuit", "ground"],
        )

    #
    # Method to solve a load flow
    #
    def solve_load_flow(
        self,
        auth: Union[tuple[str, str], HTTPBasicAuth],
        base_url: str = _DEFAULT_BASE_URL,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        tolerance: float = _DEFAULT_TOLERANCE,
        warm_start: bool = _DEFAULT_WARM_START,
        solver: Solver = _DEFAULT_SOLVER,
        solver_params: Optional[JsonDict] = None,
    ) -> int:
        """Solve the load flow for this network (Requires internet access).

        To get the results of the load flow for the whole network, use the `res_` properties on the
        network (e.g. ``print(net.res_buses``). To get the results for a specific element, use the
        `res_` properties on the element (e.g. ``print(net.buses["bus1"].res_potentials)``.

        Args:
            auth:
                The login and password for the roseau load flow api.

            base_url:
                The base url to request the load flow solver.

            max_iterations:
                The maximum number of allowed iterations.

            tolerance:
                Tolerance needed for the convergence.

            warm_start:
                If true, initialize the solver with the potentials of the last successful load flow
                result (if any).

            solver:
                The name of the solver to use for the load flow. The options are:
                    - ``'newton'``: the classical Newton-Raphson solver.
                    - ``'newton_goldstein'``: the Newton-Raphson solver with the Goldstein and
                      Price linear search.

            solver_params:
                A dictionary of parameters used by the solver. Available parameters depend on the
                solver chosen. For more information, see the :ref:`solvers` page.

        Returns:
            The number of iterations taken.
        """
        from roseau.load_flow import __version__

        solver_params = check_solver_params(solver=solver, params=solver_params)
        if not self._valid:
            warm_start = False  # Otherwise, we may get an error when calling self.results_to_dict()
            self._check_validity(constructed=True)
            self._create_network()

        # Get the data
        data = {
            "network": self.to_dict(include_geometry=False),
            "solver": {
                "name": solver,
                "params": solver_params,
                "max_iterations": max_iterations,
                "tolerance": tolerance,
                "warm_start": warm_start,
            },
        }
        if warm_start and self.res_info.get("status", "failure") == "success":
            # Ignore warnings because results may be invalid (a load power has been changed, etc.)
            data["results"] = self._results_to_dict(False)

        # Request the server
        response = requests.post(
            url=urljoin(base_url, "solve/"),
            json=data,
            auth=auth,
            headers={"accept": "application/json", "rlf-version": __version__},
        )

        # Read the response
        # Check the response headers
        remote_rlf_version = response.headers.get("rlf-new-version")
        if remote_rlf_version is not None:
            warnings.warn(
                message=f"A new version ({remote_rlf_version}) of the library roseau-load-flow is available. Please "
                f"visit https://roseautechnologies.github.io/Roseau_Load_Flow/Installation.html for more information.",
                category=UserWarning,
                stacklevel=2,
            )

        # HTTP 4xx,5xx
        if not response.ok:
            self._parse_error(response=response)

        # HTTP 200
        results: JsonDict = response.json()
        self.res_info = results["info"]
        if self.res_info["status"] != "success":
            msg = (
                f"The load flow did not converge after {self.res_info['iterations']} iterations. The norm of "
                f"the residuals is {self.res_info['residual']:.5n}"
            )
            logger.error(msg=msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE)

        logger.info(
            f"The load flow converged after {self.res_info['iterations']} iterations (residual="
            f"{self.res_info['residual']:.5n})."
        )

        # Dispatch the results
        self._results_from_dict(data=results)

        return self.res_info["iterations"]

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

    def _results_from_dict(self, data: JsonDict) -> None:
        """Dispatch the results to all the elements of the network.

        Args:
            data:
                The results returned by the solver.
        """
        for bus_data in data["buses"]:
            bus = self.buses[bus_data["id"]]
            bus.results_from_dict(bus_data)
        for branch_data in data["branches"]:
            branch = self.branches[branch_data["id"]]
            branch.results_from_dict(branch_data)
        for load_data in data["loads"]:
            load = self.loads[load_data["id"]]
            load.results_from_dict(load_data)
        for source_data in data["sources"]:
            source = self.sources[source_data["id"]]
            source.results_from_dict(data=source_data)
        for ground_data in data["grounds"]:
            ground = self.grounds[ground_data["id"]]
            ground.results_from_dict(ground_data)
        for p_ref_data in data["potential_refs"]:
            p_ref = self.potential_refs[p_ref_data["id"]]
            p_ref.results_from_dict(p_ref_data)

        # The results are now valid
        self._results_valid = True

    #
    # Properties to access the load flow results as dataframes
    #
    def _warn_invalid_results(self) -> None:
        """Warn when the network is invalid."""
        if not self._results_valid:
            warnings.warn(
                message=(
                    "The results of this network may be outdated. Please re-run a load flow to "
                    "ensure the validity of results."
                ),
                category=UserWarning,
                stacklevel=2,
            )

    @property
    def res_buses(self) -> pd.DataFrame:
        """The load flow results of the network buses.

        The results are returned as a dataframe with the following index:
            - `bus_id`: The id of the bus.
            - `phase`: The phase of the bus (in ``{'a', 'b', 'c', 'n'}``).
        and the following columns:
            - `potential`: The complex potential of the bus (in Volts) for the given phase.
        """
        self._warn_invalid_results()
        res_dict = {"bus_id": [], "phase": [], "potential": []}
        for bus_id, bus in self.buses.items():
            for potential, phase in zip(bus._res_potentials_getter(warning=False), bus.phases):
                res_dict["bus_id"].append(bus_id)
                res_dict["phase"].append(phase)
                res_dict["potential"].append(potential)
        res_df = (
            pd.DataFrame.from_dict(res_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "potential": complex})
            .set_index(["bus_id", "phase"])
        )
        return res_df

    @property
    def res_buses_voltages(self) -> pd.DataFrame:
        """The load flow results of the complex voltages of the buses (V).

        The voltages are computed from the potentials of the buses. If the bus has a neutral, the
        voltage is the line-to-neutral voltage. Otherwise, the voltage is the line-to-line voltage.
        The result dataframe has a ``phase`` index that depicts this behavior.

        The results are returned as a dataframe with the following index:
            - `bus_id`: The id of the bus.
            - `phase`: The phase of the bus (in ``{'an', 'bn', 'cn', 'ab', 'bc', 'ca'}``).
        and the following columns:
            - `voltage`: The complex voltage of the bus (in Volts) for the given phase.
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
    def res_branches(self) -> pd.DataFrame:
        """The load flow results of the network branches.

        The results are returned as a dataframe with the following index:
            - `branch_id`: The id of the branch.
            - `phase`: The phase of the branch (in ``{'a', 'b', 'c', 'n'}``).
        and the following columns:
            - `current1`: The complex current of the branch (in Amps) for the given phase at the
                first bus.
            - `current2`: The complex current of the branch (in Amps) for the given phase at the
                second bus.
            - `power1`: The complex power of the branch (in VoltAmps) for the given phase at the
                first bus.
            - `power2`: The complex power of the branch (in VoltAmps) for the given phase at the
                second bus.
            - `potential1`: The complex potential of the first bus (in Volts) for the given phase.
            - `potential2`: The complex potential of the second bus (in Volts) for the given phase.
        """
        self._warn_invalid_results()
        res_list = []
        for branch_id, branch in self.branches.items():
            currents1, currents2 = branch._res_currents_getter(warning=False)
            powers1, powers2 = branch._res_powers_getter(warning=False)
            potentials1, potentials2 = branch._res_potentials_getter(warning=False)
            res_list.extend(
                {
                    "branch_id": branch_id,
                    "phase": phase,
                    "current1": i1,
                    "current2": None,
                    "power1": s1,
                    "power2": None,
                    "potential1": v1,
                    "potential2": None,
                }
                for i1, s1, v1, phase in zip(currents1, powers1, potentials1, branch.phases1)
            )
            res_list.extend(
                {
                    "branch_id": branch_id,
                    "phase": phase,
                    "current1": None,
                    "current2": i2,
                    "power1": None,
                    "power2": s2,
                    "potential1": None,
                    "potential2": v2,
                }
                for i2, s2, v2, phase in zip(currents2, powers2, potentials2, branch.phases2)
            )

        res_df = (
            pd.DataFrame.from_records(res_list)
            .astype(
                {
                    "phase": _PHASE_DTYPE,
                    "current1": complex,
                    "current2": complex,
                    "power1": complex,
                    "power2": complex,
                    "potential1": complex,
                    "potential2": complex,
                }
            )
            .groupby(["branch_id", "phase"], observed=True)  # aggregate x1 and x2 for the same phase
            .mean()  # 2 values; only one is not nan -> keep it
            .dropna(how="all")  # if all values are nan -> drop the row (the phase does not exist)
        )
        return res_df

    @property
    def res_lines(self) -> pd.DataFrame:
        """The load flow results of the the network lines.

        This is similar to the :attr:`res_branches` property but provides more information that
        only apply to lines. This includes currents and complex power losses in the series
        components of the lines.

        The results are returned as a dataframe with the following index:
            - `line_id`: The id of the line.
            - `phase`: The phase of the line (in ``{'a', 'b', 'c', 'n'}``).

        and the following columns:
            - `current1`: The complex current of the line (in Amps) for the given phase at the
                first bus.
            - `current2`: The complex current of the line (in Amps) for the given phase at the
                second bus.
            - `power1`: The complex power of the line (in VoltAmps) for the given phase at the
                first bus.
            - `power2`: The complex power of the line (in VoltAmps) for the given phase at the
                second bus.
            - `potential1`: The complex potential of the first bus (in Volts) for the given phase.
            - `potential2`: The complex potential of the second bus (in Volts) for the given phase.
            - `series_losses`: The complex power losses of the line (in VoltAmps) for the given
                phase due to the series and mutual impedances.
            - `series_current`: The complex current in the series impedance of the line (in Amps)
                for the given phase.

        Additional information can be easily computed from this dataframe. For example:

        * To get the active power losses, use the real part of the complex power losses
        * To get the total power losses, add the columns ``powers1 + powers2``
        * To get the power losses in the shunt components of the line, subtract the series losses
          from the total power losses computed in the previous step:
          ``(powers1 + powers2) - series_losses``
        * To get the currents in the shunt components of the line:
          - For the first bus, subtract the columns ``current1 - series_current``
          - For the second bus, add the columns ``series_current + current2``
        """
        self._warn_invalid_results()
        res_dict = {
            "line_id": [],
            "phase": [],
            "current1": [],
            "current2": [],
            "power1": [],
            "power2": [],
            "potential1": [],
            "potential2": [],
            "series_losses": [],
            "series_current": [],
        }
        for branch in self.branches.values():
            if not isinstance(branch, Line):
                continue
            potentials = branch._res_potentials_getter(warning=False)
            currents = branch._res_currents_getter(warning=False)
            powers = branch._res_powers_getter(warning=False)
            series_losses = branch._res_series_power_losses_getter(warning=False)
            series_currents = branch._res_series_currents_getter(warning=False)
            for i1, i2, s1, s2, v1, v2, s_series, i_series, phase in zip(
                *currents, *powers, *potentials, series_losses, series_currents, branch.phases
            ):
                res_dict["line_id"].append(branch.id)
                res_dict["phase"].append(phase)
                res_dict["current1"].append(i1)
                res_dict["current2"].append(i2)
                res_dict["power1"].append(s1)
                res_dict["power2"].append(s2)
                res_dict["potential1"].append(v1)
                res_dict["potential2"].append(v2)
                res_dict["series_losses"].append(s_series)
                res_dict["series_current"].append(i_series)
        return (
            pd.DataFrame(res_dict)
            .astype(
                {
                    "phase": _PHASE_DTYPE,
                    **{k: complex for k in res_dict if k not in ("phase", "line_id")},
                },
            )
            .set_index(["line_id", "phase"])
        )

    @property
    def res_loads(self) -> pd.DataFrame:
        """The load flow results of the network loads.

        The results are returned as a dataframe with the following index:
            - `load_id`: The id of the load.
            - `phase`: The phase of the load (in ``{'a', 'b', 'c', 'n'}``).
        and the following columns:
            - `current`: The complex current of the load (in Amps) for the given phase.
            - `power`: The complex power of the load (in VoltAmps) for the given phase.
            - `potential`: The complex potential of the load (in Volts) for the given phase.
        """
        self._warn_invalid_results()
        res_dict = {"load_id": [], "phase": [], "current": [], "power": [], "potential": []}
        for load_id, load in self.loads.items():
            currents = load._res_currents_getter(warning=False)
            powers = load._res_powers_getter(warning=False)
            potentials = load._res_potentials_getter(warning=False)
            for i, s, v, phase in zip(currents, powers, potentials, load.phases):
                res_dict["load_id"].append(load_id)
                res_dict["phase"].append(phase)
                res_dict["current"].append(i)
                res_dict["power"].append(s)
                res_dict["potential"].append(v)
        res_df = (
            pd.DataFrame.from_dict(res_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "current": complex, "power": complex, "potential": complex})
            .set_index(["load_id", "phase"])
        )
        return res_df

    @property
    def res_loads_voltages(self) -> pd.DataFrame:
        """The load flow results of the complex voltages of the loads (V).

        The results are returned as a dataframe with the following index:
            - `load_id`: The id of the load.
            - `phase`: The phase of the load (in ``{'an', 'bn', 'cn'}`` for wye loads and in
                ``{'ab', 'bc', 'ca'}`` for delta loads.).
        and the following columns:
            - `voltage`: The complex voltage of the load (in Volts) for the given *phase*.
        """
        self._warn_invalid_results()
        voltages_dict = {"load_id": [], "phase": [], "voltage": []}
        for load_id, load in self.loads.items():
            for voltage, phase in zip(load._res_voltages_getter(warning=False), load.voltage_phases):
                voltages_dict["load_id"].append(load_id)
                voltages_dict["phase"].append(phase)
                voltages_dict["voltage"].append(voltage)
        voltages_df = (
            pd.DataFrame.from_dict(voltages_dict, orient="columns")
            .astype({"phase": _VOLTAGE_PHASES_DTYPE, "voltage": complex})
            .set_index(["load_id", "phase"])
        )
        return voltages_df

    @property
    def res_loads_flexible_powers(self) -> pd.DataFrame:
        """The load flow results of the flexible powers of the "flexible" loads.

        The results are returned as a dataframe with the following index:
            - `load_id`: The id of the load.
            - `phase`: The element phases of the load (in ``{'an', 'bn', 'cn', 'ab', 'bc', 'ca'}``).
        and the following columns:
            - `power`: The complex flexible power of the load (in VoltAmps) for the given phase.

        Note that the flexible powers are the powers that flow in the load elements and not in the
        lines. These are only different in case of delta loads. To access the powers that flow in
        the lines, use the ``power`` column from the :attr:`res_loads` property instead.
        """
        self._warn_invalid_results()
        loads_dict = {"load_id": [], "phase": [], "power": []}
        for load_id, load in self.loads.items():
            if not (isinstance(load, PowerLoad) and load.is_flexible):
                continue
            for power, phase in zip(load._res_flexible_powers_getter(warning=False), load.voltage_phases):
                loads_dict["load_id"].append(load_id)
                loads_dict["phase"].append(phase)
                loads_dict["power"].append(power)
        powers_df = (
            pd.DataFrame.from_dict(loads_dict, orient="columns")
            .astype({"phase": _VOLTAGE_PHASES_DTYPE, "power": complex})
            .set_index(["load_id", "phase"])
        )
        return powers_df

    @property
    def res_sources(self) -> pd.DataFrame:
        """The load flow results of the network sources.

        The results are returned as a dataframe with the following index:
            - `source_id`: The id of the source.
            - `phase`: The phase of the source (in ``{'a', 'b', 'c', 'n'}``).
        and the following columns:
            - `current`: The complex current of the source (in Amps) for the given phase.
            - `power`: The complex power of the source (in VoltAmps) for the given phase.
            - `potential`: The complex potential of the source (in Volts) for the given phase.
        """
        self._warn_invalid_results()
        res_dict = {"source_id": [], "phase": [], "current": [], "power": [], "potential": []}
        for source_id, source in self.sources.items():
            currents = source._res_currents_getter(warning=False)
            powers = source._res_powers_getter(warning=False)
            potentials = source._res_potentials_getter(warning=False)
            for i, s, v, phase in zip(currents, powers, potentials, source.phases):
                res_dict["source_id"].append(source_id)
                res_dict["phase"].append(phase)
                res_dict["current"].append(i)
                res_dict["power"].append(s)
                res_dict["potential"].append(v)
        res_df = (
            pd.DataFrame.from_dict(res_dict, orient="columns")
            .astype({"phase": _PHASE_DTYPE, "current": complex, "power": complex, "potential": complex})
            .set_index(["source_id", "phase"])
        )
        return res_df

    @property
    def res_grounds(self) -> pd.DataFrame:
        """The load flow results of the network grounds.

        The results are returned as a dataframe with the following index:
            - `ground_id`: The id of the ground.
        and the following columns:
            - `potential`: The complex potential of the ground (in Volts).
        """
        self._warn_invalid_results()
        res_dict = {"ground_id": [], "potential": []}
        for ground in self.grounds.values():
            potential = ground._res_potential_getter(warning=False)
            res_dict["ground_id"].append(ground.id)
            res_dict["potential"].append(potential)
        res_df = (
            pd.DataFrame.from_dict(res_dict, orient="columns").astype({"potential": complex}).set_index(["ground_id"])
        )
        return res_df

    @property
    def res_potential_refs(self) -> pd.DataFrame:
        """The load flow results of the network potential references.

        The results are returned as a dataframe with the following index:
            - `potential_ref_id`: The id of the potential reference.
        and the following columns:
            - `current`: The complex current of the potential reference (in Amps). If the load flow
                converged, this should be zero.
        """
        self._warn_invalid_results()
        res_dict = {"potential_ref_id": [], "current": []}
        for p_ref in self.potential_refs.values():
            current = p_ref._res_current_getter(warning=False)
            res_dict["potential_ref_id"].append(p_ref.id)
            res_dict["current"].append(current)
        res_df = (
            pd.DataFrame.from_dict(res_dict, orient="columns")
            .astype({"current": complex})
            .set_index(["potential_ref_id"])
        )
        return res_df

    def clear_short_circuits(self):
        """Remove the short-circuits of all the buses."""
        for bus in self.buses.values():
            bus.clear_short_circuits()

    #
    # Internal methods, please do not use
    #
    def _connect_element(self, element: Element) -> None:
        """Connect an element to the network.

        When an element is added to the network, extra processing is done to keep the network valid. This method is
        used in the by the `network` setter of `Element` instances to add the element to the internal dictionary of
        `self`.

        Args:
            element:
                The element to add. Only lines, loads, buses and sources can be added.
        """
        # The C++ electrical network and the tape will be recomputed
        if isinstance(element, Bus):
            self.buses[element.id] = element
        elif isinstance(element, AbstractLoad):
            self.loads[element.id] = element
        elif isinstance(element, AbstractBranch):
            self.branches[element.id] = element
        elif isinstance(element, VoltageSource):
            self.sources[element.id] = element
        else:
            msg = "Only lines, loads, buses and sources can be added to the network."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        element._network = self
        self._valid = False
        self._results_valid = False

    def _disconnect_element(self, element: Element) -> None:
        """Remove an element of the network.

        When an element is removed from the network, extra processing is needed to keep the network valid. This method
        is used in the by the `network` setter of `Element` instances (when the provided network is `None`) to remove
        the element to the internal dictionary of `self`.

        Args:
            element:
                The element to remove.
        """
        # The C++ electrical network and the tape will be recomputed
        if isinstance(element, (Bus, AbstractBranch)):
            msg = f"{element!r} is a {type(element).__name__} and it cannot be disconnected from a network."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        elif isinstance(element, AbstractLoad):
            self.loads.pop(element.id)
        elif isinstance(element, VoltageSource):
            self.sources.pop(element.id)
        else:
            msg = f"{element!r} is not a valid load or source."
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
        elements: set[Element] = set()
        elements.update(self.buses.values())
        elements.update(self.branches.values())
        elements.update(self.loads.values())
        elements.update(self.sources.values())
        elements.update(self.grounds.values())
        elements.update(self.potential_refs.values())

        found_source = False
        for element in elements:
            # Check connected elements and check network assignment
            for adj_element in element._connected_elements:
                if adj_element not in elements:
                    msg = (
                        f"{type(adj_element).__name__} element ({adj_element.id!r}) is connected "
                        f"to {type(element).__name__} element ({element.id!r}) but "
                    )
                    if constructed:
                        msg += "was not passed to the ElectricalNetwork constructor."
                    else:
                        msg += "has not been added to the network. It must be added with 'connect'."
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
        visited_elements: set[Element] = set()
        for initial_element in elements:
            if initial_element in visited_elements or isinstance(initial_element, Transformer):
                continue
            visited_elements.add(initial_element)
            connected_component: list[Element] = []
            to_visit = [initial_element]
            while to_visit:
                element = to_visit.pop(-1)
                connected_component.append(element)
                for connected_element in element._connected_elements:
                    if connected_element not in visited_elements and not isinstance(connected_element, Transformer):
                        to_visit.append(connected_element)
                        visited_elements.add(connected_element)

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
    # Network saving/loading
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        """Construct an electrical network from a dict created with :meth:`to_dict`.

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
            sources=sources,
            grounds=grounds,
            potential_refs=p_refs,
        )

    def to_dict(self, include_geometry: bool = True) -> JsonDict:
        """Convert the electrical network to a dictionary.

        Args:
            include_geometry:
                If False, the geometry will not be added to the network dictionary.
        """
        return network_to_dict(self, include_geometry=include_geometry)

    #
    # Results saving/loading
    #
    def results_from_dict(self, data: JsonDict) -> None:
        """Load the results of a load flow from a dict created by :meth:`results_to_dict`.

        The results are stored in the network elements.

        Args:
            data:
                The dictionary containing the results as returned by the solver.
        """
        # Checks on the provided data
        for key, self_elements, name in (
            ("buses", self.buses, "Bus"),
            ("branches", self.branches, "Branch"),
            ("loads", self.loads, "Load"),
            ("sources", self.sources, "Source"),
            ("grounds", self.grounds, "Ground"),
            ("potential_refs", self.potential_refs, "PotentialRef"),
        ):
            seen = set()
            for element_data in data[key]:
                element_id = element_data["id"]
                if element_id not in self_elements:
                    msg = f"{name} {element_id!r} appears in the results but is not present in the network."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_FLOW_RESULT)
                seen.add(element_id)
            if missing_elements := self_elements.keys() - seen:
                msg = (
                    f"The following {key} are present in the network but not in the results: "
                    f"{sorted(missing_elements)}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_FLOW_RESULT)

        # The results are assigned to all elements
        self._results_from_dict(data)

    def _results_to_dict(self, warning: bool) -> JsonDict:
        """Get the voltages and currents computed by the load flow and return them as a dict."""
        if warning:
            self._warn_invalid_results()  # Warn only once if asked
        return {
            "info": self.res_info,
            "buses": [bus._results_to_dict(False) for bus in self.buses.values()],
            "branches": [branch._results_to_dict(False) for branch in self.branches.values()],
            "loads": [load._results_to_dict(False) for load in self.loads.values()],
            "sources": [source._results_to_dict(False) for source in self.sources.values()],
            "grounds": [ground._results_to_dict(False) for ground in self.grounds.values()],
            "potential_refs": [p_ref._results_to_dict(False) for p_ref in self.potential_refs.values()],
        }

    #
    # DGS interface
    #
    @classmethod
    def from_dgs(cls, path: StrPath) -> Self:
        """Construct an electrical network from json DGS file (PowerFactory).

        Args:
            path:
                The path to the network DGS data file.

        Returns:
            The constructed network.
        """
        buses, branches, loads, sources, grounds, potential_refs = network_from_dgs(path, en_class=cls)
        return cls(
            buses=buses,
            branches=branches,
            loads=loads,
            sources=sources,
            grounds=grounds,
            potential_refs=potential_refs,
        )

    #
    # Catalogue of networks
    #
    @classmethod
    def catalogue_path(cls) -> Path:
        return Path(resources.files("roseau.load_flow") / "data" / "networks").expanduser().absolute()

    @classmethod
    def catalogue_data(cls) -> JsonDict:
        return json.loads((cls.catalogue_path() / "Catalogue.json").read_text())

    @classmethod
    def from_catalogue(cls, name: Union[str, re.Pattern[str]], load_point_name: Union[str, re.Pattern[str]]) -> Self:
        """Build a network from one in the catalogue.

        Args:
            name:
                The name of the network to get from the catalogue. It can be a regular expression.

            load_point_name:
                The name of the load point to get. For each network, several load points may be available. It can be
                a regular expression.

        Returns:
            The selected network
        """
        # Get the catalogue data
        catalogue_data = cls.catalogue_data()

        # Match on the name
        if isinstance(name, re.Pattern):
            name_pattern = name
            name = name.pattern
            match_names_list = [k for k in catalogue_data if name_pattern.match(k)]
        else:
            try:
                name_pattern = re.compile(pattern=name, flags=re.IGNORECASE)
                match_names_list = [k for k in catalogue_data if name_pattern.match(k)]
            except re.error:
                name_pattern = name.lower()
                match_names_list = [k for k in catalogue_data if k.lower() == name_pattern]
        if not match_names_list:
            msg = (
                f"No network matching the name {name!r} has been found. "
                f"Please look at the catalogue using the `print_catalogue` class method."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND)
        elif len(match_names_list) > 1:
            msg_part = textwrap.shorten(", ".join(repr(x) for x in sorted(match_names_list)), width=500)
            msg = f"Several networks matching the name {name!r} have been found: {msg_part}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND)
        name = match_names_list[0]

        # Match on the load point
        c_data = catalogue_data[name]
        available_load_points = c_data["load_points"]
        if isinstance(load_point_name, re.Pattern):
            load_point_name_pattern = load_point_name
            load_point_name = load_point_name.pattern
            match_load_point_names_list = [k for k in available_load_points if load_point_name_pattern.match(k)]
        else:
            try:
                load_point_name_pattern = re.compile(pattern=load_point_name, flags=re.IGNORECASE)
                match_load_point_names_list = [k for k in available_load_points if load_point_name_pattern.match(k)]
            except re.error:
                load_point_name_pattern = load_point_name.lower()
                match_load_point_names_list = [k for k in available_load_points if k.lower() == load_point_name_pattern]
        if not match_load_point_names_list:
            msg_part = textwrap.shorten(", ".join(repr(x) for x in sorted(available_load_points)), width=500)
            msg = (
                f"No load point matching the name {load_point_name!r} has been found for the network {name!r}. "
                f"Available load points are {msg_part}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND)
        elif len(match_load_point_names_list) > 1:
            msg_part = textwrap.shorten(", ".join(repr(x) for x in sorted(match_load_point_names_list)), width=500)
            msg = (
                f"Several load points matching the name {load_point_name!r} have been found for the network "
                f"{name!r}: {msg_part}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND)
        load_point_name = match_load_point_names_list[0]

        # Get the data from the Json file
        path = cls.catalogue_path() / f"{name}_{load_point_name}.json"
        if not path.exists():  # pragma: no cover
            msg = f"The file {path} has not been found while it should exist. Please post an issue on GitHub."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_MISSING)

        return cls.from_json(path=path)

    @classmethod
    def print_catalogue(
        cls,
        name: Optional[Union[str, re.Pattern[str]]] = None,
        load_point_name: Optional[Union[str, re.Pattern[str]]] = None,
    ) -> None:
        """Print the catalogue of available networks.

        Args:
            name:
                The name of the networks to display. It can be a regular expression. For instance, `name="lv"` will
                match all the network name starting with "lv" (ignoring case).

            load_point_name:
                Only networks having a load point matching this string or regular expression will be displayed.
        """
        # Get the catalogue data
        catalogue_data = cls.catalogue_data()

        # Start creating a table to display the results
        table = Table(title="Available Networks")
        table.add_column("Name")
        table.add_column("Nb buses", justify="right", style="color(1)", header_style="color(1)")
        table.add_column("Nb branches", justify="right", style="color(2)", header_style="color(2)")
        table.add_column("Nb loads", justify="right", style="color(3)", header_style="color(3)")
        table.add_column("Nb sources", justify="right", style="color(4)", header_style="color(4)")
        table.add_column("Nb grounds", justify="right", style="color(5)", header_style="color(5)")
        table.add_column("Nb potential refs", justify="right", style="color(6)", header_style="color(6)")
        table.add_column("Available load points", justify="right", style="color(9)", header_style="color(9)")
        empty_table = True

        # Match on the name
        match_names_list = cls._filter_name(name=name, catalogue_data=catalogue_data)

        # Match on load point name
        if load_point_name is None:
            load_point_name_pattern = None

            def match_load_point_function(x: str) -> bool:
                return True

        elif isinstance(load_point_name, re.Pattern):
            load_point_name_pattern = load_point_name
            load_point_name = load_point_name.pattern
            match_load_point_function = load_point_name_pattern.match
        else:
            try:
                load_point_name_pattern = re.compile(pattern=load_point_name, flags=re.IGNORECASE)
                match_load_point_function = load_point_name_pattern.match
            except re.error:
                load_point_name_pattern = name.lower()

                def match_load_point_function(x: str) -> bool:
                    nonlocal load_point_name_pattern
                    return x.lower() == load_point_name_pattern

        # Iterate over the networks
        for c_name in match_names_list:
            c_data = catalogue_data[c_name]
            available_load_points = c_data["load_points"]
            if any(match_load_point_function(x) for x in available_load_points):
                empty_table = False
                table.add_row(
                    c_name,
                    str(c_data["nb_buses"]),
                    str(c_data["nb_branches"]),
                    str(c_data["nb_loads"]),
                    str(c_data["nb_sources"]),
                    str(c_data["nb_grounds"]),
                    str(c_data["nb_potential_refs"]),
                    ", ".join(repr(x) for x in sorted(c_data["load_points"])),
                )

        # Handle the case of an empty table
        if empty_table:
            msg = "No networks can be found in the catalogue"
            if name is not None and load_point_name is not None:
                msg += f" with the name {name!r} and having a load point named {load_point_name!r}"
            elif name is not None:
                msg += f" with the name {name!r}"
            elif load_point_name is not None:
                msg += f" having a load point named {load_point_name!r}"
            msg += "!"
            console.print(msg)
        else:
            console.print(table)

    @staticmethod
    def _filter_name(name: Optional[Union[str, re.Pattern[str]]], catalogue_data: JsonDict) -> list[str]:
        """Filter the catalogue using the network name.

        Args:
            name:
                The optional name to use as a filter.

            catalogue_data:
                The catalogue of available networks. It avoids an additional read.

        Returns:
            The list of network names matching the provided one.
        """
        if name is None:
            match_names_list = list(catalogue_data)
        elif isinstance(name, re.Pattern):
            match_names_list = [k for k in catalogue_data if name.match(k)]
        else:
            try:
                name_pattern = re.compile(pattern=name, flags=re.IGNORECASE)
                match_names_list = [k for k in catalogue_data if name_pattern.match(k)]
            except re.error:
                name_pattern = name.lower()
                match_names_list = [k for k in catalogue_data if k.lower() == name_pattern]

        return match_names_list
