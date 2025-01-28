import logging
import warnings
from collections.abc import Iterator

import numpy as np
import pandas as pd
from shapely.geometry.base import BaseGeometry
from typing_extensions import Self

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Complex, Float, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_engine.cy_engine import CyBus
from roseau.load_flow_single.models.core import Element

logger = logging.getLogger(__name__)


class Bus(Element[CyBus]):
    """An electrical bus."""

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
                An optional nominal voltage for the bus (V). It is not used in the load flow.
                It can be a float (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            min_voltage_level:
                An optional minimum voltage of the bus (%). It is not used in the load flow.
                It must be a percentage of the `nominal_voltage`. If provided, the nominal voltage becomes mandatory.
                Either a float (unitless) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            max_voltage_level:
                An optional maximum voltage of the bus (%). It is not used in the load flow.
                It must be a percentage of the `nominal_voltage`. If provided, the nominal voltage becomes mandatory.
                Either a float (unitless) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            initial_voltage:
                An optional initial voltage of the bus (V). It can be used to improve the convergence
                of the load flow algorithm.
        """
        super().__init__(id)
        initialized = initial_voltage is not None
        if initial_voltage is None:
            initial_voltage = 0.0
        self.initial_voltage = initial_voltage
        self.geometry = geometry
        self._nominal_voltage: float | None = None
        self._min_voltage_level: float | None = None
        self._max_voltage_level: float | None = None
        if nominal_voltage is not None:
            self.nominal_voltage = nominal_voltage
        if min_voltage_level is not None:
            self.min_voltage_level = min_voltage_level
        if max_voltage_level is not None:
            self.max_voltage_level = max_voltage_level

        self._res_voltage: complex | None = None

        self._n = 2
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
        if self._cy_element is not None:
            self._cy_element.initialize_potentials(np.array([self._initial_voltage / SQRT3, 0], dtype=np.complex128))

    def _res_voltage_getter(self, warning: bool) -> complex:
        if self._fetch_results:
            self._res_voltage = self._cy_element.get_potentials(self._n)[0] * SQRT3
        return self._res_getter(value=self._res_voltage, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_voltage(self) -> Q_[complex]:
        """The load flow result of the bus voltages (V)."""
        return self._res_voltage_getter(warning=True)

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
    def nominal_voltage(self) -> Q_[float] | None:
        """The phase-phase nominal voltage of the bus of the bus (V) if it is set."""
        return None if self._nominal_voltage is None else Q_(self._nominal_voltage, "V")

    @nominal_voltage.setter
    @ureg_wraps(None, (None, "V"))
    def nominal_voltage(self, value: float | Q_[float] | None) -> None:
        if pd.isna(value):
            value = None
        if value is None:
            if self._max_voltage_level is not None or self._min_voltage_level is not None:
                warnings.warn(
                    message=(
                        f"The nominal voltage of the bus {self.id!r} is required to use `min_voltage_level` and "
                        f"`max_voltage_level`."
                    ),
                    category=UserWarning,
                    stacklevel=find_stack_level(),
                )
        else:
            if value <= 0:
                msg = f"The nominal voltage of bus {self.id!r} must be positive. {value} V has been provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
        self._nominal_voltage = value

    @property
    def min_voltage_level(self) -> Q_[float] | None:
        """The minimum voltage level of the bus if it is set."""
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
                        f"The min voltage level of the bus {self.id!r} is useless without a nominal voltage. Please "
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
        """The maximum voltage level of the bus if it is set."""
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
                        f"The max voltage level of the bus {self.id!r} is useless without a nominal voltage. Please "
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
                    or np.isclose(element._nominal_voltage, self._nominal_voltage)
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
                    or np.isclose(element._min_voltage_level, self._min_voltage_level)
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
                    or np.isclose(element._max_voltage_level, self._max_voltage_level)
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
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        geometry = cls._parse_geometry(data.get("geometry"))
        if (initial_voltage := data.get("initial_voltage")) is not None:
            initial_voltage = complex(initial_voltage[0], initial_voltage[1])
        self = cls(
            id=data["id"],
            geometry=geometry,
            initial_voltage=initial_voltage,
            nominal_voltage=data.get("nominal_voltage"),
            min_voltage_level=data.get("min_voltage_level"),
            max_voltage_level=data.get("max_voltage_level"),
        )
        if include_results and "results" in data:
            self._res_voltage = complex(data["results"]["voltage"][0], data["results"]["voltage"][1])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id}
        if self._initialized_by_the_user:
            res["initial_voltage"] = [self._initial_voltage.real, self._initial_voltage.imag]
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        if self.nominal_voltage is not None:
            res["nominal_voltage"] = self.nominal_voltage.magnitude
        if self.min_voltage_level is not None:
            res["min_voltage_level"] = self.min_voltage_level.magnitude
        if self.max_voltage_level is not None:
            res["max_voltage_level"] = self.max_voltage_level.magnitude
        if include_results:
            voltage = self._res_voltage_getter(warning=True)
            res["results"] = {"voltage": [voltage.real, voltage.imag]}
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        voltage = self._res_voltage_getter(warning)
        res = {"id": self.id, "voltage": [voltage.real, voltage.imag]}
        if full:
            res["voltage_level"] = self._res_voltage_level_getter(warning=False)
        return res
