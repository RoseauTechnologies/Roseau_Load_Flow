"""
This module defines the electrical network class.
"""

import json
import logging
import textwrap
import warnings
from collections.abc import Mapping
from importlib import resources
from itertools import chain
from math import nan
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import CRS
from typing_extensions import Self

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow._solvers import AbstractSolver
from roseau.load_flow.typing import Id, JsonDict, MapOrSeq, Solver, StrPath
from roseau.load_flow.utils import DTYPES, JsonMixin, LoadTypeDtype, count_repr, find_stack_level, optional_deps
from roseau.load_flow_engine.cy_engine import CyElectricalNetwork, CyGround, CyPotentialRef
from roseau.load_flow_single.io import network_from_dgs, network_from_dict, network_to_dgs, network_to_dict
from roseau.load_flow_single.models.branches import AbstractBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.lines import Line
from roseau.load_flow_single.models.loads import AbstractLoad, CurrentLoad, ImpedanceLoad, PowerLoad
from roseau.load_flow_single.models.sources import VoltageSource
from roseau.load_flow_single.models.switches import Switch
from roseau.load_flow_single.models.transformers import Transformer

if TYPE_CHECKING:
    from networkx import Graph

logger = logging.getLogger(__name__)

_E = TypeVar("_E", bound=Element)


