import logging
import warnings
from collections.abc import Iterator
from functools import cached_property
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd
from shapely.geometry.base import BaseGeometry
from typing_extensions import Self

from roseau.load_flow.converters import _calculate_voltages, calculate_voltage_phases, phasor_to_sym
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import ComplexArray, ComplexArrayLike1D, FloatArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils._exceptions import find_stack_level
from roseau.load_flow_engine.cy_engine import CyBus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from roseau.load_flow.models.grounds import Ground


class Bus(Element):
    """A multi-phase electrical bus."""

    allowed_phases: Final = frozenset({"ab", "bc", "ca", "an", "bn", "cn", "abn", "bcn", "can", "abc", "abcn"})
    """The allowed phases for a bus are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"``
    - P-P or P-P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"abn"``, ``"bcn"``, ``"can"``
    - P-N: ``"an"``, ``"bn"``, ``"cn"``
    """

    def __init__(
        self,
        id: Id,
        *,
        phases: str,
        geometry: BaseGeometry | None = None,
        potentials: ComplexArrayLike1D | None = None,
        nominal_voltage: float | None = None,
        min_voltage_level: float | None = None,
        max_voltage_level: float | None = None,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                A unique ID of the bus in the network buses.

            phases:
                The phases of the bus. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`.allowed_phases`.

            geometry:
                An optional geometry of the bus; a :class:`~shapely.Geometry` that represents the
                x-y coordinates of the bus.

            potentials:
                An optional array-like of initial potentials of each phase of the bus. If given,
                these potentials are used as the starting point of the load flow computation.
                Either complex values (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

            nominal_voltage:
                An optional nominal voltage for the bus (V). It is not used in the load flow.
                It is always a phase-phase voltage. It can be a float (V) or a
                :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            min_voltage_level:
                An optional minimal voltage of the bus (%). It is not used in the load flow.
                It must be a percentage of the `nominal_voltage`. If provided, the nominal voltage becomes mandatory.
                Either a float (unitless) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            max_voltage_level:
                An optional maximal voltage of the bus (%). It is not used in the load flow.
                It must be a percentage of the `nominal_voltage`. If provided, the nominal voltage becomes mandatory.
                Either a float (unitless) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.
        """
        super().__init__(id)
        self._check_phases(id, phases=phases)
        self._phases = phases
        initialized = potentials is not None
        if potentials is None:
            potentials = [0] * len(phases)
        self.potentials = potentials
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

        self._res_potentials: ComplexArray | None = None
        self._short_circuits: list[dict[str, Any]] = []

        self._n = len(self._phases)
        self._initialized = initialized
        self._initialized_by_the_user = initialized  # only used for serialization
        self._cy_element = CyBus(n=self._n, potentials=self._potentials)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r})"

    @property
    def phases(self) -> str:
        """The phases of the bus."""
        return self._phases

    @property
    @ureg_wraps("V", (None,))
    def potentials(self) -> Q_[ComplexArray]:
        """An array of initial potentials of the bus (V)."""
        return self._potentials

    @potentials.setter
    @ureg_wraps(None, (None, "V"))
    def potentials(self, value: ComplexArrayLike1D) -> None:
        if len(value) != len(self.phases):
            msg = f"Incorrect number of potentials: {len(value)} instead of {len(self.phases)}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_POTENTIALS_SIZE)
        self._potentials = np.array(value, dtype=np.complex128)
        self._invalidate_network_results()
        self._initialized = True
        self._initialized_by_the_user = True
        if self._cy_element is not None:
            self._cy_element.initialize_potentials(self._potentials)

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._res_potentials = self._cy_element.get_potentials(self._n)
        return self._res_getter(value=self._res_potentials, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potentials(self) -> Q_[ComplexArray]:
        """The load flow result of the bus potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(self, warning: bool, potentials: ComplexArray | None = None) -> ComplexArray:
        if potentials is None:
            potentials = np.array(self._res_potentials_getter(warning=warning))
        return _calculate_voltages(potentials, self.phases)

    @property
    @ureg_wraps("V", (None,))
    def res_voltages(self) -> Q_[ComplexArray]:
        """The load flow result of the bus voltages (V).

        If the bus has a neutral, the voltages are phase-neutral voltages for existing phases in
        the order ``[Van, Vbn, Vcn]``. If the bus does not have a neutral, phase-phase voltages
        are returned in the order ``[Vab, Vbc, Vca]``.
        """
        return self._res_voltages_getter(warning=True)

    @property
    def res_voltage_levels(self) -> Q_[FloatArray] | None:
        """The load flow result of the bus voltage levels (unitless)."""
        if self._nominal_voltage is None:
            return None
        voltages_abs = abs(self._res_voltages_getter(warning=True))
        if "n" in self.phases:
            return Q_(np.sqrt(3) * voltages_abs / self._nominal_voltage, "")
        else:
            return Q_(voltages_abs / self._nominal_voltage, "")

    @cached_property
    def voltage_phases(self) -> list[str]:
        """The phases of the voltages."""
        return calculate_voltage_phases(self.phases)

    def _get_potentials_of(self, phases: str, warning: bool) -> ComplexArray:
        """Get the potentials of the given phases."""
        potentials = self._res_potentials_getter(warning)
        return np.array([potentials[self.phases.index(p)] for p in phases])

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
                warnings.warn(
                    message=(
                        f"The min voltage level of the bus {self.id!r} is useless without a nominal voltage. Please "
                        f"define a nominal voltage for this bus."
                    ),
                    category=UserWarning,
                    stacklevel=find_stack_level(),
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
                warnings.warn(
                    message=(
                        f"The max voltage level of the bus {self.id!r} is useless without a nominal voltage. Please "
                        f"define a nominal voltage for this bus."
                    ),
                    category=UserWarning,
                    stacklevel=find_stack_level(),
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
    def res_violated(self) -> bool | None:
        """Whether the bus has voltage limits violations.

        Returns ``None`` if the bus has no voltage limits are not set.
        """
        if (self._min_voltage_level is None and self._max_voltage_level is None) or self._nominal_voltage is None:
            return None
        voltages = abs(self._res_voltages_getter(warning=True))
        if "n" in self.phases:
            voltages_level = np.sqrt(3) * voltages / self._nominal_voltage
        else:
            voltages_level = voltages / self._nominal_voltage
        if self._min_voltage_level is None:
            assert self._max_voltage_level is not None
            return float(max(voltages_level)) > self._max_voltage_level
        elif self._max_voltage_level is None:
            return float(min(voltages_level)) < self._min_voltage_level
        else:
            return (
                float(min(voltages_level)) < self._min_voltage_level
                or float(max(voltages_level)) > self._max_voltage_level
            )

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

    @ureg_wraps("percent", (None,))
    def res_voltage_unbalance(self) -> Q_[float]:
        """Calculate the voltage unbalance on this bus according to the IEC definition.

        Voltage Unbalance Factor:

        :math:`VUF = \\dfrac{|V_{\\mathrm{n}}|}{|V_{\\mathrm{p}}|} \\times 100 \\, (\\%)`

        Where :math:`V_{\\mathrm{n}}` is the negative-sequence voltage and :math:`V_{\\mathrm{p}}` is the
        positive-sequence voltage.
        """
        # https://std.iec.ch/terms/terms.nsf/3385f156e728849bc1256e8c00278ad2/771c5188e62fade5c125793a0043f2a5?OpenDocument
        if self.phases not in {"abc", "abcn"}:
            msg = f"Voltage unbalance is only available for 3-phases buses, bus {self.id!r} has phases {self.phases!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        # We use the potentials here which is equivalent to using the "line to neutral" voltages as
        # defined by the standard. The standard also has this note:
        # NOTE 1 Phase-to-phase voltages may also be used instead of line to neutral voltages.
        potentials = self._res_potentials_getter(warning=True)
        _, vp, vn = phasor_to_sym(potentials[:3])  # (0, +, -)
        return abs(vn) / abs(vp) * 100

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        geometry = cls._parse_geometry(data.get("geometry"))
        if (potentials := data.get("potentials")) is not None:
            potentials = [complex(v[0], v[1]) for v in potentials]
        self = cls(
            id=data["id"],
            phases=data["phases"],
            geometry=geometry,
            potentials=potentials,
            nominal_voltage=data.get("nominal_voltage"),
            min_voltage_level=data.get("min_voltage_level"),
            max_voltage_level=data.get("max_voltage_level"),
        )
        if include_results and "results" in data:
            self._res_potentials = np.array(
                [complex(v[0], v[1]) for v in data["results"]["potentials"]], dtype=np.complex128
            )
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id, "phases": self.phases}
        if self._initialized_by_the_user:
            res["potentials"] = [[v.real, v.imag] for v in self._potentials]
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        if self.nominal_voltage is not None:
            res["nominal_voltage"] = self.nominal_voltage.magnitude
        if self.min_voltage_level is not None:
            res["min_voltage_level"] = self.min_voltage_level.magnitude
        if self.max_voltage_level is not None:
            res["max_voltage_level"] = self.max_voltage_level.magnitude
        if include_results:
            potentials = self._res_potentials_getter(warning=True)
            res["results"] = {"potentials": [[v.real, v.imag] for v in potentials]}
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        potentials = np.array(self._res_potentials_getter(warning))
        res = {
            "id": self.id,
            "phases": self.phases,
            "potentials": [[v.real, v.imag] for v in potentials],
        }
        if full:
            res["voltages"] = [
                [v.real, v.imag] for v in self._res_voltages_getter(warning=False, potentials=potentials)
            ]
        return res

    def add_short_circuit(self, *phases: str, ground: "Ground | None" = None) -> None:
        """Add a short-circuit by connecting multiple phases together optionally with a ground.

        Args:
            phases:
                The phases to connect.

            ground:
                If a ground is given, the phases will also be connected to the ground.
        """
        from roseau.load_flow import PowerLoad

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
            if isinstance(element, PowerLoad):
                msg = (
                    f"A power load {element.id!r} is already connected on bus {self.id!r}. "
                    f"It makes the short-circuit calculation impossible."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)

        self._short_circuits.append({"phases": list(phases), "ground": ground.id if ground is not None else None})

        if self.network is not None:
            self.network._valid = False

        phases_index = np.array([self.phases.index(p) for p in phases], dtype=np.int32)
        self._cy_element.connect_ports(phases_index, len(phases))

        if ground is not None:
            self._cy_element.connect(ground._cy_element, [(phases_index[0], 0)])

    @property
    def short_circuits(self) -> list[dict[str, Any]]:
        """Return the list of short-circuits of this bus."""
        return self._short_circuits[:]  # return a copy as users should not modify the list directly
