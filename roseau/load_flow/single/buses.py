import logging
from collections.abc import Iterator
from typing import Any

import numpy as np
import pandas as pd
from shapely.geometry.base import BaseGeometry
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.single.core import Element
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils.graph import propagate_limits
from roseau.load_flow_engine.cy_engine import CyBus

logger = logging.getLogger(__name__)


class Bus(Element):
    """A multi-phase electrical bus."""

    def __init__(
        self,
        id: Id,
        *,
        geometry: BaseGeometry | None = None,
        potential: float | None = None,
        min_voltage: float | None = None,
        max_voltage: float | None = None,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                A unique ID of the bus in the network buses.

            geometry:
                An optional geometry of the bus; a :class:`~shapely.Geometry` that represents the
                x-y coordinates of the bus.

            min_voltage:
                An optional minimum voltage of the bus (V). It is not used in the load flow.
                It must be a phase-neutral voltage if the bus has a neutral, phase-phase otherwise.
                Either a float (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            max_voltage:
                An optional maximum voltage of the bus (V). It is not used in the load flow.
                It must be a phase-neutral voltage if the bus has a neutral, phase-phase otherwise.
                Either a float (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.
        """
        super().__init__(id)
        initialized = potential is not None
        if potential is None:
            potential = 0.0
        self.potential = potential
        self.geometry = geometry
        self._min_voltage: float | None = None
        self._max_voltage: float | None = None
        if min_voltage is not None:
            self.min_voltage = min_voltage
        if max_voltage is not None:
            self.max_voltage = max_voltage

        self._res_potentials: ComplexArray | None = None
        self._short_circuits: list[dict[str, Any]] = []

        self._n = 2
        self._initialized = initialized
        self._initialized_by_the_user = initialized  # only used for serialization
        self._cy_element = CyBus(n=self._n, potentials=np.array([0, self._potential], dtype=np.complex128))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    @property
    @ureg_wraps("V", (None,))
    def potential(self) -> Q_[ComplexArray]:
        """An array of initial potentials of the bus (V)."""
        return self._potential

    @potential.setter
    @ureg_wraps(None, (None, "V"))
    def potential(self, value: float) -> None:
        self._potential = value
        self._invalidate_network_results()
        self._initialized = True
        self._initialized_by_the_user = True
        if self._cy_element is not None:
            self._cy_element.initialize_potentials(np.array([self._potential, 0], dtype=np.complex128))

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._res_potentials = self._cy_element.get_potentials(self._n)
        return self._res_getter(value=self._res_potentials, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potential(self) -> Q_[float]:
        """The load flow result of the bus potentials (V)."""
        return self._res_potentials_getter(warning=True)[0]

    def _res_voltages_getter(self, warning: bool, potentials: ComplexArray | None = None) -> ComplexArray:
        if potentials is None:
            potentials = np.array(self._res_potentials_getter(warning=warning))
        return np.array([potentials[0] - potentials[1]])

    @property
    @ureg_wraps("V", (None,))
    def res_voltage(self) -> Q_[complex]:
        """The load flow result of the bus voltages (V).

        If the bus has a neutral, the voltages are phase-neutral voltages for existing phases in
        the order ``[Van, Vbn, Vcn]``. If the bus does not have a neutral, phase-phase voltages
        are returned in the order ``[Vab, Vbc, Vca]``.
        """
        return self._res_voltages_getter(warning=True)[0]

    @property
    def min_voltage(self) -> Q_[float] | None:
        """The minimum voltage of the bus (V) if it is set."""
        return None if self._min_voltage is None else Q_(self._min_voltage, "V")

    @min_voltage.setter
    @ureg_wraps(None, (None, "V"))
    def min_voltage(self, value: float | Q_[float] | None) -> None:
        if value is not None and self._max_voltage is not None and value > self._max_voltage:
            msg = (
                f"Cannot set min voltage of bus {self.id!r} to {value} V as it is higher than its "
                f"max voltage ({self._max_voltage} V)."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
        if pd.isna(value):
            value = None
        self._min_voltage = value

    @property
    def max_voltage(self) -> Q_[float] | None:
        """The maximum voltage of the bus (V) if it is set."""
        return None if self._max_voltage is None else Q_(self._max_voltage, "V")

    @max_voltage.setter
    @ureg_wraps(None, (None, "V"))
    def max_voltage(self, value: float | Q_[float] | None) -> None:
        if value is not None and self._min_voltage is not None and value < self._min_voltage:
            msg = (
                f"Cannot set max voltage of bus {self.id!r} to {value} V as it is lower than its "
                f"min voltage ({self._min_voltage} V)."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
        if pd.isna(value):
            value = None
        self._max_voltage = value

    @property
    def res_violated(self) -> bool | None:
        """Whether the bus has voltage limits violations.

        Returns ``None`` if the bus has no voltage limits are not set.
        """
        if self._min_voltage is None and self._max_voltage is None:
            return None
        voltages = abs(self._res_voltages_getter(warning=True))
        if self._min_voltage is None:
            assert self._max_voltage is not None
            return float(max(voltages)) > self._max_voltage
        elif self._max_voltage is None:
            return float(min(voltages)) < self._min_voltage
        else:
            return float(min(voltages)) < self._min_voltage or float(max(voltages)) > self._max_voltage

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
        propagate_limits(initial_bus=self, force=force)

    def get_connected_buses(self) -> Iterator[Id]:
        """Get IDs of all the buses galvanically connected to this bus.

        These are all the buses connected via one or more lines or switches to this bus.
        """
        from roseau.load_flow.models.lines import Line
        from roseau.load_flow.models.switches import Switch

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
        if (potential := data.get("potential")) is not None:
            potential = complex(potential[0], potential[1])
        self = cls(
            id=data["id"],
            geometry=geometry,
            potential=potential,
            min_voltage=data.get("min_voltage"),
            max_voltage=data.get("max_voltage"),
        )
        if include_results and "results" in data:
            self._res_potentials = np.array(
                [complex(data["results"]["potential"][0], data["results"]["potential"][1])], dtype=np.complex128
            )
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id}
        if self._initialized_by_the_user:
            res["potential"] = [self._potential.real, self._potential.imag]
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        if self.min_voltage is not None:
            res["min_voltage"] = self.min_voltage.magnitude
        if self.max_voltage is not None:
            res["max_voltage"] = self.max_voltage.magnitude
        if include_results:
            potentials = self._res_potentials_getter(warning=True)
            res["results"] = {"potentials": [[v.real, v.imag] for v in potentials]}
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        potentials = np.array(self._res_potentials_getter(warning))
        res = {
            "id": self.id,
            "potential": [[v.real, v.imag] for v in potentials],
        }
        if full:
            res["voltages"] = [
                [v.real, v.imag] for v in self._res_voltages_getter(warning=False, potentials=potentials)
            ]
        return res
