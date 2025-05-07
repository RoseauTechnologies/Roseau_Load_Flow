import logging
import math
import warnings
from collections.abc import Iterator
from typing import Final, Self

import numpy as np
import pandas as pd
from shapely.geometry.base import BaseGeometry

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Complex, Float, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_engine.cy_engine import CyBus
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.terminals import AbstractTerminal

logger = logging.getLogger(__name__)


class Bus(AbstractTerminal[CyBus]):
    """An electrical bus."""

    element_type: Final = "bus"

    def __init__(
        self,
        id: Id,
        *,
        geometry: BaseGeometry | None = None,
        nominal_voltage: Float | Q_[Float] | None = None,
        min_voltage_level: Float | Q_[Float] | None = None,
        max_voltage_level: Float | Q_[Float] | None = None,
        initial_voltage: Complex | Q_[Complex] | None = None,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                A unique ID of the bus in the network buses.

            geometry:
                An optional geometry of the bus; a :class:`~shapely.Geometry` that represents the
                x-y coordinates of the bus.

            nominal_voltage:
                An optional nominal phase-to-phase voltage for the bus (V). It is not used in the
                load flow. It can be a float (V) or a :class:`Quantity <roseau.load_flow.units.Q_>`
                of float. It must be provided if either `min_voltage_level` or `max_voltage_level`
                is provided.

            min_voltage_level:
                An optional minimal voltage level of the bus (%). It is not used in the load flow.
                It must be a percentage of the `nominal_voltage` between 0 and 1. Either a float
                (unitless) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            max_voltage_level:
                An optional maximal voltage level of the bus (%). It is not used in the load flow.
                It must be a percentage of the `nominal_voltage` between 0 and 1. Either a float
                (unitless) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            initial_voltage:
                An optional initial voltage of the bus (V). It can be used to improve the convergence
                of the load flow algorithm.
        """
        super().__init__(id)
        initialized = initial_voltage is not None
        if initial_voltage is None:
            initial_voltage = 0.0
        self.initial_voltage = initial_voltage
        self.geometry = self._check_geometry(geometry)

        self._nominal_voltage: float | None = None
        self._min_voltage_level: float | None = None
        self._max_voltage_level: float | None = None
        if nominal_voltage is not None:
            self.nominal_voltage = nominal_voltage
        if min_voltage_level is not None:
            self.min_voltage_level = min_voltage_level
        if max_voltage_level is not None:
            self.max_voltage_level = max_voltage_level

        self._short_circuit: bool = False

        self._initialized = initialized
        self._initialized_by_the_user = initialized  # only used for serialization
        self._cy_element = CyBus(
            n=self._n, potentials=np.array([self._initial_voltage / SQRT3, 0], dtype=np.complex128)
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    @property
    @ureg_wraps("V", (None,))
    def initial_voltage(self) -> Q_[complex]:
        """Initial voltage of the bus (V)."""
        return self._initial_voltage

    @initial_voltage.setter
    @ureg_wraps(None, (None, "V"))
    def initial_voltage(self, value: Complex | Q_[Complex]) -> None:
        self._initial_voltage = complex(value)
        self._invalidate_network_results()
        self._initialized = True
        self._initialized_by_the_user = True
        if self._cy_initialized:
            self._cy_element.initialize_potentials(np.array([self._initial_voltage / SQRT3, 0], dtype=np.complex128))

    @property
    def nominal_voltage(self) -> Q_[float] | None:
        """The phase-to-phase nominal voltage of the bus (V) if it is set."""
        return None if self._nominal_voltage is None else Q_(self._nominal_voltage, "V")

    @nominal_voltage.setter
    @ureg_wraps(None, (None, "V"))
    def nominal_voltage(self, value: Float | Q_[Float] | None) -> None:
        if pd.isna(value):
            if self._max_voltage_level is not None or self._min_voltage_level is not None:
                warnings.warn(
                    message=(
                        f"The nominal voltage of bus {self.id!r} is required to use `min_voltage_level` "
                        f"and `max_voltage_level`."
                    ),
                    category=UserWarning,
                    stacklevel=find_stack_level(),
                )
            self._nominal_voltage = None
        else:
            if value <= 0:
                msg = f"The nominal voltage of bus {self.id!r} must be positive. {value} V has been provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
            self._nominal_voltage = float(value)

    @property
    def min_voltage_level(self) -> Q_[float] | None:
        """The minimum voltage level of the bus (pu) if it is set."""
        return None if self._min_voltage_level is None else Q_(self._min_voltage_level, "")

    @min_voltage_level.setter
    @ureg_wraps(None, (None, ""))
    def min_voltage_level(self, value: Float | Q_[Float] | None) -> None:
        if pd.isna(value):
            self._min_voltage_level = None
        else:
            if self._max_voltage_level is not None and value > self._max_voltage_level:
                msg = (
                    f"Cannot set min voltage level of bus {self.id!r} to {value} as it is higher than its "
                    f"max voltage ({self._max_voltage_level})."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
            if self._nominal_voltage is None:
                warnings.warn(
                    message=(
                        f"The min voltage level of bus {self.id!r} is useless without a nominal voltage. Please "
                        f"define a nominal voltage for this bus."
                    ),
                    category=UserWarning,
                    stacklevel=find_stack_level(),
                )
            self._min_voltage_level = float(value)

    @property
    def min_voltage(self) -> Q_[float] | None:
        """The minimum voltage of the bus (V) if it is set."""
        return (
            None
            if self._min_voltage_level is None or self._nominal_voltage is None
            else Q_(self._min_voltage_level * self._nominal_voltage, "V")
        )

    @property
    def max_voltage_level(self) -> Q_[float] | None:
        """The maximum voltage level of the bus (pu) if it is set."""
        return None if self._max_voltage_level is None else Q_(self._max_voltage_level, "")

    @max_voltage_level.setter
    @ureg_wraps(None, (None, ""))
    def max_voltage_level(self, value: Float | Q_[Float] | None) -> None:
        if pd.isna(value):
            self._max_voltage_level = None
        else:
            if self._min_voltage_level is not None and value < self._min_voltage_level:
                msg = (
                    f"Cannot set max voltage level of bus {self.id!r} to {value} as it is lower than its "
                    f"min voltage ({self._min_voltage_level})."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
            if self._nominal_voltage is None:
                warnings.warn(
                    message=(
                        f"The max voltage level of bus {self.id!r} is useless without a nominal voltage. Please "
                        f"define a nominal voltage for this bus."
                    ),
                    category=UserWarning,
                    stacklevel=find_stack_level(),
                )
            self._max_voltage_level = float(value)

    @property
    def max_voltage(self) -> Q_[float] | None:
        """The maximum voltage of the bus (V) if it is set."""
        return (
            None
            if self._max_voltage_level is None or self._nominal_voltage is None
            else Q_(self._max_voltage_level * self._nominal_voltage, "V")
        )

    @property
    def short_circuit(self) -> bool:
        """Whether there is a short circuit on the bus or not"""
        return self._short_circuit

    def add_short_circuit(self) -> None:
        """Add a short-circuit by connecting all the phases together with a ground."""
        from roseau.load_flow_single import CurrentLoad, PowerLoad

        for element in self._connected_elements:
            if isinstance(element, (PowerLoad, CurrentLoad)):
                msg = (
                    f"A {element.type} load {element.id!r} is already connected on bus {self.id!r}. "
                    f"It makes the short-circuit calculation impossible."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)

        self._short_circuit = True
        self._cy_element.connect_ports(np.array([0, 1], dtype=np.int32))

        if self.network is not None:
            self.network._valid = False

    def propagate_limits(self, force: bool = False) -> None:
        """Propagate the voltage limits to galvanically connected buses.

        Galvanically connected buses are buses connected to this bus through lines or switches. This
        ensures that these voltage limits are only applied to buses with the same voltage level. If
        a bus is connected to this bus through a transformer, the voltage limits are not propagated
        to that bus.

        If this bus does not define any voltage limits, calling this method will unset the limits
        of the connected buses.

        Args:
            force:
                If ``False`` (default), an exception is raised if connected buses already have
                limits different from this bus. If ``True``, the limits are propagated even if
                connected buses have different limits.
        """
        from roseau.load_flow_single.models.lines import Line
        from roseau.load_flow_single.models.switches import Switch

        buses: set[Bus] = set()
        visited: set[Element] = set()
        remaining = set(self._connected_elements)

        while remaining:
            branch = remaining.pop()
            visited.add(branch)
            if not isinstance(branch, (Line, Switch)):
                continue
            for element in branch._connected_elements:
                if not isinstance(element, Bus) or element is self or element in buses:
                    continue
                buses.add(element)
                to_add = set(element._connected_elements).difference(visited)
                remaining.update(to_add)
                if not (
                    force
                    or self._nominal_voltage is None
                    or element._nominal_voltage is None
                    or math.isclose(element._nominal_voltage, self._nominal_voltage)
                ):
                    msg = (
                        f"Cannot propagate the nominal voltage ({self._nominal_voltage} V) of bus {self.id!r} "
                        f"to bus {element.id!r} with different nominal voltage ({element._nominal_voltage} V)."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
                if not (
                    force
                    or self._min_voltage_level is None
                    or element._min_voltage_level is None
                    or math.isclose(element._min_voltage_level, self._min_voltage_level)
                ):
                    msg = (
                        f"Cannot propagate the minimum voltage level ({self._min_voltage_level}) of bus {self.id!r} "
                        f"to bus {element.id!r} with different minimum voltage level ({element._min_voltage_level})."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
                if not (
                    force
                    or self._max_voltage_level is None
                    or element._max_voltage_level is None
                    or math.isclose(element._max_voltage_level, self._max_voltage_level)
                ):
                    msg = (
                        f"Cannot propagate the maximum voltage level ({self._max_voltage_level}) of bus {self.id!r} "
                        f"to bus {element.id!r} with different maximum voltage level ({element._max_voltage_level})."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)

        for bus in buses:
            bus._nominal_voltage = self._nominal_voltage
            bus._min_voltage_level = self._min_voltage_level
            bus._max_voltage_level = self._max_voltage_level

    def get_connected_buses(self) -> Iterator[Id]:
        """Get IDs of all the buses galvanically connected to this bus.

        These are all the buses connected via one or more lines or switches to this bus.
        """
        from roseau.load_flow_single.models.lines import Line
        from roseau.load_flow_single.models.switches import Switch

        visited_buses = {self.id}
        yield self.id

        visited: set[Element] = set()
        remaining = set(self._connected_elements)

        while remaining:
            branch = remaining.pop()
            visited.add(branch)
            if not isinstance(branch, (Line, Switch)):
                continue
            for element in branch._connected_elements:
                if not isinstance(element, Bus) or element.id in visited_buses:
                    continue
                visited_buses.add(element.id)
                yield element.id
                to_add = set(element._connected_elements).difference(visited)
                remaining.update(to_add)

    #
    # Results
    #
    def _res_voltage_level_getter(self, warning: bool) -> float | None:
        if self._nominal_voltage is None:
            return None
        voltage = self._res_voltage_getter(warning)
        return abs(voltage) / self._nominal_voltage

    @property
    def res_voltage_level(self) -> Q_[float] | None:
        """The load flow result of the bus voltage levels (unitless)."""
        voltages_level = self._res_voltage_level_getter(warning=True)
        return None if voltages_level is None else Q_(voltages_level, "")

    @property
    def res_violated(self) -> bool | None:
        """Whether the bus has voltage limits violations.

        Returns ``None`` if the bus has no voltage limits set.
        """
        u_min = self._min_voltage_level
        u_max = self._max_voltage_level
        if u_min is None and u_max is None:
            return None
        u_pu = self._res_voltage_level_getter(warning=True)
        if u_pu is None:
            return None

        return (u_min is not None and u_pu < u_min) or (u_max is not None and u_pu > u_max)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        if (initial_voltage := data.get("initial_voltage")) is not None:
            initial_voltage = complex(initial_voltage[0], initial_voltage[1])
        self = cls(
            id=data["id"],
            geometry=cls._parse_geometry(data.get("geometry")),
            initial_voltage=initial_voltage,
            nominal_voltage=data.get("nominal_voltage"),
            min_voltage_level=data.get("min_voltage_level"),
            max_voltage_level=data.get("max_voltage_level"),
        )
        self._parse_results_from_dict(data, include_results=include_results)
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results=include_results)
        if self._initialized_by_the_user:
            data["initial_voltage"] = [self._initial_voltage.real, self._initial_voltage.imag]
        if self.geometry is not None:
            data["geometry"] = self.geometry.__geo_interface__
        if self.nominal_voltage is not None:
            data["nominal_voltage"] = self.nominal_voltage.magnitude
        if self.min_voltage_level is not None:
            data["min_voltage_level"] = self.min_voltage_level.magnitude
        if self.max_voltage_level is not None:
            data["max_voltage_level"] = self.max_voltage_level.magnitude
        if include_results:
            data["results"] = data.pop("results")  # move results to the end
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning, full)
        if full:
            results["voltage_level"] = self._res_voltage_level_getter(warning=False)
        return results
