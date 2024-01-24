"""
This module defines the electrical network class.
"""
import json
import logging
import re
import time
import warnings
from collections.abc import Iterable, Mapping, Sized
from importlib import resources
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, TypeVar

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import CRS
from typing_extensions import Self

from roseau.load_flow._solvers import AbstractSolver
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
from roseau.load_flow.typing import Id, JsonDict, MapOrSeq, Solver, StrPath
from roseau.load_flow.utils import CatalogueMixin, JsonMixin, _optional_deps
from roseau.load_flow.utils.types import _DTYPES, VoltagePhaseDtype
from roseau.load_flow_engine.cy_engine import CyElectricalNetwork

if TYPE_CHECKING:
    from networkx import Graph

logger = logging.getLogger(__name__)

_E = TypeVar("_E", bound=Element)


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
    """

    _DEFAULT_SOLVER: Solver = "newton_goldstein"

    #
    # Methods to build an electrical network
    #
    def __init__(
        self,
        buses: MapOrSeq[Bus],
        branches: MapOrSeq[AbstractBranch],
        loads: MapOrSeq[AbstractLoad],
        sources: MapOrSeq[VoltageSource],
        grounds: MapOrSeq[Ground],
        potential_refs: MapOrSeq[PotentialRef],
    ) -> None:
        self.buses = self._elements_as_dict(buses, RoseauLoadFlowExceptionCode.BAD_BUS_ID)
        self.branches = self._elements_as_dict(branches, RoseauLoadFlowExceptionCode.BAD_BRANCH_ID)
        self.loads = self._elements_as_dict(loads, RoseauLoadFlowExceptionCode.BAD_LOAD_ID)
        self.sources = self._elements_as_dict(sources, RoseauLoadFlowExceptionCode.BAD_SOURCE_ID)
        self.grounds = self._elements_as_dict(grounds, RoseauLoadFlowExceptionCode.BAD_GROUND_ID)
        self.potential_refs = self._elements_as_dict(potential_refs, RoseauLoadFlowExceptionCode.BAD_POTENTIAL_REF_ID)

        self._elements: list[Element] = []
        self._check_validity(constructed=False)
        self._create_network()
        self._valid = True
        self._results_valid: bool = False
        self._solver = AbstractSolver.from_dict(data={"name": self._DEFAULT_SOLVER, "params": {}}, network=self)

    def __repr__(self) -> str:
        def count_repr(__o: Sized, /, singular: str, plural: str | None = None) -> str:
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
    def _elements_as_dict(elements: MapOrSeq[_E], error_code: RoseauLoadFlowExceptionCode) -> dict[Id, _E]:
        """Convert a sequence or a mapping of elements to a dictionary of elements with their IDs as keys."""
        typ = error_code.name.removeprefix("BAD_").removesuffix("_ID").replace("_", " ")
        elements_dict: dict[Id, _E] = {}
        if isinstance(elements, Mapping):
            for element_id, element in elements.items():
                if element.id != element_id:
                    msg = f"{typ.capitalize()} ID mismatch: {element_id!r} != {element.id!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg, code=error_code)
                elements_dict[element_id] = element
        else:
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
        data = []
        for bus in self.buses.values():
            min_voltage = bus.min_voltage.magnitude if bus.min_voltage is not None else float("nan")
            max_voltage = bus.max_voltage.magnitude if bus.max_voltage is not None else float("nan")
            data.append((bus.id, bus.phases, min_voltage, max_voltage, bus.geometry))
        return gpd.GeoDataFrame(
            data=pd.DataFrame.from_records(
                data=data,
                columns=["id", "phases", "min_voltage", "max_voltage", "geometry"],
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
    def transformers_frame(self) -> gpd.GeoDataFrame:
        """The transformers of the network as a geo dataframe.

        This is similar to :attr:`branches_frame` but only contains the transformers. It has a
        `max_power` column that contains the maximum power loading (VA) of the transformers.
        """
        data = []
        for branch in self.branches.values():
            if not isinstance(branch, Transformer):
                continue
            max_power = branch.max_power.magnitude if branch.max_power is not None else float("nan")
            data.append(
                (
                    branch.id,
                    branch.phases1,
                    branch.phases2,
                    branch.bus1.id,
                    branch.bus2.id,
                    branch.parameters.id,
                    max_power,
                    branch.geometry,
                )
            )
        return gpd.GeoDataFrame(
            data=pd.DataFrame.from_records(
                data=data,
                columns=["id", "phases1", "phases2", "bus1_id", "bus2_id", "parameters_id", "max_power", "geometry"],
                index="id",
            ),
            geometry="geometry",
            crs=CRS("EPSG:4326"),
        )

    @property
    def lines_frame(self) -> gpd.GeoDataFrame:
        """The lines of the network as a geo dataframe.

        This is similar to :attr:`branches_frame` but only contains the lines. It has a
        `max_current` column that contains the maximum current loading (A) of the lines.
        """
        data = []
        for branch in self.branches.values():
            if not isinstance(branch, Line):
                continue
            max_current = branch.max_current.magnitude if branch.max_current is not None else float("nan")
            data.append(
                (
                    branch.id,
                    branch.phases,
                    branch.bus1.id,
                    branch.bus2.id,
                    branch.parameters.id,
                    max_current,
                    branch.geometry,
                )
            )
        return gpd.GeoDataFrame(
            data=pd.DataFrame.from_records(
                data=data,
                columns=["id", "phases", "bus1_id", "bus2_id", "parameters_id", "max_current", "geometry"],
                index="id",
            ),
            geometry="geometry",
            crs=CRS("EPSG:4326"),
        )

    @property
    def switches_frame(self) -> gpd.GeoDataFrame:
        """The switches of the network as a geo dataframe.

        This is similar to :attr:`branches_frame` but only contains the switches.
        """
        data = []
        for branch in self.branches.values():
            if not isinstance(branch, Switch):
                continue
            data.append((branch.id, branch.phases, branch.bus1.id, branch.bus2.id, branch.geometry))
        return gpd.GeoDataFrame(
            data=pd.DataFrame.from_records(
                data=data,
                columns=["id", "phases", "bus1_id", "bus2_id", "geometry"],
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
    # Helpers to analyze the network
    #
    @property
    def buses_clusters(self) -> list[set[Id]]:
        """Sets of galvanically connected buses, i.e buses connected by lines or a switches.

        This can be useful to isolate parts of the network for localized analysis. For example, to
        study a LV subnetwork of a MV feeder.

        See Also:
            :meth:`Bus.get_connected_buses() <roseau.load_flow.models.Bus.get_connected_buses>`: Get
            the buses in the same galvanically isolated section as a certain bus.
        """
        visited: set[Id] = set()
        result: list[set[Id]] = []
        for bus in self.buses.values():
            if bus.id in visited:
                continue
            bus_cluster = set(bus.get_connected_buses())
            visited |= bus_cluster
            result.append(bus_cluster)
        return result

    def to_graph(self) -> "Graph":
        """Create a networkx graph from this electrical network.

        The graph contains the geometries of the buses in the nodes data and the geometries and
        branch types in the edges data.

        Note:
            This method requires *networkx* to be installed. You can install it with the ``"graph"``
            extra if you are using pip: ``pip install "roseau-load-flow[graph]"``.
        """
        nx = _optional_deps.networkx
        graph = nx.Graph()
        for bus in self.buses.values():
            graph.add_node(bus.id, geom=bus.geometry)
        for branch in self.branches.values():
            graph.add_edge(branch.bus1.id, branch.bus2.id, id=branch.id, type=branch.branch_type, geom=branch.geometry)
        return graph

    #
    # Method to solve a load flow
    #
    def solve_load_flow(
        self,
        max_iterations: int = 20,
        tolerance: float = 1e-6,
        warm_start: bool = True,
        solver: Solver = _DEFAULT_SOLVER,
        solver_params: JsonDict | None = None,
    ) -> tuple[int, float]:
        """Solve the load flow for this network.

        To get the results of the load flow for the whole network, use the `res_` properties on the
        network (e.g. ``print(net.res_buses``). To get the results for a specific element, use the
        `res_` properties on the element (e.g. ``print(net.buses["bus1"].res_potentials)``.

        You need to activate the license before calling this method. Alternatively you may set the
        environment variable ``ROSEAU_LOAD_FLOW_LICENSE_KEY`` to your license key and it will be
        picked automatically when calling this method. See the :ref:`license` page for more
        information.

        Args:
            max_iterations:
                The maximum number of allowed iterations.

            tolerance:
                Tolerance needed for the convergence.

            warm_start:
                If true (the default), the solver is initialized with the potentials of the last
                successful load flow result (if any). Otherwise, the potentials are reset to their
                initial values.

            solver:
                The name of the solver to use for the load flow. The options are:
                    - ``'newton'``: the classical Newton-Raphson solver.
                    - ``'newton_goldstein'``: the Newton-Raphson solver with the Goldstein and
                      Price linear search.

            solver_params:
                A dictionary of parameters used by the solver. Available parameters depend on the
                solver chosen. For more information, see the :ref:`solvers` page.

        Returns:
            The number of iterations performed and the residual error at the last iteration.
        """
        if not self._valid:
            self._check_validity(constructed=False)
            self._create_network()  # <-- calls _propagate_potentials, no warm start
            self._solver.update_network(self)

        # Update solver
        if solver != self._solver.name:
            solver_params = solver_params if solver_params is not None else {}
            self._solver = AbstractSolver.from_dict(data={"name": solver, "params": solver_params}, network=self)
        elif solver_params is not None:
            self._solver.update_params(solver_params)

        if not warm_start:
            self._reset_inputs()

        start = time.perf_counter()
        try:
            iterations, residual = self._solver.solve_load_flow(max_iterations=max_iterations, tolerance=tolerance)
        except RuntimeError as e:
            self._handle_error(e)

        end = time.perf_counter()

        if iterations == max_iterations:
            msg = (
                f"The load flow did not converge after {iterations} iterations. The norm of the residuals is "
                f"{residual:5n}"
            )
            logger.error(msg=msg)
            raise RoseauLoadFlowException(
                msg, RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE, iterations, residual
            )

        logger.debug(f"The load flow converged after {iterations} iterations and {end - start:.3n} s.")

        # Lazily update the results of the elements
        for element in chain(
            self.buses.values(),
            self.branches.values(),
            self.loads.values(),
            self.sources.values(),
            self.grounds.values(),
            self.potential_refs.values(),
        ):
            element._fetch_results = True

        # The results are now valid
        self._results_valid = True

        return iterations, residual

    def _handle_error(self, e: RuntimeError) -> NoReturn:
        msg = e.args[0]
        if msg.startswith("0 "):
            msg = f"The license cannot be validated. The detailed error message is {msg[2:]!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.LICENSE_ERROR) from e
        else:
            assert msg.startswith("1 ")
            msg = msg[2:]
            zero_elements_index, inf_elements_index = self._solver._cy_solver.analyse_jacobian()
            if zero_elements_index:
                zero_elements = [self._elements[i] for i in zero_elements_index]
                printable_elements = ", ".join(f"{type(e).__name__}({e.id!r})" for e in zero_elements)
                msg += (
                    f"The problem seems to come from the elements [{printable_elements}] that have at least one "
                    f"disconnected phase. "
                )
            if inf_elements_index:
                inf_elements = [self._elements[i] for i in inf_elements_index]
                printable_elements = ", ".join(f"{type(e).__name__}({e.id!r})" for e in inf_elements)
                msg += (
                    f"The problem seems to come from the elements [{printable_elements}] that induce infinite "
                    f"values. This might be caused by flexible loads with very high alpha."
                )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_JACOBIAN) from e

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
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for bus_id, bus in self.buses.items():
            for potential, phase in zip(bus._res_potentials_getter(warning=False), bus.phases, strict=True):
                res_dict["bus_id"].append(bus_id)
                res_dict["phase"].append(phase)
                res_dict["potential"].append(potential)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["bus_id", "phase"])

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
            - `min_voltage`: The minimum voltage of the bus (in Volts).
            - `max_voltage`: The maximum voltage of the bus (in Volts).
        """
        self._warn_invalid_results()
        voltages_dict = {
            "bus_id": [],
            "phase": [],
            "voltage": [],
            "min_voltage": [],
            "max_voltage": [],
            "violated": [],
        }
        dtypes = {c: _DTYPES[c] for c in voltages_dict} | {"phase": VoltagePhaseDtype}
        for bus_id, bus in self.buses.items():
            min_voltage = bus._min_voltage
            max_voltage = bus._max_voltage
            voltage_limits_set = False

            if min_voltage is None:
                min_voltage = float("nan")
            else:
                voltage_limits_set = True
            if max_voltage is None:
                max_voltage = float("nan")
            else:
                voltage_limits_set = True
            for voltage, phase in zip(bus._res_voltages_getter(warning=False), bus.voltage_phases, strict=True):
                voltage_abs = abs(voltage)
                violated = (voltage_abs < min_voltage or voltage_abs > max_voltage) if voltage_limits_set else None
                voltages_dict["bus_id"].append(bus_id)
                voltages_dict["phase"].append(phase)
                voltages_dict["voltage"].append(voltage)
                voltages_dict["min_voltage"].append(min_voltage)
                voltages_dict["max_voltage"].append(max_voltage)
                voltages_dict["violated"].append(violated)
        return pd.DataFrame(voltages_dict).astype(dtypes).set_index(["bus_id", "phase"])

    @property
    def res_branches(self) -> pd.DataFrame:
        """The load flow results of the network branches.

        The results are returned as a dataframe with the following index:
            - `branch_id`: The id of the branch.
            - `phase`: The phase of the branch (in ``{'a', 'b', 'c', 'n'}``).
        and the following columns:
            - `branch_type`: The type of the branch, can be ``{'line', 'transformer', 'switch'}``.
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
        res_dict = {
            "branch_id": [],
            "phase": [],
            "branch_type": [],
            "current1": [],
            "current2": [],
            "power1": [],
            "power2": [],
            "potential1": [],
            "potential2": [],
        }
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for branch_id, branch in self.branches.items():
            currents1, currents2 = branch._res_currents_getter(warning=False)
            potentials1, potentials2 = branch._res_potentials_getter(warning=False)
            powers1, powers2 = branch._res_powers_getter(warning=False, pot1=potentials1, pot2=potentials2)
            phases = sorted(set(branch.phases1) | set(branch.phases2))
            for phase in phases:
                if phase in branch.phases1:
                    idx1 = branch.phases1.index(phase)
                    i1, s1, v1 = currents1[idx1], powers1[idx1], potentials1[idx1]
                else:
                    i1, s1, v1 = None, None, None
                if phase in branch.phases2:
                    idx2 = branch.phases2.index(phase)
                    i2, s2, v2 = currents2[idx2], powers2[idx2], potentials2[idx2]
                else:
                    i2, s2, v2 = None, None, None
                res_dict["branch_id"].append(branch_id)
                res_dict["phase"].append(phase)
                res_dict["branch_type"].append(branch.branch_type)
                res_dict["current1"].append(i1)
                res_dict["current2"].append(i2)
                res_dict["power1"].append(s1)
                res_dict["power2"].append(s2)
                res_dict["potential1"].append(v1)
                res_dict["potential2"].append(v2)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["branch_id", "phase"])

    @property
    def res_transformers(self) -> pd.DataFrame:
        """The load flow results of the network transformers.

        This is similar to the :attr:`res_branches` property but provides more information that
        only apply to transformers.

        The results are returned as a dataframe with the following index:
            - `transformer_id`: The id of the transformer.
            - `phase`: The phase of the transformer (in ``{'a', 'b', 'c', 'n'}``).

        and the following columns:
            - `current1`: The complex current of the transformer (in Amps) for the given phase at the
                first bus.
            - `current2`: The complex current of the transformer (in Amps) for the given phase at the
                second bus.
            - `power1`: The complex power of the transformer (in VoltAmps) for the given phase at the
                first bus.
            - `power2`: The complex power of the transformer (in VoltAmps) for the given phase at the
                second bus.
            - `potential1`: The complex potential of the first bus (in Volts) for the given phase.
            - `potential2`: The complex potential of the second bus (in Volts) for the given phase.
            - `max_power`: The maximum power loading (in VoltAmps) of the transformer.

        Note that values for missing phases are set to ``nan``. For example, a "Dyn" transformer
        has the phases "abc" on the primary side and "abcn" on the secondary side, so the primary
        side values for current, power, and potential for phase "n" will be ``nan``.
        """
        self._warn_invalid_results()
        res_dict = {
            "transformer_id": [],
            "phase": [],
            "current1": [],
            "current2": [],
            "power1": [],
            "power2": [],
            "potential1": [],
            "potential2": [],
            "max_power": [],
            "violated": [],
        }
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for branch in self.branches.values():
            if not isinstance(branch, Transformer):
                continue
            currents1, currents2 = branch._res_currents_getter(warning=False)
            potentials1, potentials2 = branch._res_potentials_getter(warning=False)
            powers1, powers2 = branch._res_powers_getter(warning=False, pot1=potentials1, pot2=potentials2)
            s_max = branch.parameters._max_power
            violated = None
            if s_max is not None:
                violated = max(abs(sum(powers1)), abs(sum(powers2))) > s_max
            phases = sorted(set(branch.phases1) | set(branch.phases2))
            for phase in phases:
                if phase in branch.phases1:
                    idx1 = branch.phases1.index(phase)
                    i1, s1, v1 = currents1[idx1], powers1[idx1], potentials1[idx1]
                else:
                    i1, s1, v1 = None, None, None
                if phase in branch.phases2:
                    idx2 = branch.phases2.index(phase)
                    i2, s2, v2 = currents2[idx2], powers2[idx2], potentials2[idx2]
                else:
                    i2, s2, v2 = None, None, None
                res_dict["transformer_id"].append(branch.id)
                res_dict["phase"].append(phase)
                res_dict["current1"].append(i1)
                res_dict["current2"].append(i2)
                res_dict["power1"].append(s1)
                res_dict["power2"].append(s2)
                res_dict["potential1"].append(v1)
                res_dict["potential2"].append(v2)
                res_dict["max_power"].append(s_max)
                res_dict["violated"].append(violated)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["transformer_id", "phase"])

    @property
    def res_lines(self) -> pd.DataFrame:
        """The load flow results of the network lines.

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
            "max_current": [],
            "violated": [],
        }
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for branch in self.branches.values():
            if not isinstance(branch, Line):
                continue
            potentials = branch._res_potentials_getter(warning=False)
            currents = branch._res_currents_getter(warning=False)
            powers = branch._res_powers_getter(warning=False, pot1=potentials[0], pot2=potentials[1])
            series_losses = branch._res_series_power_losses_getter(warning=False)
            series_currents = branch._res_series_currents_getter(warning=False)
            i_max = branch.parameters._max_current
            for i1, i2, s1, s2, v1, v2, s_series, i_series, phase in zip(
                *currents, *powers, *potentials, series_losses, series_currents, branch.phases, strict=True
            ):
                violated = None if i_max is None else max(abs(i1), abs(i2)) > i_max
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
                res_dict["max_current"].append(i_max)
                res_dict["violated"].append(violated)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["line_id", "phase"])

    @property
    def res_switches(self) -> pd.DataFrame:
        """The load flow results of the network switches.

        This is similar to the :attr:`res_branches` property but only apply to switches.

        The results are returned as a dataframe with the following index:
            - `switch_id`: The id of the switch.
            - `phase`: The phase of the switch (in ``{'a', 'b', 'c', 'n'}``).
        and the following columns:
            - `current1`: The complex current of the switch (in Amps) for the given phase at the
                first bus.
            - `current2`: The complex current of the switch (in Amps) for the given phase at the
                second bus.
            - `power1`: The complex power of the switch (in VoltAmps) for the given phase at the
                first bus.
            - `power2`: The complex power of the switch (in VoltAmps) for the given phase at the
                second bus.
            - `potential1`: The complex potential of the first bus (in Volts) for the given phase.
            - `potential2`: The complex potential of the second bus (in Volts) for the given phase.
        """
        self._warn_invalid_results()
        res_dict = {
            "switch_id": [],
            "phase": [],
            "current1": [],
            "current2": [],
            "power1": [],
            "power2": [],
            "potential1": [],
            "potential2": [],
        }
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for branch in self.branches.values():
            if not isinstance(branch, Switch):
                continue
            potentials = branch._res_potentials_getter(warning=False)
            currents = branch._res_currents_getter(warning=False)
            powers = branch._res_powers_getter(warning=False, pot1=potentials[0], pot2=potentials[1])
            for i1, i2, s1, s2, v1, v2, phase in zip(*currents, *powers, *potentials, branch.phases, strict=True):
                res_dict["switch_id"].append(branch.id)
                res_dict["phase"].append(phase)
                res_dict["current1"].append(i1)
                res_dict["current2"].append(i2)
                res_dict["power1"].append(s1)
                res_dict["power2"].append(s2)
                res_dict["potential1"].append(v1)
                res_dict["potential2"].append(v2)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["switch_id", "phase"])

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
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for load_id, load in self.loads.items():
            currents = load._res_currents_getter(warning=False)
            powers = load._res_powers_getter(warning=False)
            potentials = load._res_potentials_getter(warning=False)
            for i, s, v, phase in zip(currents, powers, potentials, load.phases, strict=True):
                res_dict["load_id"].append(load_id)
                res_dict["phase"].append(phase)
                res_dict["current"].append(i)
                res_dict["power"].append(s)
                res_dict["potential"].append(v)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["load_id", "phase"])

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
        dtypes = {c: _DTYPES[c] for c in voltages_dict} | {"phase": VoltagePhaseDtype}
        for load_id, load in self.loads.items():
            for voltage, phase in zip(load._res_voltages_getter(warning=False), load.voltage_phases, strict=True):
                voltages_dict["load_id"].append(load_id)
                voltages_dict["phase"].append(phase)
                voltages_dict["voltage"].append(voltage)
        return pd.DataFrame(voltages_dict).astype(dtypes).set_index(["load_id", "phase"])

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
        dtypes = {c: _DTYPES[c] for c in loads_dict} | {"phase": VoltagePhaseDtype}
        for load_id, load in self.loads.items():
            if not (isinstance(load, PowerLoad) and load.is_flexible):
                continue
            for power, phase in zip(load._res_flexible_powers_getter(warning=False), load.voltage_phases, strict=True):
                loads_dict["load_id"].append(load_id)
                loads_dict["phase"].append(phase)
                loads_dict["power"].append(power)
        return pd.DataFrame(loads_dict).astype(dtypes).set_index(["load_id", "phase"])

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
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for source_id, source in self.sources.items():
            currents = source._res_currents_getter(warning=False)
            powers = source._res_powers_getter(warning=False)
            potentials = source._res_potentials_getter(warning=False)
            for i, s, v, phase in zip(currents, powers, potentials, source.phases, strict=True):
                res_dict["source_id"].append(source_id)
                res_dict["phase"].append(phase)
                res_dict["current"].append(i)
                res_dict["power"].append(s)
                res_dict["potential"].append(v)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["source_id", "phase"])

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
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for ground in self.grounds.values():
            potential = ground._res_potential_getter(warning=False)
            res_dict["ground_id"].append(ground.id)
            res_dict["potential"].append(potential)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["ground_id"])

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
        dtypes = {c: _DTYPES[c] for c in res_dict}
        for p_ref in self.potential_refs.values():
            current = p_ref._res_current_getter(warning=False)
            res_dict["potential_ref_id"].append(p_ref.id)
            res_dict["current"].append(current)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["potential_ref_id"])

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
        elif isinstance(element, Ground):
            self.grounds[element.id] = element
        elif isinstance(element, PotentialRef):
            self.potential_refs[element.id] = element
        else:
            msg = f"Unknown element {element} can not be added to the network."
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
        if isinstance(element, Bus | AbstractBranch):
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
        cy_elements = []
        self._elements = []
        for bus in self.buses.values():
            cy_elements.append(bus._cy_element)
            self._elements.append(bus)
        for line in self.branches.values():
            cy_elements.append(line._cy_element)
            self._elements.append(line)
        for load in self.loads.values():
            cy_elements.append(load._cy_element)
            self._elements.append(load)
        for ground in self.grounds.values():
            cy_elements.append(ground._cy_element)
            self._elements.append(ground)
        for p_ref in self.potential_refs.values():
            cy_elements.append(p_ref._cy_element)
            self._elements.append(p_ref)
        for source in self.sources.values():
            cy_elements.append(source._cy_element)
            self._elements.append(source)
        self._propagate_potentials()
        self._cy_electrical_network = CyElectricalNetwork(elements=np.array(cy_elements), nb_elements=len(cy_elements))

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

        if not elements:
            msg = "Cannot create a network without elements."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.EMPTY_NETWORK)

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

    def _reset_inputs(self) -> None:
        """Reset the input vector used for the first step of the newton algorithm to its initial value."""
        if self._solver is not None:
            self._solver.reset_inputs()

    def _propagate_potentials(self) -> None:
        """Set the bus potentials that have not been initialized yet."""
        uninitialized = False
        for bus in self.buses.values():
            if not bus._initialized:
                uninitialized = True

        if uninitialized:
            max_voltages = 0.0
            voltage_source = None
            potentials = None
            for source in self.sources.values():
                # if there are multiple voltage sources, start from the higher one
                source_voltages = source.voltages.m_as("V")
                if np.average(np.abs(source_voltages)) > max_voltages:
                    max_voltages = np.average(np.abs(source_voltages))
                    voltage_source = source
                    if "n" in source.phases:
                        # Assume Vn = 0
                        potentials = np.append(source_voltages, 0.0)
                    elif len(source.phases) == 2:
                        # Assume V1 + V2 = 0
                        u = source_voltages[0]
                        potentials = np.array([u / 2, -u / 2])
                    else:
                        assert len(source.phases) == 3
                        # Assume Va + Vb + Vc = 0
                        u_ab = source_voltages[0]
                        u_bc = source_voltages[1]
                        v_b = (u_bc - u_ab) / 3
                        v_c = v_b - u_bc
                        v_a = v_b + u_ab
                        potentials = np.array([v_a, v_b, v_c, 0.0])

            elements = [(voltage_source, potentials)]
            visited = set()
            while elements:
                element, potentials = elements.pop(-1)
                visited.add(element)
                if isinstance(element, Bus) and not element._initialized:
                    bus_n = element._n
                    element.potentials = potentials[0:bus_n]
                    element._initialized_by_the_user = False  # only used for serialization
                for e in element._connected_elements:
                    if e not in visited and isinstance(e, AbstractBranch | Bus):
                        if isinstance(element, Transformer):
                            k = element.parameters._ulv / element.parameters._uhv
                            phase_displacement = element.parameters.phase_displacement
                            if phase_displacement is None:
                                phase_displacement = 0
                            elements.append((e, potentials * k * np.exp(phase_displacement * -1j * np.pi / 6.0)))
                        else:
                            elements.append((e, potentials))

    @staticmethod
    def _check_ref(elements: Iterable[Element]) -> None:
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
        buses, branches, loads, sources, grounds, p_refs = network_from_dict(data)
        return cls(
            buses=buses,
            branches=branches,
            loads=loads,
            sources=sources,
            grounds=grounds,
            potential_refs=p_refs,
        )

    def to_dict(self, *, _lf_only: bool = False) -> JsonDict:
        """Convert the electrical network to a dictionary.

        Args:
            _lf_only:
                Internal argument, please do not use.
        """
        return network_to_dict(self, _lf_only=_lf_only)

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
        buses, branches, loads, sources, grounds, potential_refs = network_from_dgs(path)
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
    def _get_catalogue(
        cls, name: str | re.Pattern[str] | None, load_point_name: str | re.Pattern[str] | None, raise_if_not_found: bool
    ) -> tuple[pd.DataFrame, str]:
        # Get the catalogue data
        catalogue_data = cls.catalogue_data()

        catalogue_dict = {
            "name": [],
            "nb_buses": [],
            "nb_branches": [],
            "nb_loads": [],
            "nb_sources": [],
            "nb_grounds": [],
            "nb_potential_refs": [],
            "load_points": [],
        }
        query_msg_list = []

        # Match on the name
        available_names = list(catalogue_data)
        match_names_list = available_names
        if name is not None:
            match_names_list = cls._filter_catalogue_str(name, strings=available_names)
            if isinstance(name, re.Pattern):
                name = name.pattern
            query_msg_list.append(f"{name=!r}")
        if raise_if_not_found:
            cls._assert_one_found(found_data=match_names_list, display_name="networks", query_info=f"{name=!r}")

        if load_point_name is not None:
            load_point_name_str = load_point_name if isinstance(load_point_name, str) else load_point_name.pattern
            query_msg_list.append(f"load_point_name={load_point_name_str!r}")

        for name in match_names_list:
            network_data = catalogue_data[name]

            # Match on the load point
            available_load_points: list[str] = network_data["load_points"]
            match_load_point_names_list = available_load_points
            if load_point_name is not None:
                match_load_point_names_list = cls._filter_catalogue_str(load_point_name, strings=available_load_points)
                if raise_if_not_found:
                    cls._assert_one_found(
                        found_data=match_load_point_names_list,
                        display_name=f"load points for network {name!r}",
                        query_info=query_msg_list[-1],
                    )
                elif not match_load_point_names_list:
                    continue

            catalogue_dict["name"].append(name)
            catalogue_dict["nb_buses"].append(network_data["nb_buses"])
            catalogue_dict["nb_branches"].append(network_data["nb_branches"])
            catalogue_dict["nb_loads"].append(network_data["nb_loads"])
            catalogue_dict["nb_sources"].append(network_data["nb_sources"])
            catalogue_dict["nb_grounds"].append(network_data["nb_grounds"])
            catalogue_dict["nb_potential_refs"].append(network_data["nb_potential_refs"])
            catalogue_dict["load_points"].append(match_load_point_names_list)

        return pd.DataFrame(catalogue_dict), ", ".join(query_msg_list)

    @classmethod
    def from_catalogue(cls, name: str | re.Pattern[str], load_point_name: str | re.Pattern[str]) -> Self:
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
        catalogue_data, _ = cls._get_catalogue(
            name=name,
            load_point_name=load_point_name,
            raise_if_not_found=True,
        )

        name = catalogue_data["name"].item()
        load_point_name = catalogue_data["load_points"].item()[0]

        # Get the data from the Json file
        path = cls.catalogue_path() / f"{name}_{load_point_name}.json"
        try:
            json_dict = json.loads(path.read_text())
        except FileNotFoundError:
            msg = f"The file {path} has not been found while it should exist. Please post an issue on GitHub."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_MISSING) from None

        return cls.from_dict(json_dict)

    @classmethod
    def get_catalogue(
        cls, name: str | re.Pattern[str] | None = None, load_point_name: str | re.Pattern[str] | None = None
    ) -> pd.DataFrame:
        """Read a network dictionary from the catalogue.

        Args:
            name:
                The name of the network to get from the catalogue. It can be a regular expression.

            load_point_name:
                The name of the load point to get. For each network, several load points may be available. It can be
                a regular expression.

        Returns:
            The dictionary containing the network data.
        """

        catalogue_data, _ = cls._get_catalogue(
            name=name,
            load_point_name=load_point_name,
            raise_if_not_found=False,
        )
        return (
            catalogue_data.reset_index(drop=True)
            .rename(
                columns={
                    "name": "Name",
                    "nb_buses": "Nb buses",
                    "nb_branches": "Nb branches",
                    "nb_loads": "Nb loads",
                    "nb_sources": "Nb sources",
                    "nb_grounds": "Nb grounds",
                    "nb_potential_refs": "Nb potential refs",
                    "load_points": "Available load points",
                }
            )
            .set_index("Name")
        )
