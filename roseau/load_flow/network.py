"""
This module defines the electrical network class.
"""

import json
import logging
import re
import textwrap
import warnings
from collections.abc import Generator, Iterable, Mapping
from importlib import resources
from itertools import chain
from math import nan
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeVar

import geopandas as gpd
import numpy as np
import pandas as pd
from typing_extensions import Self

from roseau.load_flow._solvers import AbstractSolver
from roseau.load_flow.constants import ALPHA, ALPHA2, CLOCK_PHASE_SHIFT, SQRT3
from roseau.load_flow.converters import _calculate_voltages, calculate_voltage_phases
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io import network_from_dgs, network_from_dict, network_to_dict
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    AbstractTerminal,
    Bus,
    CurrentLoad,
    Element,
    Ground,
    GroundConnection,
    ImpedanceLoad,
    Line,
    PotentialRef,
    PowerLoad,
    Switch,
    Transformer,
    VoltageSource,
)
from roseau.load_flow.typing import ComplexArray, CRSLike, Id, JsonDict, MapOrSeq, Solver, StrPath
from roseau.load_flow.utils import (
    DTYPES,
    CatalogueMixin,
    JsonMixin,
    LoadTypeDtype,
    SourceTypeDtype,
    VoltagePhaseDtype,
    count_repr,
    find_stack_level,
    optional_deps,
)
from roseau.load_flow_engine.cy_engine import CyElectricalNetwork

if TYPE_CHECKING:
    from networkx import Graph

logger = logging.getLogger(__name__)

