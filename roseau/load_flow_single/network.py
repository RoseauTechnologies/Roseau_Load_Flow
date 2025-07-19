"""
This module defines the electrical network class.
"""

import json
import logging
from collections.abc import Iterable, Mapping
from math import nan
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self, TypeVar, final

import geopandas as gpd
import pandas as pd

from roseau.load_flow import SQRT3, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import CRSLike, Id, JsonDict, MapOrSeq, StrPath
from roseau.load_flow.utils import DTYPES, AbstractNetwork, LoadTypeDtype, count_repr, optional_deps
from roseau.load_flow_engine.cy_engine import CyGround, CyPotentialRef
from roseau.load_flow_single.io import network_from_dgs, network_from_dict, network_to_dgs, network_to_dict
from roseau.load_flow_single.models import (
    AbstractLoad,
    Bus,
    CurrentLoad,
    Element,
    ImpedanceLoad,
    Line,
    PowerLoad,
    Switch,
    Transformer,
    VoltageSource,
)

if TYPE_CHECKING:
    from networkx import Graph

logger = logging.getLogger(__name__)

_E = TypeVar("_E", bound=Element)


@final
class ElectricalNetwork(AbstractNetwork[Element]):
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
            An optional Coordinate Reference System to use with geo data frames. Can be anything
            accepted by geopandas and pyproj, such as an authority string or WKT string.

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

    is_multi_phase: Final = False

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
        crs: CRSLike | None = None,
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

        self._elements_by_type = {  # type: ignore
            "bus": self.buses,
            "line": self.lines,
            "transformer": self.transformers,
            "switch": self.switches,
            "load": self.loads,
            "source": self.sources,
        }
        super().__init__(crs=crs)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}:"
            f" {count_repr(self.buses, 'bus', 'buses')},"
            f" {count_repr(self.lines, 'line', 'lines')},"
            f" {count_repr(self.transformers, 'transformer', 'transformers')},"
            f" {count_repr(self.switches, 'switch', 'switches')},"
            f" {count_repr(self.loads, 'load')},"
            f" {count_repr(self.sources, 'source')}"
            f">"
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
    # Properties to access the load flow results as dataframes
    #
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
            current1 = line._side1._res_current_getter(warning=False)
            current2 = line._side2._res_current_getter(warning=False)
            voltage1 = line._side1._res_voltage_getter(warning=False)
            voltage2 = line._side2._res_voltage_getter(warning=False)
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
            current_hv = transformer._side1._res_current_getter(warning=False)
            current_lv = transformer._side2._res_current_getter(warning=False)
            voltage_hv = transformer._side1._res_voltage_getter(warning=False)
            voltage_lv = transformer._side2._res_voltage_getter(warning=False)
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
            current1 = switch._side1._res_current_getter(warning=False)
            current2 = switch._side2._res_current_getter(warning=False)
            voltage1 = switch._side1._res_voltage_getter(warning=False)
            voltage2 = switch._side2._res_voltage_getter(warning=False)
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
    def _add_ground_connections(self, element: Element) -> None:
        if isinstance(element, Bus):
            element._cy_element.connect(self._ground, [(1, 0)])
        elif isinstance(element, Line) and element.with_shunt:
            element._cy_element.connect(self._ground, [(2, 0)])

    def _get_has_floating_neutral(self) -> bool:
        return False  # single-phase networks do not support floating neutral

    def _propagate_voltages(self) -> None:
        starting_voltage, starting_source = self._get_starting_voltage()
        elements: list[tuple[Element, complex, Element | None]] = [(starting_source, starting_voltage, None)]
        self._elements = []
        self._has_loop = False
        visited: set[Element] = {starting_source}
        while elements:
            element, initial_voltage, parent = elements.pop(-1)
            self._elements.append(element)
            if isinstance(element, Bus) and not element._initialized:
                element.initial_voltage = initial_voltage
                element._initialized_by_the_user = False  # only used for serialization
            elif isinstance(element, Switch) and not element.closed:
                # Do not propagate voltages through open switches
                continue
            for e in element._connected_elements:
                if e not in visited:
                    if isinstance(element, Transformer):
                        if element.bus_hv in visited:
                            # Traversing from HV side to LV side
                            element_voltage = initial_voltage * (element.parameters.kd * element._tap)
                        else:
                            # Traversing from LV side to HV side
                            element_voltage = initial_voltage / (element.parameters.kd * element._tap)
                    else:
                        element_voltage = initial_voltage
                    elements.append((e, element_voltage, element))
                    visited.add(e)
                elif (
                    not self._has_loop  # Save some checks if we already found a loop
                    and parent != e
                    and (not isinstance(e, Switch) or e.closed)
                ):
                    self._has_loop = True
        self._check_connectivity(visited, starting_source)

    def _get_starting_voltage(self) -> tuple[complex, VoltageSource]:
        """Compute the initial voltages from the voltage sources of the network and get the starting source."""
        sources = iter(self.sources.values())
        starting_source = next(sources)
        # if there are multiple voltage sources, start from the one with the highest voltage
        for source in sources:
            if abs(source._voltage) > abs(starting_source._voltage):
                starting_source = source
        return starting_source._voltage, starting_source

    @classmethod
    def _check_ref(cls, elements: Iterable[Element]) -> None:
        pass  # potential reference is managed internally

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
        network_data, tool_data, has_results = network_from_dict(data=data, include_results=include_results)
        network = cls(**network_data)
        network.tool_data._storage.update(tool_data)
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
    def _from_dgs(cls, data: Mapping[str, Any], /, use_name_as_id: bool = False) -> Self:
        return cls(**network_from_dgs(data, use_name_as_id))

    def to_dgs_dict(self) -> JsonDict:
        """Convert the network to a dictionary compatible with the DGS json format (PowerFactory).

        Only JSON format of DGS is currently. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.
        """
        return network_to_dgs(self)

    def to_dgs_file(self, path: StrPath, *, encoding: str | None = None) -> Path:
        """Save the network to a json DGS file (PowerFactory).

        Only JSON format of DGS is currently. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.

        Args:
            path:
                Save the network to this path.

            encoding:
                The encoding of the file to be passed to the `open` function.
        """
        data = network_to_dgs(self)
        path = Path(path).expanduser().resolve()
        with open(path, "w", encoding=encoding) as f:
            json.dump(data, f, indent=2)
        return path

    # TODO: delete the alias when we know how to teach sphinx to include the docstring of the parent class
    tool_data = AbstractNetwork.tool_data
