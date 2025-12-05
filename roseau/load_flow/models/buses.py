import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Final, Self

import numpy as np
import pandas as pd
from shapely.geometry.base import BaseGeometry
from typing_extensions import deprecated

from roseau.load_flow.constants import SQRT3
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.terminals import AbstractTerminal
from roseau.load_flow.typing import BoolArray, ComplexArray, ComplexArrayLike1D, FloatArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import deprecate_renamed_parameter, warn_external
from roseau.load_flow_engine.cy_engine import CyBus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from roseau.load_flow.models.grounds import Ground


class Bus(AbstractTerminal[CyBus]):
    """A multi-phase electrical bus."""

    element_type: Final = "bus"

    @deprecate_renamed_parameter(
        old_name="potentials", new_name="initial_potentials", version="0.12.0", category=DeprecationWarning
    )
    def __init__(
        self,
        id: Id,
        *,
        phases: str,
        geometry: BaseGeometry | None = None,
        initial_potentials: ComplexArrayLike1D | None = None,
        nominal_voltage: float | Q_[float] | None = None,
        min_voltage_level: float | Q_[float] | None = None,
        max_voltage_level: float | Q_[float] | None = None,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                A unique ID of the bus in the network buses.

            phases:
                The phases of the bus. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`!allowed_phases`.

            geometry:
                An optional geometry of the bus; a :class:`~shapely.Geometry` that represents the
                x-y coordinates of the bus.

            initial_potentials:
                An optional array-like of initial potentials of each phase of the bus. If given,
                these potentials are used as the starting point of the load flow computation.
                Either complex values (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

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
        """
        super().__init__(id, phases=phases)
        initialized = initial_potentials is not None
        if initial_potentials is None:
            initial_potentials = [0] * len(phases)
        self.initial_potentials = initial_potentials
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

        self._short_circuits: list[dict[str, Any]] = []

        self._initialized = initialized
        self._initialized_by_the_user = initialized  # only used for serialization
        self._cy_element = CyBus(n=self._n, potentials=self._initial_potentials)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r})"

    @property
    @ureg_wraps("V", (None,))
    def initial_potentials(self) -> Q_[ComplexArray]:
        """An array of initial potentials of the bus (V)."""
        return self._initial_potentials

    @initial_potentials.setter
    @ureg_wraps(None, (None, "V"))
    def initial_potentials(self, value: ComplexArrayLike1D) -> None:
        if len(value) != len(self.phases):
            msg = f"Incorrect number of potentials: {len(value)} instead of {len(self.phases)}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_POTENTIALS_SIZE)
        self._initial_potentials: ComplexArray = np.array(value, dtype=np.complex128)
        self._invalidate_network_results()
        self._initialized = True
        self._initialized_by_the_user = True
        if self._cy_initialized:
            self._cy_element.initialize_potentials(self._initial_potentials)

    @property
    @deprecated("'Bus.potentials' is deprecated. It has been renamed to 'initial_potentials'.")
    def potentials(self) -> Q_[ComplexArray]:
        """Deprecated alias to `initial_potentials`."""
        return self.initial_potentials

    @potentials.setter
    @deprecated("'Bus.potentials' is deprecated. It has been renamed to 'initial_potentials'.")
    def potentials(self, value: ComplexArrayLike1D) -> None:
        self.initial_potentials = value

    @property
    def nominal_voltage(self) -> Q_[float] | None:
        """The phase-to-phase nominal voltage of the bus (V) if it is set."""
        return None if self._nominal_voltage is None else Q_(self._nominal_voltage, "V")

    @nominal_voltage.setter
    @ureg_wraps(None, (None, "V"))
    def nominal_voltage(self, value: float | Q_[float] | None) -> None:
        if pd.isna(value):
            value = None
        if value is None:
            if self._max_voltage_level is not None or self._min_voltage_level is not None:
                warn_external(
                    message=(
                        f"The nominal voltage of the bus {self.id!r} is required to use `min_voltage_level` and "
                        f"`max_voltage_level`."
                    ),
                    category=UserWarning,
                )
        else:
            if value <= 0:
                msg = f"The nominal voltage of bus {self.id!r} must be positive. {value} V has been provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
        self._nominal_voltage = value

    @property
    def min_voltage_level(self) -> Q_[float] | None:
        """The minimal voltage level of the bus if it is set."""
        return None if self._min_voltage_level is None else Q_(self._min_voltage_level, "")

    @min_voltage_level.setter
    @ureg_wraps(None, (None, ""))
    def min_voltage_level(self, value: float | Q_[float] | None) -> None:
        if pd.isna(value):
            value = None
        if value is not None:
            if self._max_voltage_level is not None and value > self._max_voltage_level:
                msg = (
                    f"Cannot set min voltage level of bus {self.id!r} to {value} as it is higher than its "
                    f"max voltage ({self._max_voltage_level})."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
            if self._nominal_voltage is None:
                warn_external(
                    message=(
                        f"The min voltage level of the bus {self.id!r} is useless without a nominal voltage. Please "
                        f"define a nominal voltage for this bus."
                    ),
                    category=UserWarning,
                )

        self._min_voltage_level = value

    @property
    def min_voltage(self) -> Q_[float] | None:
        """The minimal voltage of the bus (V) if it is set."""
        return (
            None
            if self._min_voltage_level is None or self._nominal_voltage is None
            else Q_(self._min_voltage_level * self._nominal_voltage, "V")
        )

    @property
    def max_voltage_level(self) -> Q_[float] | None:
        """The maximal voltage level of the bus if it is set."""
        return None if self._max_voltage_level is None else Q_(self._max_voltage_level, "")

    @max_voltage_level.setter
    @ureg_wraps(None, (None, ""))
    def max_voltage_level(self, value: float | Q_[float] | None) -> None:
        if pd.isna(value):
            value = None
        if value is not None:
            if self._min_voltage_level is not None and value < self._min_voltage_level:
                msg = (
                    f"Cannot set max voltage level of bus {self.id!r} to {value} as it is lower than its "
                    f"min voltage ({self._min_voltage_level})."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
            if self._nominal_voltage is None:
                warn_external(
                    message=(
                        f"The max voltage level of the bus {self.id!r} is useless without a nominal voltage. Please "
                        f"define a nominal voltage for this bus."
                    ),
                    category=UserWarning,
                )
        self._max_voltage_level = value

    @property
    def max_voltage(self) -> Q_[float] | None:
        """The maximal voltage of the bus (V) if it is set."""
        return (
            None
            if self._max_voltage_level is None or self._nominal_voltage is None
            else Q_(self._max_voltage_level * self._nominal_voltage, "V")
        )

    @property
    def short_circuits(self) -> list[dict[str, Any]]:
        """Return the list of short-circuits of this bus."""
        return self._short_circuits[:]  # return a copy as users should not modify the list directly

    def add_short_circuit(self, *phases: str, ground: "Ground | None" = None) -> None:
        """Add a short-circuit by connecting multiple phases together optionally with a ground.

        Args:
            phases:
                The phases to connect.

            ground:
                If a ground is given, the phases will also be connected to the ground.
        """
        from roseau.load_flow import CurrentLoad, PowerLoad

        for phase in phases:
            if phase not in self.phases:
                msg = f"Phase {phase!r} is not in the phases {set(self.phases)} of bus {self.id!r}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        if not phases or (len(phases) == 1 and ground is None):
            msg = f"For the short-circuit on bus {self.id!r}, expected at least two phases or a phase and a ground."
            if not phases:
                msg += " No phase was given."
            else:
                msg += f" Only phase {phases[0]!r} is given."

            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        duplicates = [item for item in set(phases) if phases.count(item) > 1]
        if duplicates:
            msg = f"For the short-circuit on bus {self.id!r}, some phases are duplicated: {duplicates}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        for element in self._connected_elements:
            if isinstance(element, (PowerLoad, CurrentLoad)):
                msg = (
                    f"A {element.type} load {element.id!r} is already connected on bus {self.id!r}. "
                    f"It makes the short-circuit calculation impossible."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)

        self._short_circuits.append({"phases": list(phases), "ground": ground.id if ground is not None else None})

        if self.network is not None:
            self.network._valid = False

        phases_index = np.array([self.phases.index(p) for p in phases], dtype=np.int32)
        self._cy_element.connect_ports(phases_index)

        if ground is not None:
            self._connect(ground)
            self._cy_element.connect(ground._cy_element, [(phases_index[0], 0)])

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
        from roseau.load_flow.models.lines import Line
        from roseau.load_flow.models.switches import Switch

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
    # Results
    #
    def _res_voltage_levels_getter(self, warning: bool) -> FloatArray | None:
        if self._nominal_voltage is None:
            return None
        voltages_abs = abs(self._res_voltages_getter(warning=warning))
        if "n" in self.phases:
            return SQRT3 * voltages_abs / self._nominal_voltage
        else:
            return voltages_abs / self._nominal_voltage

    def _res_voltage_levels_pp_getter(self, warning: bool) -> FloatArray | None:
        if self._nominal_voltage is None:
            return None
        voltages_abs = abs(self._res_voltages_pp_getter(warning=warning))
        return voltages_abs / self._nominal_voltage

    def _res_voltage_levels_pn_getter(self, warning: bool) -> FloatArray | None:
        if self._nominal_voltage is None:
            return None
        voltages_abs = abs(self._res_voltages_pn_getter(warning=warning))
        return SQRT3 * voltages_abs / self._nominal_voltage

    @property
    def res_voltage_levels(self) -> Q_[FloatArray] | None:
        """The load flow result of the bus voltage levels (p.u.)."""
        voltage_levels = self._res_voltage_levels_getter(warning=True)
        return None if voltage_levels is None else Q_(voltage_levels, "")

    @property
    def res_voltage_levels_pp(self) -> Q_[FloatArray] | None:
        """The load flow result of the bus's phase-to-phase voltage levels (p.u.).

        Raises an error if the element has only one phase.
        """
        voltage_levels = self._res_voltage_levels_pp_getter(warning=True)
        return None if voltage_levels is None else Q_(voltage_levels, "")

    @property
    def res_voltage_levels_pn(self) -> Q_[FloatArray] | None:
        """The load flow result of the bus's phase-to-neutral voltage levels (p.u.).

        Raises an error if the element does not have a neutral.
        """
        voltage_levels = self._res_voltage_levels_pn_getter(warning=True)
        return None if voltage_levels is None else Q_(voltage_levels, "")

    @property
    def res_violated(self) -> BoolArray | None:
        """Whether the bus has voltage limits violations.

        Returns ``None`` if the bus has no voltage limits are not set.
        """
        u_min = self._min_voltage_level
        u_max = self._max_voltage_level
        if u_min is None and u_max is None:
            return None
        voltage_levels = self._res_voltage_levels_getter(warning=True)
        if voltage_levels is None:
            return None
        violated = np.full_like(voltage_levels, fill_value=False, dtype=np.bool_)
        if u_min is not None:
            violated |= voltage_levels < u_min
        if u_max is not None:
            violated |= voltage_levels > u_max
        return violated

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        if (initial_potentials := data.get("initial_potentials")) is not None:
            initial_potentials = [complex(*v) for v in initial_potentials]
        self = cls(
            id=data["id"],
            phases=data["phases"],
            geometry=cls._parse_geometry(data.get("geometry")),
            initial_potentials=initial_potentials,
            nominal_voltage=data.get("nominal_voltage"),
            min_voltage_level=data.get("min_voltage_level"),
            max_voltage_level=data.get("max_voltage_level"),
        )
        self._parse_results_from_dict(data, include_results=include_results)
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results=include_results)
        if self._initialized_by_the_user:
            data["initial_potentials"] = [[v.real, v.imag] for v in self._initial_potentials.tolist()]
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
            voltage_levels = self._res_voltage_levels_getter(warning=False)
            results["voltage_levels"] = None if voltage_levels is None else voltage_levels.tolist()
        return results