_E = TypeVar("_E", bound=Element)
_AT = TypeVar("_AT", bound=AbstractTerminal)


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

        lines:
            The lines of the network. Either a list of lines or a dictionary of lines with their IDs
            as keys.

        transformers:
            The transformers of the network. Either a list of transformers or a dictionary of
            transformers with their IDs as keys.

        switches:
            The switches of the network. Either a list of switches or a dictionary of switches with
            their IDs as keys.

        loads:
            The loads of the network. Either a list of loads or a dictionary of loads with their IDs
            as keys. There are three types of loads: constant power, constant current, and constant
            impedance.

        sources:
            The sources of the network. Either a list of sources or a dictionary of sources with
            their IDs as keys. A network must have at least one source. Note that two sources cannot
            be connected with a switch.

        grounds:
            The grounds of the network. Either a list of grounds or a dictionary of grounds with
            their IDs as keys. LV networks typically have one ground element connected to the
            neutral of the main source bus (LV side of the MV/LV transformer). HV networks may have
            one or more grounds connected to the shunt components of their lines.

        potential_refs:
            The potential references of the network. Either a list of potential references or a
            dictionary of potential references with their IDs as keys. As the name suggests, this
            element defines the reference of potentials of the network. A potential reference per
            galvanically isolated section of the network is expected. A potential reference can be
            connected to a bus or to a ground.

        crs:
            An optional Coordinate Reference System to use with geo data frames. Can be anything
            accepted by geopandas and pyproj, such as an authority string or WKT string.

    Attributes:
        buses (dict[Id, roseau.load_flow.Bus]):
            Dictionary of buses of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<buses_frame>`.

        lines (dict[Id, roseau.load_flow.Line]):
            Dictionary of lines of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<lines_frame>`.

        transformers (dict[Id, roseau.load_flow.Transformer]):
            Dictionary of transformers of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<transformers_frame>`.

        switches (dict[Id, roseau.load_flow.Switch]):
            Dictionary of switches of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<switches_frame>`.

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
        *,
        buses: MapOrSeq[Bus],
        lines: MapOrSeq[Line],
        transformers: MapOrSeq[Transformer],
        switches: MapOrSeq[Switch],
        loads: MapOrSeq[AbstractLoad],
        sources: MapOrSeq[VoltageSource],
        grounds: MapOrSeq[Ground],
        potential_refs: MapOrSeq[PotentialRef],
        ground_connections: MapOrSeq[GroundConnection] = (),
        crs: CRSLike | None = None,
    ) -> None:
        self.buses: dict[Id, Bus] = self._elements_as_dict(buses, RoseauLoadFlowExceptionCode.BAD_BUS_ID)
        self.lines: dict[Id, Line] = self._elements_as_dict(lines, RoseauLoadFlowExceptionCode.BAD_LINE_ID)
        self.transformers: dict[Id, Transformer] = self._elements_as_dict(
            transformers, RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_ID
        )
        self.switches: dict[Id, Switch] = self._elements_as_dict(switches, RoseauLoadFlowExceptionCode.BAD_SWITCH_ID)
        # Use a union of all loads types to help autocompletion when typing `load.powers` for example
        self.loads: dict[Id, AbstractLoad | PowerLoad | CurrentLoad | ImpedanceLoad] = self._elements_as_dict(
            loads, RoseauLoadFlowExceptionCode.BAD_LOAD_ID
        )
        self.sources: dict[Id, VoltageSource] = self._elements_as_dict(
            sources, RoseauLoadFlowExceptionCode.BAD_SOURCE_ID
        )
        self.grounds: dict[Id, Ground] = self._elements_as_dict(grounds, RoseauLoadFlowExceptionCode.BAD_GROUND_ID)
        self.potential_refs: dict[Id, PotentialRef] = self._elements_as_dict(
            potential_refs, RoseauLoadFlowExceptionCode.BAD_POTENTIAL_REF_ID
        )
        self.ground_connections: dict[Id, GroundConnection] = self._elements_as_dict(
            ground_connections, RoseauLoadFlowExceptionCode.BAD_GROUND_CONNECTION_ID
        )

        self._elements: list[Element] = []
        self._has_loop = False
        self._has_floating_neutral = False
        self._check_validity(constructed=True)
        self._create_network()
        self._valid = True
        self._solver = AbstractSolver.from_dict(data={"name": self._DEFAULT_SOLVER, "params": {}}, network=self)
        self.crs: CRSLike | None = crs

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}:"
            f" {count_repr(self.buses, 'bus', 'buses')},"
            f" {count_repr(self.lines, 'line', 'lines')},"
            f" {count_repr(self.transformers, 'transformer', 'transformers')},"
            f" {count_repr(self.switches, 'switch', 'switches')},"
            f" {count_repr(self.loads, 'load')},"
            f" {count_repr(self.sources, 'source')},"
            f" {count_repr(self.grounds, 'ground')},"
            f" {count_repr(self.potential_refs, 'potential ref')},"
            f" {count_repr(self.ground_connections, 'ground connection')}"
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
                    msg = (
                        f"{typ.capitalize()} ID {element.id!r} does not match its key in the dictionary {element_id!r}."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg, code=error_code)
                elements_dict[element_id] = element
        else:
            for element in elements:
                if element.id in elements_dict:
                    msg = f"Duplicate {typ.lower()} ID {element.id!r} in the network."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg, code=error_code)
                elements_dict[element.id] = element
        return elements_dict

    @classmethod
    def from_element(cls, initial_bus: Bus, crs: CRSLike | None = None) -> Self:
        """Construct the network from only one element (bus) and add the others automatically.

        Args:
            initial_bus:
                Any bus of the network. The network is constructed from this bus and all the
                elements connected to it. This is usually the main source bus of the network.

        crs:
            An optional Coordinate Reference System to use with geo data frames. Can be anything
            accepted by geopandas and pyproj, such as an authority string or WKT string.

        Returns:
            The network constructed from the given bus and all the elements connected to it.
        """
        buses: list[Bus] = []
        lines: list[Line] = []
        transformers: list[Transformer] = []
        switches: list[Switch] = []
        loads: list[AbstractLoad] = []
        sources: list[VoltageSource] = []
        grounds: list[Ground] = []
        potential_refs: list[PotentialRef] = []
        ground_connections: list[GroundConnection] = []

        elements: list[Element] = [initial_bus]
        visited_elements: set[Element] = set()
        while elements:
            e = elements.pop(-1)
            visited_elements.add(e)
            if isinstance(e, Bus):
                buses.append(e)
            elif isinstance(e, Line):
                lines.append(e)
            elif isinstance(e, Transformer):
                transformers.append(e)
            elif isinstance(e, Switch):
                switches.append(e)
            elif isinstance(e, AbstractLoad):
                loads.append(e)
            elif isinstance(e, VoltageSource):
                sources.append(e)
            elif isinstance(e, Ground):
                grounds.append(e)
            elif isinstance(e, PotentialRef):
                potential_refs.append(e)
            elif isinstance(e, GroundConnection):
                ground_connections.append(e)
            for connected_element in e._connected_elements:
                if connected_element not in visited_elements and connected_element not in elements:
                    elements.append(connected_element)
        return cls(
            buses=buses,
            lines=lines,
            transformers=transformers,
            switches=switches,
            loads=loads,
            sources=sources,
            grounds=grounds,
            potential_refs=potential_refs,
            ground_connections=ground_connections,
            crs=crs,
        )

    #
    # Properties to access the data as dataframes
    #
    @property
    def buses_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`buses` of the network as a geo dataframe."""
        index = []
        data = {
            "phases": [],
            "nominal_voltage": [],
            "min_voltage_level": [],
            "max_voltage_level": [],
            "geometry": [],
        }
        for bus in self.buses.values():
            index.append(bus.id)
            data["phases"].append(bus.phases)
            data["nominal_voltage"].append(bus._nominal_voltage if bus._nominal_voltage is not None else nan)
            data["min_voltage_level"].append(bus._min_voltage_level if bus._min_voltage_level is not None else nan)
            data["max_voltage_level"].append(bus._max_voltage_level if bus._max_voltage_level is not None else nan)
            data["geometry"].append(bus.geometry)
        index = pd.Index(index, name="id")
        return gpd.GeoDataFrame(data=data, index=index, geometry="geometry", crs=self.crs)

    @property
    def lines_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`lines` of the network as a geo dataframe."""
        index = []
        data = {
            "phases": [],
            "bus1_id": [],
            "bus2_id": [],
            "parameters_id": [],
            "length": [],
            "max_loading": [],
            "geometry": [],
        }
        for line in self.lines.values():
            index.append(line.id)
            data["phases"].append(line.phases)
            data["bus1_id"].append(line.bus1.id)
            data["bus2_id"].append(line.bus2.id)
            data["parameters_id"].append(line.parameters.id)
            data["length"].append(line._length)
            data["max_loading"].append(line._max_loading)
            data["geometry"].append(line.geometry)
        index = pd.Index(index, name="id")
        return gpd.GeoDataFrame(data=data, index=index, geometry="geometry", crs=self.crs)

    @property
    def transformers_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`transformers` of the network as a geo dataframe."""
        index = []
        data = {
            "phases_hv": [],
            "phases_lv": [],
            "bus_hv_id": [],
            "bus_lv_id": [],
            "parameters_id": [],
            "tap": [],
            "max_loading": [],
            "geometry": [],
        }
        for transformer in self.transformers.values():
            index.append(transformer.id)
            data["phases_hv"].append(transformer.phases_hv)
            data["phases_lv"].append(transformer.phases_lv)
            data["bus_hv_id"].append(transformer.bus_hv.id)
            data["bus_lv_id"].append(transformer.bus_lv.id)
            data["parameters_id"].append(transformer.parameters.id)
            data["tap"].append(transformer._tap)
            data["max_loading"].append(transformer._max_loading)
            data["geometry"].append(transformer.geometry)
        index = pd.Index(index, name="id")
        return gpd.GeoDataFrame(data=data, index=index, geometry="geometry", crs=self.crs)

    @property
    def switches_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`switches` of the network as a geo dataframe."""
        index = []
        data = {"phases": [], "bus1_id": [], "bus2_id": [], "geometry": []}
        for switch in self.switches.values():
            index.append(switch.id)
            data["phases"].append(switch.phases)
            data["bus1_id"].append(switch.bus1.id)
            data["bus2_id"].append(switch.bus2.id)
            data["geometry"].append(switch.geometry)
        index = pd.Index(index, name="id")
        return gpd.GeoDataFrame(data=data, index=index, geometry="geometry", crs=self.crs)

    @property
    def loads_frame(self) -> pd.DataFrame:
        """The :attr:`loads` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[(load.id, load.type, load.phases, load.bus.id, load.is_flexible) for load in self.loads.values()],
            columns=["id", "type", "phases", "bus_id", "flexible"],
            index="id",
        )

    @property
    def sources_frame(self) -> pd.DataFrame:
        """The :attr:`sources` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[(source.id, source.type, source.phases, source.bus.id) for source in self.sources.values()],
            columns=["id", "type", "phases", "bus_id"],
            index="id",
        )

    @property
    def grounds_frame(self) -> pd.DataFrame:
        """The :attr:`grounds` of the network as a dataframe.

        See :attr:`ground_connections_frame` for the connections to the ground.
        """
        return pd.DataFrame.from_records(data=[(ground.id,) for ground in self.grounds.values()], columns=["id"])

    @property
    def potential_refs_frame(self) -> pd.DataFrame:
        """The :attr:`potential references <potential_refs>` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[
                (pref.id, pref.phases, pref.element.id, type(pref.element).__name__.lower())
                for pref in self.potential_refs.values()
            ],
            columns=["id", "phases", "element_id", "element_type"],
            index="id",
        )

    @property
    def ground_connections_frame(self) -> pd.DataFrame:
        """The :attr:`ground connections <ground_connections>` of the network as a dataframe."""
        return pd.DataFrame.from_records(
            data=[
                (gc.id, gc.ground.id, gc.element.id, gc.element.element_type, gc.phase, gc.side, gc._impedance)
                for gc in self.ground_connections.values()
            ],
            columns=["id", "ground_id", "element_id", "element_type", "phase", "side", "impedance"],
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
        """Clusters of buses connected by lines and switches.

        Each cluster is a set of bus IDs.

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
        nx = optional_deps.networkx
        graph = nx.Graph()
        for bus in self.buses.values():
            graph.add_node(bus.id, geom=bus.geometry)
        for line in self.lines.values():
            if (ampacities := line.parameters._ampacities) is not None:
                ampacities = ampacities.tolist()
            graph.add_edge(
                line.bus1.id,
                line.bus2.id,
                id=line.id,
                type="line",
                phases=line.phases,
                parameters_id=line.parameters.id,
                length=line._length,
                max_loading=line._max_loading,
                ampacities=ampacities,
                geom=line.geometry,
            )
        for transformer in self.transformers.values():
            graph.add_edge(
                transformer.bus1.id,
                transformer.bus2.id,
                id=transformer.id,
                type="transformer",
                phases1=transformer.phases1,
                phases2=transformer.phases2,
                parameters_id=transformer.parameters.id,
                max_loading=transformer._max_loading,
                sn=transformer.parameters._sn,
                geom=transformer.geometry,
            )
        for switch in self.switches.values():
            graph.add_edge(
                switch.bus1.id, switch.bus2.id, id=switch.id, type="switch", phases=switch.phases, geom=switch.geometry
            )
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

        You need to activate the license before calling this method. You may set the environment
        variable ``ROSEAU_LOAD_FLOW_LICENSE_KEY`` to your license key and it will be picked
        automatically when calling this method. See the :ref:`license` page for more information.

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

                - ``newton``: The classical *Newton-Raphson* method.
                - ``newton_goldstein``: The *Newton-Raphson* method with the *Goldstein and Price*
                  linear search algorithm. It generally has better convergence properties than the
                  classical Newton-Raphson method. This is the default.
                - ``backward_forward``: the *Backward-Forward Sweep* method. It usually executes
                  faster than the other approaches but may exhibit weaker convergence properties. It
                  does not support meshed networks or floating neutrals.

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

        iterations, residual = self._solver.solve_load_flow(max_iterations=max_iterations, tolerance=tolerance)

        self._no_results = False

        # Lazily update the results of the elements
        for element in self._elements:
            element._fetch_results = True
            element._no_results = False

        # The results are now valid
        self._results_valid = True

        return iterations, residual

    #
    # Properties to access the load flow results as dataframes
    #
    def _check_valid_results(self) -> None:
        """Check that the results exist and warn if they are invalid."""
        if self._no_results:
            msg = "The load flow results are not available because the load flow has not been run yet."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN)

        if not self._results_valid:
            warnings.warn(
                message=(
                    "The results of this network may be outdated. Please re-run a load flow to "
                    "ensure the validity of results."
                ),
                category=UserWarning,
                stacklevel=find_stack_level(),
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
        self._check_valid_results()
        res_dict = {"bus_id": [], "phase": [], "potential": []}
        dtypes = {c: DTYPES[c] for c in res_dict}
        for bus_id, bus in self.buses.items():
            for potential, phase in zip(bus._res_potentials_getter(warning=False), bus.phases, strict=True):
                res_dict["bus_id"].append(bus_id)
                res_dict["phase"].append(phase)
                res_dict["potential"].append(potential)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["bus_id", "phase"])

    @property
    def res_lines(self) -> pd.DataFrame:
        """The load flow results of the network lines.

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
            - `potential1`: The complex potential (in Volts) for the given phase of the first bus.
            - `potential2`: The complex potential (in Volts) for the given phase of the second bus.
            - `series_losses`: The complex losses in the series and mutual impedances of the line
              (in VoltAmps) for the given phase.
            - `series_current`: The complex current in the series impedance of the line (in Amps)
                for the given phase.
            - `violated`: True, if the line loading exceeds the maximum loading for the given phase.
            - `loading`: The loading of the line (unitless) for the given phase.
            - `max_loading`: The maximal loading of the line (unitless) for the given phase.
            - `ampacity`: The ampacity of the line (in Amps) for the given phase.

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
        self._check_valid_results()
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
            "violated": [],
            "loading": [],
            # Non results
            "max_loading": [],
            "ampacity": [],
        }
        dtypes = {c: DTYPES[c] for c in res_dict}
        for line in self.lines.values():
            currents1, currents2 = line._res_currents_getter(warning=False)
            potentials1, potentials2 = line._res_potentials_getter(warning=False)
            du_line, series_currents = line._res_series_values_getter(warning=False)
            powers1 = potentials1 * currents1.conj()
            powers2 = potentials2 * currents2.conj()
            series_losses = du_line * series_currents.conj()
            ampacity_array = line.parameters._ampacities
            max_loading = line._max_loading
            if ampacity_array is None:
                ampacity_array = loading_array = violated_array = [None for _ in line.phases]
            else:
                loading_array = np.maximum(abs(currents1), abs(currents2)) / ampacity_array
                violated_array = loading_array > max_loading
            for i1, i2, s1, s2, v1, v2, s_series, i_series, phase, ampacity, loading, violated in zip(
                currents1,
                currents2,
                powers1,
                powers2,
                potentials1,
                potentials2,
                series_losses,
                series_currents,
                line.phases,
                ampacity_array,
                loading_array,
                violated_array,
                strict=True,
            ):
                res_dict["line_id"].append(line.id)
                res_dict["phase"].append(phase)
                res_dict["current1"].append(i1)
                res_dict["current2"].append(i2)
                res_dict["power1"].append(s1)
                res_dict["power2"].append(s2)
                res_dict["potential1"].append(v1)
                res_dict["potential2"].append(v2)
                res_dict["series_losses"].append(s_series)
                res_dict["series_current"].append(i_series)
                res_dict["violated"].append(violated)
                res_dict["loading"].append(loading)
                # Non results
                res_dict["max_loading"].append(max_loading)
                res_dict["ampacity"].append(ampacity)

        return pd.DataFrame(res_dict).astype(dtypes).set_index(["line_id", "phase"])

    @property
    def res_transformers(self) -> pd.DataFrame:
        """The load flow results of the network transformers.

        The results are returned as a dataframe with the following index:
            - `transformer_id`: The id of the transformer.
            - `phase`: The phase of the transformer (in ``{'a', 'b', 'c', 'n'}``).

        and the following columns:
            - `current_hv`: The complex current on the HV side of the transformer (in Amps) for the
              given phase.
            - `current_lv`: The complex current on the LV side of the transformer (in Amps) for the
              given phase.
            - `power_hv`: The complex power on the HV side of the transformer (in VoltAmps) for the
              given phase.
            - `power_lv`: The complex power on the LV side of the transformer (in VoltAmps) for the
              given phase.
            - `potential_hv`: The complex potential on the HV side of the transformer (in Volts) for
              the given phase.
            - `potential_lv`: The complex potential on the LV side of the transformer (in Volts) for
              the given phase.
            - `max_loading`: The maximal loading (unitless) of the transformer.

        Note that values for missing phases are set to ``nan``. For example, a "Dyn" transformer has
        the phases "abc" on the HV side and "abcn" on the LV side, so the HV side values for current,
        power, and potential for phase "n" will be ``nan``.
        """
        self._check_valid_results()
        res_dict = {
            "transformer_id": [],
            "phase": [],
            "current_hv": [],
            "current_lv": [],
            "power_hv": [],
            "power_lv": [],
            "potential_hv": [],
            "potential_lv": [],
            "violated": [],
            "loading": [],
            # Non results
            "max_loading": [],
            "sn": [],
        }
        dtypes = {c: DTYPES[c] for c in res_dict}
        for transformer in self.transformers.values():
            currents_hv, currents_lv = transformer._res_currents_getter(warning=False)
            potentials_hv, potentials_lv = transformer._res_potentials_getter(warning=False)
            powers_hv = potentials_hv * currents_hv.conj()
            powers_lv = potentials_lv * currents_lv.conj()
            sn = transformer.parameters._sn
            max_loading = transformer._max_loading
            loading = max(abs(powers_hv.sum()), abs(powers_lv.sum())) / sn
            violated = loading > max_loading
            for phase in transformer._all_phases:
                if phase in transformer.phases_hv:
                    idx_hv = transformer.phases_hv.index(phase)
                    i_hv, s_hv, v_hv = currents_hv[idx_hv], powers_hv[idx_hv], potentials_hv[idx_hv]
                else:
                    i_hv, s_hv, v_hv = None, None, None
                if phase in transformer.phases_lv:
                    idx_lv = transformer.phases_lv.index(phase)
                    i_lv, s_lv, v_lv = currents_lv[idx_lv], powers_lv[idx_lv], potentials_lv[idx_lv]
                else:
                    i_lv, s_lv, v_lv = None, None, None
                res_dict["transformer_id"].append(transformer.id)
                res_dict["phase"].append(phase)
                res_dict["current_hv"].append(i_hv)
                res_dict["current_lv"].append(i_lv)
                res_dict["power_hv"].append(s_hv)
                res_dict["power_lv"].append(s_lv)
                res_dict["potential_hv"].append(v_hv)
                res_dict["potential_lv"].append(v_lv)
                res_dict["violated"].append(violated)
                res_dict["loading"].append(loading)
                # Non results
                res_dict["max_loading"].append(max_loading)
                res_dict["sn"].append(sn)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["transformer_id", "phase"])

    @property
    def res_switches(self) -> pd.DataFrame:
        """The load flow results of the network switches.

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
        self._check_valid_results()
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
        dtypes = {c: DTYPES[c] for c in res_dict}
        for switch in self.switches.values():
            currents1, currents2 = switch._res_currents_getter(warning=False)
            potentials1, potentials2 = switch._res_potentials_getter(warning=False)
            powers1 = potentials1 * currents1.conj()
            powers2 = potentials2 * currents2.conj()
            for i1, i2, s1, s2, v1, v2, phase in zip(
                currents1, currents2, powers1, powers2, potentials1, potentials2, switch.phases, strict=True
            ):
                res_dict["switch_id"].append(switch.id)
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
            - `type`: The type of the load, can be ``{'power', 'current', 'impedance'}``.
            - `current`: The complex current of the load (in Amps) for the given phase.
            - `power`: The complex power of the load (in VoltAmps) for the given phase.
            - `potential`: The complex potential of the load (in Volts) for the given phase.
        """
        self._check_valid_results()
        res_dict = {"load_id": [], "phase": [], "type": [], "current": [], "power": [], "potential": []}
        dtypes = {c: DTYPES[c] for c in res_dict} | {"type": LoadTypeDtype}
        for load_id, load in self.loads.items():
            currents = load._res_currents_getter(warning=False)
            potentials = load._res_potentials_getter(warning=False)
            powers = potentials * currents.conj()
            for i, s, v, phase in zip(currents, powers, potentials, load.phases, strict=True):
                res_dict["load_id"].append(load_id)
                res_dict["phase"].append(phase)
                res_dict["type"].append(load.type)
                res_dict["current"].append(i)
                res_dict["power"].append(s)
                res_dict["potential"].append(v)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["load_id", "phase"])

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
        self._check_valid_results()
        loads_dict = {"load_id": [], "phase": [], "flexible_power": []}
        dtypes = {c: DTYPES[c] for c in loads_dict} | {"phase": VoltagePhaseDtype}
        for load_id, load in self.loads.items():
            if not (isinstance(load, PowerLoad) and load.is_flexible):
                continue
            for flexible_power, phase in zip(
                load._res_flexible_powers_getter(warning=False), load.voltage_phases, strict=True
            ):
                loads_dict["load_id"].append(load_id)
                loads_dict["phase"].append(phase)
                loads_dict["flexible_power"].append(flexible_power)
        return pd.DataFrame(loads_dict).astype(dtypes).set_index(["load_id", "phase"])

    @property
    def res_sources(self) -> pd.DataFrame:
        """The load flow results of the network sources.

        The results are returned as a dataframe with the following index:
            - `source_id`: The id of the source.
            - `phase`: The phase of the source (in ``{'a', 'b', 'c', 'n'}``).

        and the following columns:
            - `type`: The type of the source, can be ``{'voltage'}``.
            - `current`: The complex current of the source (in Amps) for the given phase.
            - `power`: The complex power of the source (in VoltAmps) for the given phase.
            - `potential`: The complex potential of the source (in Volts) for the given phase.
        """
        self._check_valid_results()
        res_dict = {"source_id": [], "type": [], "phase": [], "current": [], "power": [], "potential": []}
        dtypes = {c: DTYPES[c] for c in res_dict} | {"type": SourceTypeDtype}
        for source_id, source in self.sources.items():
            currents = source._res_currents_getter(warning=False)
            potentials = source._res_potentials_getter(warning=False)
            powers = potentials * currents.conj()
            for i, s, v, phase in zip(currents, powers, potentials, source.phases, strict=True):
                res_dict["source_id"].append(source_id)
                res_dict["phase"].append(phase)
                res_dict["type"].append(source.type)
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
        self._check_valid_results()
        res_dict = {"ground_id": [], "potential": []}
        dtypes = {c: DTYPES[c] for c in res_dict}
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
        self._check_valid_results()
        res_dict = {"potential_ref_id": [], "current": []}
        dtypes = {c: DTYPES[c] for c in res_dict}
        for p_ref in self.potential_refs.values():
            current = p_ref._res_current_getter(warning=False)
            res_dict["potential_ref_id"].append(p_ref.id)
            res_dict["current"].append(current)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["potential_ref_id"])

    @property
    def res_ground_connections(self) -> pd.DataFrame:
        """The load flow results of the network ground connections.

        The results are returned as a dataframe with the following index:
            - `connection_id`: The id of the ground connection.
        and the following columns:
            - `current`: The complex current passing through connection to the ground (in Amps).
        """
        self._check_valid_results()
        res_dict = {"connection_id": [], "current": []}
        dtypes = {c: DTYPES[c] for c in res_dict}
        for gc in self.ground_connections.values():
            current = gc._res_current_getter(warning=False)
            res_dict["connection_id"].append(gc.id)
            res_dict["current"].append(current)
        return pd.DataFrame(res_dict).astype(dtypes).set_index(["connection_id"])

    # Voltages results
    def _iter_terminal_res_voltages(
        self, terminals: Mapping[Id, _AT], voltage_type: Literal["pp", "pn", "auto"]
    ) -> Generator[tuple[_AT, ComplexArray, list[str]]]:
        if voltage_type == "auto":
            for e in terminals.values():
                yield e, e._res_voltages_getter(warning=False), e.voltage_phases
        elif voltage_type == "pp":
            for e in terminals.values():
                phases = e.phases.removesuffix("n")
                n = len(phases)
                if n == 1:
                    continue
                voltage_phases = calculate_voltage_phases(phases)
                potentials = e._res_potentials_getter(warning=False)
                voltages = _calculate_voltages(potentials[:n], phases)
                yield e, voltages, voltage_phases
        elif voltage_type == "pn":
            for e in terminals.values():
                if "n" not in e.phases:
                    continue
                yield e, e._res_voltages_getter(warning=False), e.voltage_phases

    def _get_res_buses_voltages(self, voltage_type: Literal["pp", "pn", "auto"]) -> pd.DataFrame:
        self._check_valid_results()
        voltages_dict = {
            "bus_id": [],
            "phase": [],
            "voltage": [],
            "violated": [],
            "voltage_level": [],
            # Non results
            "min_voltage_level": [],
            "max_voltage_level": [],
            "nominal_voltage": [],
        }
        dtypes = {c: DTYPES[c] for c in voltages_dict} | {"phase": VoltagePhaseDtype}
        for bus, voltages, phases in self._iter_terminal_res_voltages(self.buses, voltage_type):
            nominal_voltage = bus._nominal_voltage
            min_voltage_level = bus._min_voltage_level
            max_voltage_level = bus._max_voltage_level
            nominal_voltage_defined = nominal_voltage is not None
            voltage_limits_set = nominal_voltage_defined and (
                min_voltage_level is not None or max_voltage_level is not None
            )
            if nominal_voltage is None:
                nominal_voltage = nan
            if min_voltage_level is None:
                min_voltage_level = nan
            if max_voltage_level is None:
                max_voltage_level = nan
            for voltage, phase in zip(voltages, phases, strict=True):
                voltage_abs = abs(voltage)
                if nominal_voltage_defined:
                    if "n" in phase:
                        voltage_level = SQRT3 * voltage_abs / nominal_voltage
                    else:
                        voltage_level = voltage_abs / nominal_voltage
                    violated = (
                        (voltage_level < min_voltage_level or voltage_level > max_voltage_level)
                        if voltage_limits_set
                        else None
                    )
                else:
                    voltage_level = nan
                    violated = None
                voltages_dict["bus_id"].append(bus.id)
                voltages_dict["phase"].append(phase)
                voltages_dict["voltage"].append(voltage)
                voltages_dict["violated"].append(violated)
                voltages_dict["voltage_level"].append(voltage_level)
                # Non results
                voltages_dict["min_voltage_level"].append(min_voltage_level)
                voltages_dict["max_voltage_level"].append(max_voltage_level)
                voltages_dict["nominal_voltage"].append(nominal_voltage)

        return pd.DataFrame(voltages_dict).astype(dtypes).set_index(["bus_id", "phase"])

    @property
    def res_buses_voltages(self) -> pd.DataFrame:
        """The load flow results of the complex voltages of the buses (V).

        The voltage is phase-to-neutral if the bus has a neutral and phase-to-phase otherwise. The
        dataframe has a ``phase`` index that will contain values like ``'an'`` for phase-to-neutral
        voltages and values like ``'ab'`` for phase-to-phase voltages.

        The results are returned as a dataframe with the following index:
            - `bus_id`: The id of the bus.
            - `phase`: The phase of the bus (in ``{'an', 'bn', 'cn', 'ab', 'bc', 'ca'}``).

        and the following columns:
            - `voltage`: The complex voltage of the bus (in Volts) for the given phase.
            - `violated`: `True` if a voltage limit is not respected.
            - `voltage_level`: The voltage level of the bus.
            - `min_voltage_level`: The minimal voltage level of the bus.
            - `max_voltage_level`: The maximal voltage level of the bus.
            - `nominal_voltage`: The nominal voltage of the bus (in Volts).
        """
        return self._get_res_buses_voltages(voltage_type="auto")

    @property
    def res_buses_voltages_pp(self) -> pd.DataFrame:
        """The load flow results of the complex phase-to-phase voltages of the buses (V).

        Only buses with two or more phases are considered.

        The results are returned as a dataframe with the following index:
            - `bus_id`: The id of the bus.
            - `phase`: The phase of the bus (in ``{'ab', 'bc', 'ca'}``).

        and the following columns:
            - `voltage`: The complex voltage of the bus (in Volts) for the given phase.
            - `violated`: `True` if a voltage limit is not respected.
            - `voltage_level`: The voltage level of the bus.
            - `min_voltage_level`: The minimal voltage level of the bus.
            - `max_voltage_level`: The maximal voltage level of the bus.
            - `nominal_voltage`: The nominal voltage of the bus (in Volts).
        """
        return self._get_res_buses_voltages(voltage_type="pp")

    @property
    def res_buses_voltages_pn(self) -> pd.DataFrame:
        """The load flow results of the complex phase-to-neutral voltages of the buses (V).

        Only buses with a neutral are considered.

        The results are returned as a dataframe with the following index:
            - `bus_id`: The id of the bus.
            - `phase`: The phase of the bus (in ``{'an', 'bn', 'cn'}``).

        and the following columns:
            - `voltage`: The complex voltage of the bus (in Volts) for the given phase.
            - `violated`: `True` if a voltage limit is not respected.
            - `voltage_level`: The voltage level of the bus.
            - `min_voltage_level`: The minimal voltage level of the bus.
            - `max_voltage_level`: The maximal voltage level of the bus.
            - `nominal_voltage`: The nominal voltage of the bus (in Volts).
        """
        return self._get_res_buses_voltages(voltage_type="pn")

    def _get_res_loads_voltages(self, voltage_type: Literal["pp", "pn", "auto"]) -> pd.DataFrame:
        self._check_valid_results()
        voltages_dict = {"load_id": [], "phase": [], "type": [], "voltage": []}
        dtypes = {c: DTYPES[c] for c in voltages_dict} | {"phase": VoltagePhaseDtype, "type": LoadTypeDtype}
        for load, voltages, phases in self._iter_terminal_res_voltages(self.loads, voltage_type):
            for voltage, phase in zip(voltages, phases, strict=True):
                voltages_dict["load_id"].append(load.id)
                voltages_dict["phase"].append(phase)
                voltages_dict["type"].append(load.type)
                voltages_dict["voltage"].append(voltage)
        return pd.DataFrame(voltages_dict).astype(dtypes).set_index(["load_id", "phase"])

    @property
    def res_loads_voltages(self) -> pd.DataFrame:
        """The load flow results of the complex voltages of the loads (V).

        The results are returned as a dataframe with the following index:
            - `load_id`: The id of the load.
            - `phase`: The phase of the load (in ``{'an', 'bn', 'cn'}`` for wye loads and in
                ``{'ab', 'bc', 'ca'}`` for delta loads.).

        and the following columns:
            - `type`: The type of the load, can be ``{'power', 'current', 'impedance'}``.s
            - `voltage`: The complex voltage of the load (in Volts) for the given *phase*.
        """
        return self._get_res_loads_voltages(voltage_type="auto")

    @property
    def res_loads_voltages_pp(self) -> pd.DataFrame:
        """The load flow results of the complex phase-to-phase voltages of the loads (V).

        Only loads with two or more phases are considered.

        The results are returned as a dataframe with the following index:
            - `load_id`: The id of the load.
            - `phase`: The phase of the load (in ``{'ab', 'bc', 'ca'}``).

        and the following columns:
            - `type`: The type of the load, can be ``{'power', 'current', 'impedance'}``.s
            - `voltage`: The complex voltage of the load (in Volts) for the given *phase*.
        """
        return self._get_res_loads_voltages(voltage_type="pp")

    @property
    def res_loads_voltages_pn(self) -> pd.DataFrame:
        """The load flow results of the complex phase-to-phase voltages of the loads (V).

        Only loads with a neutral are considered.

        The results are returned as a dataframe with the following index:
            - `load_id`: The id of the load.
            - `phase`: The phase of the load (in ``{'an', 'bn', 'cn'}``).

        and the following columns:
            - `type`: The type of the load, can be ``{'power', 'current', 'impedance'}``.s
            - `voltage`: The complex voltage of the load (in Volts) for the given *phase*.
        """
        return self._get_res_loads_voltages(voltage_type="pn")

    def _get_res_sources_voltages(self, voltage_type: Literal["pp", "pn", "auto"]) -> pd.DataFrame:
        self._check_valid_results()
        voltages_dict = {"source_id": [], "phase": [], "type": [], "voltage": []}
        dtypes = {c: DTYPES[c] for c in voltages_dict} | {"phase": VoltagePhaseDtype, "type": SourceTypeDtype}
        for source, voltages, phases in self._iter_terminal_res_voltages(self.sources, voltage_type):
            for voltage, phase in zip(voltages, phases, strict=True):
                voltages_dict["source_id"].append(source.id)
                voltages_dict["phase"].append(phase)
                voltages_dict["type"].append(source.type)
                voltages_dict["voltage"].append(voltage)
        return pd.DataFrame(voltages_dict).astype(dtypes).set_index(["source_id", "phase"])

    @property
    def res_sources_voltages(self) -> pd.DataFrame:
        """The load flow results of the complex voltages of the sources (V).

        The results are returned as a dataframe with the following index:
            - `source_id`: The id of the source.
            - `phase`: The phase of the source (in ``{'an', 'bn', 'cn'}`` for wye sources and in
                ``{'ab', 'bc', 'ca'}`` for delta sources.).

        and the following columns:
            - `type`: The type of the source, can be ``{'voltage'}``.
            - `voltage`: The complex voltage of the source (in Volts) for the given *phase*.
        """
        return self._get_res_sources_voltages(voltage_type="auto")

    @property
    def res_sources_voltages_pp(self) -> pd.DataFrame:
        """The load flow results of the complex phase-to-phase voltages of the sources (V).

        Only sources with two or more phases are considered.

        The results are returned as a dataframe with the following index:
            - `source_id`: The id of the source.
            - `phase`: The phase of the source (in ``{'ab', 'bc', 'ca'}``).

        and the following columns:
            - `type`: The type of the source, can be ``{'voltage'}``.
            - `voltage`: The complex voltage of the source (in Volts) for the given *phase*.
        """
        return self._get_res_sources_voltages(voltage_type="pp")

    @property
    def res_sources_voltages_pn(self) -> pd.DataFrame:
        """The load flow results of the complex phase-to-neutral voltages of the sources (V).

        Only sources with a neutral are considered.

        The results are returned as a dataframe with the following index:
            - `source_id`: The id of the source.
            - `phase`: The phase of the source (in ``{'an', 'bn', 'cn'}``).

        and the following columns:
            - `type`: The type of the source, can be ``{'voltage'}``.
            - `voltage`: The complex voltage of the source (in Volts) for the given *phase*.
        """
        return self._get_res_sources_voltages(voltage_type="pn")

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
            self._add_element_to_dict(element, self.buses)
        elif isinstance(element, AbstractLoad):
            self._add_element_to_dict(element, self.loads, disconnectable=True)
        elif isinstance(element, Line):
            self._add_element_to_dict(element, self.lines)
        elif isinstance(element, Transformer):
            self._add_element_to_dict(element, self.transformers)
        elif isinstance(element, Switch):
            self._add_element_to_dict(element, self.switches)
        elif isinstance(element, VoltageSource):
            self._add_element_to_dict(element, self.sources, disconnectable=True)
        elif isinstance(element, Ground):
            self._add_element_to_dict(element, self.grounds)
        elif isinstance(element, PotentialRef):
            self._add_element_to_dict(element, self.potential_refs)
        elif isinstance(element, GroundConnection):
            self._add_element_to_dict(element, self.ground_connections)
        else:
            msg = f"Unknown element {element!r} cannot be added to the network."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        self._valid = False
        self._results_valid = False

    def _add_element_to_dict(self, element: _E, to: dict[Id, _E], disconnectable: bool = False) -> None:
        if element.id in to and (old := to[element.id]) is not element:
            element._disconnect()  # Don't leave it lingering in other elements _connected_elements
            old_type = type(old).__name__
            prefix = "An" if old_type[0] in "AEIOU" else "A"
            msg = f"{prefix} {old_type} of ID {element.id!r} is already connected to the network."
            if disconnectable:
                msg += " Disconnect the old element first if you meant to replace it."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        to[element.id] = element
        element._network = self

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
        if isinstance(element, AbstractLoad):
            self.loads.pop(element.id)
        elif isinstance(element, VoltageSource):
            self.sources.pop(element.id)
        elif isinstance(element, Bus | AbstractBranch):
            msg = f"{element!r} is a {element.element_type} and cannot be disconnected from a network."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
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
        self._has_floating_neutral = False
        for load in self.loads.values():
            if load.has_floating_neutral:
                self._has_floating_neutral = True
        for source in self.sources.values():
            if source.has_floating_neutral:
                self._has_floating_neutral = True
        self._propagate_potentials()
        cy_elements = []
        for element in self._elements:
            cy_elements.append(element._cy_element)
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
        elements.update(self.lines.values())
        elements.update(self.transformers.values())
        elements.update(self.switches.values())
        elements.update(self.loads.values())
        elements.update(self.sources.values())
        elements.update(self.grounds.values())
        elements.update(self.potential_refs.values())
        elements.update(self.ground_connections.values())

        if not elements:
            msg = "Cannot create a network without elements."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.EMPTY_NETWORK)

        # Temporarily print a better error message for missing ground_connections to help with the
        # transition. TODO remove this special case in version 0.15.0
        missing_gc = next((gc for g in self.grounds.values() for gc in g.connections), None)
        if not self.ground_connections and missing_gc is not None:
            gc_hint = (
                "ground.connections" if len(self.grounds) == 1 else "[gc for g in grounds for gc in g.connections]"
            )
            msg = (
                f"It looks like you forgot to add the ground connections to the network. Either use "
                f"`ElectricalNetwork.from_element()` to create the network or add the ground connections "
                f"manually, e.g: `ElectricalNetwork(..., ground_connections={gc_hint})`."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT)

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
        all_phases = set()
        for bus in self.buses.values():
            if not bus._initialized:
                all_phases |= set(bus.phases)

        starting_potentials, starting_source = self._get_potentials(all_phases)
        elements: list[tuple[Element, dict[str, complex], Element | None]] = [
            (starting_source, starting_potentials, None)
        ]
        self._elements = []
        self._has_loop = False
        visited: set[Element] = {starting_source}
        while elements:
            element, potentials, parent = elements.pop(-1)
            self._elements.append(element)
            if isinstance(element, Bus) and not element._initialized:
                element.initial_potentials = np.array([potentials[p] for p in element.phases], dtype=np.complex128)
                element._initialized_by_the_user = False  # only used for serialization
            if not isinstance(element, Ground):  # Do not go from ground to buses/branches
                for e in element._connected_elements:
                    if e not in visited:
                        if isinstance(element, Transformer):
                            phase_shift = CLOCK_PHASE_SHIFT[element.parameters.phase_displacement]
                            kd = element.parameters._ulv / element.parameters._uhv * phase_shift
                            new_potentials = {key: p * kd * element.tap for key, p in potentials.items()}
                        else:
                            new_potentials = potentials
                        elements.append((e, new_potentials, element))
                        visited.add(e)
                    elif parent != e and not isinstance(e, Ground):
                        self._has_loop = True
            else:
                for e in element._connected_elements:
                    if e not in visited and isinstance(e, PotentialRef):
                        elements.append((e, potentials, element))
                        visited.add(e)

        if len(visited) < (
            len(self.buses)
            + len(self.lines)
            + len(self.transformers)
            + len(self.switches)
            + len(self.sources)
            + len(self.loads)
            + len(self.grounds)
            + len(self.potential_refs)
            + len(self.ground_connections)
        ):
            unconnected_elements = [
                element
                for element in chain(
                    self.buses.values(),
                    self.lines.values(),
                    self.transformers.values(),
                    self.switches.values(),
                    self.sources.values(),
                    self.loads.values(),
                    self.grounds.values(),
                    self.potential_refs.values(),
                    self.ground_connections.values(),
                )
                if element not in visited
            ]
            printable_elements = textwrap.wrap(
                ", ".join(f"{type(e).__name__}({e.id!r})" for e in unconnected_elements), 500
            )
            msg = f"The elements {printable_elements} are not electrically connected to a voltage source."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.POORLY_CONNECTED_ELEMENT)

    def _get_potentials(self, all_phases: set[str]) -> tuple[dict[str, complex], VoltageSource]:
        """Compute initial potentials from the voltages sources of the network, get also the starting source"""
        starting_source = None
        potentials = {"n": 0j}
        # if there are multiple voltage sources, start from the higher one (the last one in the sorted below)
        for source in sorted(self.sources.values(), key=lambda x: np.average(np.abs(x._voltages))):
            source_voltages = source._voltages
            starting_source = source
            if "n" in source.phases:
                # Assume Vn = 0
                for phase, voltage in zip(source.phases[:-1], source_voltages, strict=True):
                    potentials[phase] = voltage
            elif len(source.phases) == 2:
                # Assume V1 + V2 = 0
                u = source_voltages[0]
                potentials[source.phases[0]] = u / 2
                potentials[source.phases[1]] = -u / 2
            else:
                assert source.phases == "abc"
                # Assume Va + Vb + Vc = 0
                u_ab = source_voltages[0]
                u_bc = source_voltages[1]
                v_b = (u_bc - u_ab) / 3
                v_c = v_b - u_bc
                v_a = v_b + u_ab
                potentials["a"] = v_a
                potentials["b"] = v_b
                potentials["c"] = v_c

        if len(potentials) < len(all_phases):
            # We failed to determine all the potentials (the sources are strange), fallback to something simple
            v = np.average(np.abs(starting_source._voltages))
            potentials["a"] = v
            potentials["b"] = v * ALPHA2
            potentials["c"] = v * ALPHA
            potentials["n"] = 0.0

        return potentials, starting_source

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
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        """Construct an electrical network from a dict created with :meth:`to_dict`.

        Args:
            data:
                The dictionary containing the network data.

            include_results:
                If True (default) and the results of the load flow are included in the dictionary,
                the results are also loaded into the element.

        Returns:
            The constructed network.
        """
        network_data, has_results = network_from_dict(data=data, include_results=include_results)
        network = cls(**network_data)
        network._no_results = not has_results
        network._results_valid = has_results
        return network

    def _to_dict(self, include_results: bool) -> JsonDict:
        return network_to_dict(en=self, include_results=include_results)

    #
    # Results saving
    #
    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        """Get the voltages and currents computed by the load flow and return them as a dict."""
        if warning:
            self._check_valid_results()  # Warn only once if asked
        return {
            "buses": [bus._results_to_dict(warning=False, full=full) for bus in self.buses.values()],
            "lines": [line._results_to_dict(warning=False, full=full) for line in self.lines.values()],
            "transformers": [
                transformer._results_to_dict(warning=False, full=full) for transformer in self.transformers.values()
            ],
            "switches": [switch._results_to_dict(warning=False, full=full) for switch in self.switches.values()],
            "loads": [load._results_to_dict(warning=False, full=full) for load in self.loads.values()],
            "sources": [source._results_to_dict(warning=False, full=full) for source in self.sources.values()],
            "grounds": [ground._results_to_dict(warning=False, full=full) for ground in self.grounds.values()],
            "potential_refs": [
                p_ref._results_to_dict(warning=False, full=full) for p_ref in self.potential_refs.values()
            ],
            "ground_connections": [
                gc._results_to_dict(warning=False, full=full) for gc in self.ground_connections.values()
            ],
        }

    #
    # DGS interface
    #
    @classmethod
    def dgs_export_definition_folder_path(cls) -> Path:
        """Returns the path to the DGS pfd file to use as "Export Definition Folder"."""
        return Path(resources.files("roseau.load_flow") / "data" / "io" / "DGS-RLF.pfd").expanduser().absolute()

    @classmethod
    def from_dgs(cls, path: StrPath, use_name_as_id: bool = False) -> Self:
        """Construct an electrical network from json DGS file (PowerFactory).

        Only JSON format of DGS is currently supported. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.

        Args:
            path:
                The path to the network DGS data file.

            use_name_as_id:
                If True, use the name of the elements (i.e. the ``loc_name`` field) as their ID.
                Otherwise, use their DGS file ID (i.e. the ``FID`` field) as their ID. Can only be
                used if the names are unique. Default is False.

        Returns:
            The constructed network.
        """
        return cls(**network_from_dgs(path, use_name_as_id))

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
            "nb_lines": [],
            "nb_transformers": [],
            "nb_switches": [],
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
            match_names_list = cls._filter_catalogue_str(value=name, strings=available_names)
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
                match_load_point_names_list = cls._filter_catalogue_str(
                    value=load_point_name, strings=available_load_points
                )
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
            catalogue_dict["nb_lines"].append(network_data["nb_lines"])
            catalogue_dict["nb_transformers"].append(network_data["nb_transformers"])
            catalogue_dict["nb_switches"].append(network_data["nb_switches"])
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
        catalogue_data, _ = cls._get_catalogue(name=name, load_point_name=load_point_name, raise_if_not_found=True)

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
        catalogue_data, _ = cls._get_catalogue(name=name, load_point_name=load_point_name, raise_if_not_found=False)
        return (
            catalogue_data.reset_index(drop=True)
            .rename(
                columns={
                    "name": "Name",
                    "nb_buses": "Nb buses",
                    "nb_lines": "Nb lines",
                    "nb_transformers": "Nb transformers",
                    "nb_switches": "Nb switches",
                    "nb_loads": "Nb loads",
                    "nb_sources": "Nb sources",
                    "nb_grounds": "Nb grounds",
                    "nb_potential_refs": "Nb potential refs",
                    "load_points": "Available load points",
                }
            )
            .set_index("Name")
        )