class ElectricalNetwork(JsonMixin):
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
            The loads of the network. Either a list of loads or a dictionary of loads with their
            IDs as keys. There are three types of loads: constant power, constant current, and
            constant impedance.

        sources:
            The sources of the network. Either a list of sources or a dictionary of sources with
            their IDs as keys. A network must have at least one source. Note that two sources
            cannot be connected with a switch.

        crs:
            An optional Coordinate Reference System to use with geo data frames. If not provided,
            the ``EPSG:4326`` CRS will be used.

    Attributes:
        buses (dict[Id, roseau.load_flow_single.Bus]):
            Dictionary of buses of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<buses_frame>`.

        lines (dict[Id, roseau.load_flow_single.Line]):
            Dictionary of lines of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<lines_frame>`.

        transformers (dict[Id, roseau.load_flow_single.Transformer]):
            Dictionary of transformers of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<transformers_frame>`.

        switches (dict[Id, roseau.load_flow_single.Switch]):
            Dictionary of switches of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<switches_frame>`.

        loads (dict[Id, roseau.load_flow_single.AbstractLoad]):
            Dictionary of loads of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<loads_frame>`.

        sources (dict[Id, roseau.load_flow_single.VoltageSource]):
            Dictionary of voltage sources of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<sources_frame>`.
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
        crs: str | CRS | None = None,
    ) -> None:
        self.buses: dict[Id, Bus] = self._elements_as_dict(buses, RoseauLoadFlowExceptionCode.BAD_BUS_ID)
        self.lines: dict[Id, Line] = self._elements_as_dict(lines, RoseauLoadFlowExceptionCode.BAD_LINE_ID)
        self.transformers: dict[Id, Transformer] = self._elements_as_dict(
            transformers, RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_ID
        )
        self.switches: dict[Id, Switch] = self._elements_as_dict(switches, RoseauLoadFlowExceptionCode.BAD_SWITCH_ID)
        self.loads: dict[Id, AbstractLoad | PowerLoad | CurrentLoad | ImpedanceLoad] = self._elements_as_dict(
            loads, RoseauLoadFlowExceptionCode.BAD_LOAD_ID
        )
        self.sources: dict[Id, VoltageSource] = self._elements_as_dict(
            sources, RoseauLoadFlowExceptionCode.BAD_SOURCE_ID
        )

        # Add ground and pref
        self._ground = CyGround()
        self._potential_ref = CyPotentialRef()
        self._ground.connect(self._potential_ref, [(0, 0)])
        for bus in self.buses.values():
            bus._cy_element.connect(self._ground, [(1, 0)])
        for line in self.lines.values():
            if line.with_shunt:
                self._ground.connect(line._cy_element, [(0, 2)])

        self._elements: list[Element] = []
        self._has_loop = False
        self._has_floating_neutral = False
        self._check_validity(constructed=True)
        self._create_network()
        self._valid = True
        self._solver = AbstractSolver.from_dict(data={"name": self._DEFAULT_SOLVER, "params": {}}, network=self)
        if crs is None:
            crs = "EPSG:4326"
        self.crs: CRS = CRS(crs)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}:"
            f" {count_repr(self.buses, 'bus', 'buses')},"
            f" {count_repr(self.lines, 'line', 'lines')},"
            f" {count_repr(self.transformers, 'transformer', 'transformers')},"
            f" {count_repr(self.switches, 'switch', 'switches')},"
            f" {count_repr(self.loads, 'load')},"
            f" {count_repr(self.sources, 'source')},"
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
    def from_element(cls, initial_bus: Bus) -> Self:
        """Construct the network from only one element (bus) and add the others automatically.

        Args:
            initial_bus:
                Any bus of the network. The network is constructed from this bus and all the
                elements connected to it. This is usually the main source bus of the network.

        Returns:
            The network constructed from the given bus and all the elements connected to it.
        """
        buses: list[Bus] = []
        lines: list[Line] = []
        transformers: list[Transformer] = []
        switches: list[Switch] = []
        loads: list[PowerLoad | CurrentLoad | ImpedanceLoad] = []
        sources: list[VoltageSource] = []

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
        )

    #
    # Properties to access the data as dataframes
    #
    @property
    def buses_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`buses` of the network as a geo dataframe."""
        index = []
        data = {"nominal_voltage": [], "min_voltage_level": [], "max_voltage_level": [], "geometry": []}
        for bus in self.buses.values():
            index.append(bus.id)
            data["nominal_voltage"].append(bus._nominal_voltage if bus._nominal_voltage is not None else nan)
            data["min_voltage_level"].append(bus._min_voltage_level if bus._min_voltage_level is not None else nan)
            data["max_voltage_level"].append(bus._max_voltage_level if bus._max_voltage_level is not None else nan)
            data["geometry"].append(bus.geometry)
        return gpd.GeoDataFrame(data=data, index=pd.Index(index, name="id"), geometry="geometry", crs=self.crs)

    @property
    def lines_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`lines` of the network as a geo dataframe."""
        index = []
        data = {"bus1_id": [], "bus2_id": [], "parameters_id": [], "length": [], "max_loading": [], "geometry": []}
        for line in self.lines.values():
            index.append(line.id)
            data["bus1_id"].append(line.bus1.id)
            data["bus2_id"].append(line.bus2.id)
            data["parameters_id"].append(line.parameters.id)
            data["length"].append(line.length.m)
            data["max_loading"].append(line._max_loading)
            data["geometry"].append(line.geometry)
        return gpd.GeoDataFrame(data=data, index=pd.Index(index, name="id"), geometry="geometry", crs=self.crs)

    @property
    def transformers_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`transformers` of the network as a geo dataframe."""
        index = []
        data = {"bus_hv_id": [], "bus_lv_id": [], "parameters_id": [], "tap": [], "max_loading": [], "geometry": []}
        for transformer in self.transformers.values():
            index.append(transformer.id)
            data["bus_hv_id"].append(transformer.bus1.id)
            data["bus_lv_id"].append(transformer.bus2.id)
            data["parameters_id"].append(transformer.parameters.id)
            data["tap"].append(transformer._tap)
            data["max_loading"].append(transformer._max_loading)
            data["geometry"].append(transformer.geometry)
        return gpd.GeoDataFrame(data=data, index=pd.Index(index, name="id"), geometry="geometry", crs=self.crs)

    @property
    def switches_frame(self) -> gpd.GeoDataFrame:
        """The :attr:`switches` of the network as a geo dataframe."""
        index = []
        data = {"bus1_id": [], "bus2_id": [], "geometry": []}
        for switch in self.switches.values():
            index.append(switch.id)
            data["bus1_id"].append(switch.bus1.id)
            data["bus2_id"].append(switch.bus2.id)
            data["geometry"].append(switch.geometry)
        return gpd.GeoDataFrame(data=data, index=pd.Index(index, name="id"), geometry="geometry", crs=self.crs)

    @property
    def loads_frame(self) -> pd.DataFrame:
        """The :attr:`loads` of the network as a dataframe."""
        index = []
        data = {"type": [], "bus_id": [], "flexible": []}
        for load in self.loads.values():
            index.append(load.id)
            data["type"].append(load.type)
            data["bus_id"].append(load.bus.id)
            data["flexible"].append(load.is_flexible)
        return pd.DataFrame(data=data, index=pd.Index(index, name="id"))

    @property
    def sources_frame(self) -> pd.DataFrame:
        """The :attr:`sources` of the network as a dataframe."""
        index = []
        data = {"bus_id": []}
        for source in self.sources.values():
            index.append(source.id)
            data["bus_id"].append(source.bus.id)
        return pd.DataFrame(data=data, index=pd.Index(index, name="id"))

    #
    # Helpers to analyze the network
    #
    @property
    def buses_clusters(self) -> list[set[Id]]:
        """Sets of galvanically connected buses, i.e buses connected by lines or a switches.

        This can be useful to isolate parts of the network for localized analysis. For example, to
        study a LV subnetwork of a MV feeder.

        See Also:
            :meth:`Bus.get_connected_buses() <roseau.load_flow_single.models.Bus.get_connected_buses>`:
            Get the buses in the same galvanically isolated section as a certain bus.
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
            graph.add_edge(
                line.bus1.id,
                line.bus2.id,
                id=line.id,
                type="line",
                parameters_id=line.parameters.id,
                max_loading=line._max_loading,
                ampacity=line.parameters._ampacity,
                geom=line.geometry,
            )
        for transformer in self.transformers.values():
            graph.add_edge(
                transformer.bus1.id,
                transformer.bus2.id,
                id=transformer.id,
                type="transformer",
                parameters_id=transformer.parameters.id,
                max_loading=transformer._max_loading,
                sn=transformer.parameters._sn,
                geom=transformer.geometry,
            )
        for switch in self.switches.values():
            graph.add_edge(switch.bus1.id, switch.bus2.id, id=switch.id, type="switch", geom=switch.geometry)
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
        `res_` properties on the element (e.g. ``print(net.buses["bus1"].res_voltage)``.

        You need to activate the license before calling this method. You may set the environment
        variable ``ROSEAU_LOAD_FLOW_LICENSE_KEY`` to your license key and it will be picked
        automatically when calling this method. See the :ref:`license` page for more information.

        Args:
            max_iterations:
                The maximum number of allowed iterations.

            tolerance:
                Tolerance needed for the convergence.

            warm_start:
                If true (the default), the solver is initialized with the voltages of the last
                successful load flow result (if any). Otherwise, the voltages are reset to their
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
            self._create_network()  # <-- calls _propagate_voltages, no warm start
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

        The results are returned as a dataframe with the bus id as index and the following columns:
            - `voltage`: The complex voltage of the bus (in Volts).
            - `violated`: `True` if a voltage levels is not respected.
            - `voltage_level`: The voltage level of the bus (in per-unit).
            - `min_voltage_level`: The minimal voltage level of the bus (in per-unit).
            - `max_voltage_level`: The maximal voltage level of the bus (in per-unit).
            - `nominal_voltage`: The nominal voltage of the bus (in Volts).
        """
        self._check_valid_results()
        index = []
        res_dict = {
            "voltage": [],
            "violated": [],
            "voltage_level": [],
            # Non results
            "min_voltage_level": [],
            "max_voltage_level": [],
            "nominal_voltage": [],
        }
        dtypes = {c: DTYPES[c] for c in res_dict}
        for bus in self.buses.values():
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
            voltage = bus._res_voltage_getter(warning=False)
            if nominal_voltage_defined:
                voltage_level = abs(voltage) / nominal_voltage
                violated = (
                    (voltage_level < min_voltage_level or voltage_level > max_voltage_level)
                    if voltage_limits_set
                    else None
                )
            else:
                voltage_level = nan
                violated = None
            index.append(bus.id)
            res_dict["voltage"].append(voltage)
            res_dict["violated"].append(violated)
            res_dict["voltage_level"].append(voltage_level)
            # Non results
            res_dict["min_voltage_level"].append(min_voltage_level)
            res_dict["max_voltage_level"].append(max_voltage_level)
            res_dict["nominal_voltage"].append(nominal_voltage)
        index = pd.Index(index, dtype=object, name="bus_id")
        return pd.DataFrame(res_dict, index=index).astype(dtypes)

    @property
    def res_lines(self) -> pd.DataFrame:
        """The load flow results of the network lines.

        The results are returned as a dataframe with the line id as index and the following columns:
            - `current1`: The complex current of the line (in Amps) at the first bus.
            - `current2`: The complex current of the line (in Amps) at the second bus.
            - `power1`: The complex power of the line (in VoltAmps) at the first bus.
            - `power2`: The complex power of the line (in VoltAmps) at the second bus.
            - `voltage1`: The complex voltage (in Volts) of the first bus.
            - `voltage2`: The complex voltage (in Volts) of the second bus.
            - `series_loss`: The complex losses in the series and mutual impedances of the line (in
              VoltAmps).
            - `series_current`: The complex current in the series impedance of the line (in Amps).
            - `violated`: True, if the line loading exceeds the maximum loading.
            - `loading`: The loading of the line (in per-unit).
            - `max_loading`: The maximal loading of the line (in per-unit).
            - `ampacity`: The ampacity of the line (in Amps).

        Additional information can be easily computed from this dataframe. For example:

        * To get the active power losses, use the real part of the complex power losses
        * To get the total power losses, add the columns ``power1 + power2``
        * To get the power losses in the shunt components of the line, subtract the series losses
          from the total power losses computed in the previous step:
          ``(power1 + power2) - series_loss``
        * To get the currents in the shunt components of the line:
          - For the first bus, subtract the columns ``current1 - series_current``
          - For the second bus, add the columns ``series_current + current2``
        """
        self._check_valid_results()
        index = []
        res_dict = {
            "current1": [],
            "current2": [],
            "power1": [],
            "power2": [],
            "voltage1": [],
            "voltage2": [],
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
            current1, current2 = line._res_currents_getter(warning=False)
            voltage1, voltage2 = line._res_voltages_getter(warning=False)
            du_line, series_current = line._res_series_values_getter(warning=False)
            power1 = voltage1 * current1.conjugate() * SQRT3
            power2 = voltage2 * current2.conjugate() * SQRT3
            series_loss = du_line * series_current.conjugate() * SQRT3
            max_loading = line._max_loading
            ampacity = line.parameters._ampacity
            if ampacity is None:
                loading = None
                violated = None
            else:
                loading = max(abs(current1), abs(current2)) / ampacity
                violated = loading > max_loading
            index.append(line.id)
            res_dict["current1"].append(current1)
            res_dict["current2"].append(current2)
            res_dict["power1"].append(power1)
            res_dict["power2"].append(power2)
            res_dict["voltage1"].append(voltage1)
            res_dict["voltage2"].append(voltage2)
            res_dict["series_losses"].append(series_loss)
            res_dict["series_current"].append(series_current)
            res_dict["loading"].append(loading)
            res_dict["violated"].append(violated)
            # Non results
            res_dict["max_loading"].append(max_loading)
            res_dict["ampacity"].append(ampacity)
        index = pd.Index(index, dtype=object, name="line_id")
        return pd.DataFrame(res_dict, index=index).astype(dtypes)

    @property
    def res_transformers(self) -> pd.DataFrame:
        """The load flow results of the network transformers.

        The results are returned as a dataframe with the id of the transformer as index and the
        following columns:
            - `current_hv`: The complex current of the transformer on the HV side (in Amps).
            - `current_lv`: The complex current of the transformer on the LV side (in Amps).
            - `power_hv`: The complex power of the transformer on the HV side (in VoltAmps).
            - `power_lv`: The complex power of the transformer on the LV side (in VoltAmps).
            - `voltage_hv`: The complex voltage of the HV bus (in Volts).
            - `voltage_lv`: The complex voltage of the LV bus (in Volts).
            - `violated`: True, if the transformer loading exceeds the maximum loading.
            - `loading`: The loading of the transformer (in per-unit).
            - `max_loading`: The maximal loading of the transformer (in per-unit).
            - `sn`: The nominal power of the transformer (in VoltAmps).
        """
        self._check_valid_results()
        index = []
        res_dict = {
            "current_hv": [],
            "current_lv": [],
            "power_hv": [],
            "power_lv": [],
            "voltage_hv": [],
            "voltage_lv": [],
            "violated": [],
            "loading": [],
            # Non results
            "max_loading": [],
            "sn": [],
        }
        dtypes = {c: DTYPES[c] for c in res_dict}
        for transformer in self.transformers.values():
            current_hv, current_lv = transformer._res_currents_getter(warning=False)
            voltage_hv, voltage_lv = transformer._res_voltages_getter(warning=False)
            power_hv = voltage_hv * current_hv.conjugate() * SQRT3
            power_lv = voltage_lv * current_lv.conjugate() * SQRT3
            sn = transformer.parameters._sn
            max_loading = transformer._max_loading
            loading = max(abs(power_hv), abs(power_lv)) / sn
            violated = loading > max_loading
            index.append(transformer.id)
            res_dict["current_hv"].append(current_hv)
            res_dict["current_lv"].append(current_lv)
            res_dict["power_hv"].append(power_hv)
            res_dict["power_lv"].append(power_lv)
            res_dict["voltage_hv"].append(voltage_hv)
            res_dict["voltage_lv"].append(voltage_lv)
            res_dict["violated"].append(violated)
            res_dict["loading"].append(loading)
            # Non results
            res_dict["max_loading"].append(max_loading)
            res_dict["sn"].append(sn)
        index = pd.Index(index, dtype=object, name="transformer_id")
        return pd.DataFrame(res_dict, index=index).astype(dtypes)

    @property
    def res_switches(self) -> pd.DataFrame:
        """The load flow results of the network switches.

        The results are returned as a dataframe with the id of the switch as index and the following
        columns:
            - `current1`: The complex current of the switch (in Amps) at the first bus.
            - `current2`: The complex current of the switch (in Amps) at the second bus.
            - `power1`: The complex power of the switch (in VoltAmps) at the first bus.
            - `power2`: The complex power of the switch (in VoltAmps) at the second bus.
            - `voltage1`: The complex voltage of the first bus (in Volts).
            - `voltage2`: The complex voltage of the second bus (in Volts).
        """
        self._check_valid_results()
        index = []
        res_dict = {
            "current1": [],
            "current2": [],
            "power1": [],
            "power2": [],
            "voltage1": [],
            "voltage2": [],
        }
        dtypes = {c: DTYPES[c] for c in res_dict}
        for switch in self.switches.values():
            current1, current2 = switch._res_currents_getter(warning=False)
            voltage1, voltage2 = switch._res_voltages_getter(warning=False)
            power1 = voltage1 * current1.conjugate() * SQRT3
            power2 = voltage2 * current2.conjugate() * SQRT3
            index.append(switch.id)
            res_dict["current1"].append(current1)
            res_dict["current2"].append(current2)
            res_dict["power1"].append(power1)
            res_dict["power2"].append(power2)
            res_dict["voltage1"].append(voltage1)
            res_dict["voltage2"].append(voltage2)
        index = pd.Index(index, dtype=object, name="switch_id")
        return pd.DataFrame(res_dict, index=index).astype(dtypes)

    @property
    def res_loads(self) -> pd.DataFrame:
        """The load flow results of the network loads.

        The results are returned as a dataframe with the load id as index and the following columns:
            - `type`: The type of the load, can be ``{'power', 'current', 'impedance'}``.
            - `current`: The complex current of the load (in Amps).
            - `power`: The complex power of the load (in VoltAmps).
            - `voltage`: The complex voltage of the load (in Volts).
        """
        self._check_valid_results()
        index = []
        res_dict = {"type": [], "current": [], "power": [], "voltage": []}
        dtypes = {c: DTYPES[c] for c in res_dict} | {"type": LoadTypeDtype}
        for load in self.loads.values():
            current = load._res_current_getter(warning=False)
            voltage = load._res_voltage_getter(warning=False)
            power = voltage * current.conjugate() * SQRT3
            index.append(load.id)
            res_dict["type"].append(load.type)
            res_dict["current"].append(current)
            res_dict["power"].append(power)
            res_dict["voltage"].append(voltage)
        index = pd.Index(index, dtype=object, name="load_id")
        return pd.DataFrame(res_dict, index=index).astype(dtypes)

    @property
    def res_sources(self) -> pd.DataFrame:
        """The load flow results of the network sources.

        The results are returned as a dataframe with the source id as index and the following columns:
            - `current`: The complex current of the source (in Amps).
            - `power`: The complex power of the source (in VoltAmps).
            - `voltage`: The complex voltage of the source (in Volts).
        """
        self._check_valid_results()
        index = []
        res_dict = {"current": [], "power": [], "voltage": []}
        dtypes = {c: DTYPES[c] for c in res_dict}
        for source in self.sources.values():
            current = source._res_current_getter(warning=False)
            voltage = source._res_voltage_getter(warning=False)
            power = voltage * current.conjugate() * SQRT3
            index.append(source.id)
            res_dict["current"].append(current)
            res_dict["power"].append(power)
            res_dict["voltage"].append(voltage)
        index = pd.Index(index, dtype=object, name="source_id")
        return pd.DataFrame(res_dict, index=index).astype(dtypes)

    #
    # Internal methods, please do not use
    #
    def _connect_element(self, element: Element) -> None:
        """Connect an element to the network.

        When an element is added to the network, extra processing is done to keep the network valid.
        This method is used by the `network` setter of `Element` instances to add the element to the
        internal dictionary of `self`.

        Args:
            element:
                The element to add. Only lines, loads, buses and sources can be added.
        """
        # The C++ electrical network and the tape will be recomputed
        if isinstance(element, Bus):
            self._add_element_to_dict(element, to=self.buses)
            element._cy_element.connect(self._ground, [(1, 0)])
        elif isinstance(element, AbstractLoad):
            self._add_element_to_dict(element, to=self.loads, disconnectable=True)
        elif isinstance(element, Line):
            self._add_element_to_dict(element, to=self.lines)
            if element.with_shunt:
                self._ground.connect(element._cy_element, [(0, 2)])
        elif isinstance(element, Transformer):
            self._add_element_to_dict(element, to=self.transformers)
        elif isinstance(element, Switch):
            self._add_element_to_dict(element, to=self.switches)
        elif isinstance(element, VoltageSource):
            self._add_element_to_dict(element, to=self.sources, disconnectable=True)
        else:
            msg = f"Unknown element {element} can not be added to the network."
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

        When an element is removed from the network, extra processing is needed to keep the network
        valid. This method is used in the by the `network` setter of `Element` instances (when the
        provided network is `None`) to remove the element to the internal dictionary of `self`.
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
        self._propagate_voltages()
        cy_elements = []
        for element in self._elements:
            cy_elements.append(element._cy_element)
        self._cy_electrical_network = CyElectricalNetwork(elements=np.array(cy_elements), nb_elements=len(cy_elements))

    def _check_validity(self, constructed: bool) -> None:
        """Check the validity of the network to avoid having a singular jacobian matrix.

        It also assigns the `self` to the network field of elements.

        Args:
            constructed:
                True if we are adding an element to already constructed network, False otherwise.
        """
        elements: set[Element] = set()
        elements.update(self.buses.values())
        elements.update(self.lines.values())
        elements.update(self.transformers.values())
        elements.update(self.switches.values())
        elements.update(self.loads.values())
        elements.update(self.sources.values())

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

    def _propagate_voltages(self) -> None:
        """Set the voltage on buses that have not been initialized yet and compute self._elements order."""
        starting_voltage, starting_source = self._get_starting_voltage()
        elements = [(starting_source, starting_voltage, None)]
        self._elements = []
        self._has_loop = False
        visited = {starting_source}
        while elements:
            element, initial_voltage, parent = elements.pop(-1)
            self._elements.append(element)
            if isinstance(element, Bus) and not element._initialized:
                element.initial_voltage = initial_voltage
                element._initialized_by_the_user = False  # only used for serialization
            for e in element._connected_elements:
                if e not in visited:
                    if isinstance(element, Transformer):
                        element_voltage = initial_voltage * element.parameters.kd * element._tap
                    else:
                        element_voltage = initial_voltage
                    elements.append((e, element_voltage, element))
                    visited.add(e)
                elif parent != e:
                    self._has_loop = True

        if len(visited) < len(self.buses) + len(self.lines) + len(self.transformers) + len(self.switches) + len(
            self.loads
        ) + len(self.sources):
            unconnected_elements = [
                element
                for element in chain(
                    self.buses.values(),
                    self.lines.values(),
                    self.transformers.values(),
                    self.switches.values(),
                    self.loads.values(),
                    self.sources.values(),
                )
                if element not in visited
            ]
            printable_elements = textwrap.wrap(
                ", ".join(f"{type(e).__name__}({e.id!r})" for e in unconnected_elements), 500
            )
            msg = f"The elements {printable_elements} are not electrically connected to a voltage source."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.POORLY_CONNECTED_ELEMENT)

    def _get_starting_voltage(self) -> tuple[complex, VoltageSource]:
        """Compute initial voltages from the voltage sources of the network, get also the starting source."""
        starting_source = None
        initial_voltage = None
        # if there are multiple voltage sources, start from the higher one (the last one in the sorted below)
        for source in sorted(self.sources.values(), key=lambda x: np.average(np.abs(x._voltage))):
            source_voltage = source._voltage
            starting_source = source
            initial_voltage = source_voltage

        return initial_voltage, starting_source

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
        buses, lines, transformers, switches, loads, sources, has_results = network_from_dict(
            data=data, include_results=include_results
        )
        network = cls(
            buses=buses,
            lines=lines,
            transformers=transformers,
            switches=switches,
            loads=loads,
            sources=sources,
        )
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
        }

    #
    # DGS interface
    #
    @classmethod
    def dgs_export_definition_folder_path(cls) -> Path:
        """Returns the path to the DGS pfd file to use as "Export Definition Folder"."""
        return Path(resources.files("roseau.load_flow") / "data" / "io" / "DGS-RLF.pfd").expanduser().absolute()

    @classmethod
    def from_dgs_dict(cls, data: Mapping[str, Any], /, use_name_as_id: bool = False) -> Self:
        """Construct an electrical network from a json DGS file (PowerFactory).

        Only JSON format of DGS is currently supported. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.

        Args:
            data:
                The dictionary containing the network DGS data.

            use_name_as_id:
                If True, use the name of the elements (the ``loc_name`` field) as their id. Otherwise,
                use the id from the DGS file (the ``FID`` field). Only use if you are sure the names
                are unique. Default is False.

        Returns:
            The constructed network.
        """
        return cls(**network_from_dgs(data, use_name_as_id))

    @classmethod
    def from_dgs_file(cls, path: StrPath, use_name_as_id: bool = False) -> Self:
        """Construct an electrical network from a json DGS file (PowerFactory).

        Only JSON format of DGS is currently supported. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.

        Args:
            path:
                The path to the network DGS data file.

            use_name_as_id:
                If True, use the name of the elements (the ``loc_name`` field) as their id. Otherwise,
                use the id from the DGS file (the ``FID`` field). Only use if you are sure the names
                are unique. Default is False.

        Returns:
            The constructed network.
        """
        with open(path, encoding="ISO-8859-10") as f:
            data = json.load(f)
        return cls(**network_from_dgs(data, use_name_as_id))

    def to_dgs_dict(self) -> JsonDict:
        """Convert the network to a dictionary compatible with the DGS json format (PowerFactory).

        Only JSON format of DGS is currently. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.
        """
        return network_to_dgs(self)

    def to_dgs_file(self, path: StrPath) -> Path:
        """Save the network to a json DGS file (PowerFactory).

        Only JSON format of DGS is currently. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.
        """
        data = network_to_dgs(self)
        path = Path(path).expanduser().resolve()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path
