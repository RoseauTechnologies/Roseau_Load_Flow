import logging
import warnings
from abc import ABC
from functools import cached_property
from typing import ClassVar, Final, Literal

import numpy as np

from roseau.load_flow.converters import _PHASE_SIZES, _calculate_voltages, calculate_voltage_phases
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.typing import ComplexArray, ComplexScalarOrArrayLike1D, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils.constants import PositiveSequence
from roseau.load_flow_engine.cy_engine import (
    CyAdmittanceLoad,
    CyCurrentLoad,
    CyDeltaAdmittanceLoad,
    CyDeltaCurrentLoad,
    CyDeltaFlexibleLoad,
    CyDeltaPowerLoad,
    CyFlexibleLoad,
    CyPowerLoad,
)

logger = logging.getLogger(__name__)


class AbstractLoad(Element, ABC):
    """An abstract class of an electric load.

    The subclasses of this class can be used to depict:
        * star-connected loads using a `phases` constructor argument containing `"n"`
        * delta-connected loads using a `phases` constructor argument not containing `"n"`
    """

    type: ClassVar[Literal["power", "current", "impedance"]]

    allowed_phases: Final = Bus.allowed_phases
    """The allowed phases for a load are the same as for a :attr:`bus<Bus.allowed_phases>`."""

    def __init__(self, id: Id, bus: Bus, *, phases: str | None = None, connect_neutral: bool | None = None) -> None:
        """AbstractLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to be
                connected to buses that don't have a neutral if ``connect_neutral`` is not set to
                ``True``.

            connect_neutral:
                Specifies whether the load's neutral should be connected to the bus's neutral or
                left floating. By default, the load's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the load's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        if type(self) is AbstractLoad:
            raise TypeError("Can't instantiate abstract class AbstractLoad")
        super().__init__(id)
        if connect_neutral is not None:
            connect_neutral = bool(connect_neutral)  # to allow np.bool

        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id=id, phases=phases)
            # Also check they are in the bus phases
            phases_not_in_bus = set(phases) - set(bus.phases)
            # "n" is allowed to be absent from the bus only if the load has more than 2 phases
            missing_ok = phases_not_in_bus == {"n"} and len(phases) > 2 and not connect_neutral
            if phases_not_in_bus and not missing_ok:
                msg = (
                    f"Phases {sorted(phases_not_in_bus)} of load {id!r} are not in bus {bus.id!r} "
                    f"phases {bus.phases!r}"
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        if connect_neutral and "n" not in phases:
            warnings.warn(
                message=f"Neutral connection requested for load {id!r} with no neutral phase",
                category=UserWarning,
                stacklevel=3,
            )
            connect_neutral = None
        self._connect(bus)

        self._phases = phases
        self._bus = bus
        self._n = len(self._phases)
        self._symbol = {"power": "S", "current": "I", "impedance": "Z"}[self.type]
        self._size = _PHASE_SIZES[phases]
        self._connect_neutral = connect_neutral

        # Results
        self._res_currents: ComplexArray | None = None
        self._res_potentials: ComplexArray | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"<{type(self).__name__}: id={self.id!r}, bus={bus_id!r}, phases={self.phases!r}>"

    @property
    def phases(self) -> str:
        """The phases of the load."""
        return self._phases

    @property
    def bus(self) -> Bus:
        """The bus of the load."""
        return self._bus

    @property
    def is_flexible(self) -> bool:
        """Whether the load is flexible or not. Only :class:`PowerLoad` can be flexible."""
        return False

    @cached_property
    def has_floating_neutral(self) -> bool:
        """Does this load have a floating neutral?"""
        if "n" not in self._phases:
            return False
        if self._connect_neutral is False:
            return True
        if self._connect_neutral is None:
            return "n" not in self.bus.phases
        return False

    @cached_property
    def voltage_phases(self) -> list[str]:
        """The phases of the load voltages."""
        return calculate_voltage_phases(self.phases)

    def _refresh_results(self) -> None:
        self._res_currents = self._cy_element.get_currents(self._n)
        self._res_potentials = self._cy_element.get_potentials(self._n)

    def _res_currents_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps("A", (None,))
    def res_currents(self) -> Q_[ComplexArray]:
        """The load flow result of the load currents (A)."""
        return self._res_currents_getter(warning=True)

    def _validate_value(self, value: ComplexScalarOrArrayLike1D) -> ComplexArray:
        if np.isscalar(value):
            if self.type == "current":
                if self._size == 1:
                    values = [value]
                elif self._size == 2:
                    values = [value, -value]
                else:
                    assert self._size == 3
                    values = value * PositiveSequence
            else:
                values = [value for _ in range(self._size)]
        else:
            values = value
        values = np.array(values, dtype=np.complex128)
        if len(values) != self._size:
            msg = f"Incorrect number of {self.type}s: {len(values)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{self._symbol}_SIZE"])
        # A load cannot have any zero impedance
        if self.type == "impedance" and np.isclose(values, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return values

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_potentials, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potentials(self) -> Q_[ComplexArray]:
        """The load flow result of the load potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(self, warning: bool) -> ComplexArray:
        potentials = self._res_potentials_getter(warning)
        return _calculate_voltages(potentials, self.phases)

    @property
    @ureg_wraps("V", (None,))
    def res_voltages(self) -> Q_[ComplexArray]:
        """The load flow result of the load voltages (V)."""
        return self._res_voltages_getter(warning=True)

    def _res_powers_getter(
        self, warning: bool, currents: ComplexArray | None = None, potentials: ComplexArray | None = None
    ) -> ComplexArray:
        if currents is None:
            currents = self._res_currents_getter(warning=warning)
            warning = False  # we warn only one
        if potentials is None:
            potentials = self._res_potentials_getter(warning=warning)
        return potentials * currents.conj()

    @property
    @ureg_wraps("VA", (None,))
    def res_powers(self) -> Q_[ComplexArray]:
        """The load flow result of the "line powers" flowing into the load (VA)."""
        return self._res_powers_getter(warning=True)

    def _cy_connect(self):
        connections = []
        bus_phases = self.bus.phases.removesuffix("n") if self.has_floating_neutral else self.bus.phases
        for i, phase in enumerate(bus_phases):
            if phase in self.phases:
                j = self.phases.index(phase)
                connections.append((i, j))
        self.bus._cy_element.connect(self._cy_element, connections)

    #
    # Disconnect
    #
    def disconnect(self) -> None:
        """Disconnect this load from the network. It cannot be used afterwards."""
        self._disconnect()
        self._bus = None

    def _raise_disconnected_error(self) -> None:
        """Raise an error if the load is disconnected."""
        if self.bus is None:
            msg = f"The load {self.id!r} is disconnected and cannot be used anymore."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> "AbstractLoad":
        load_type: Literal["power", "current", "impedance"] = data["type"]
        if load_type == "power":
            powers = [complex(s[0], s[1]) for s in data["powers"]]
            if (fp_data_list := data.get("flexible_params")) is not None:
                fp = [
                    FlexibleParameter.from_dict(data=fp_dict, include_results=include_results)
                    for fp_dict in fp_data_list
                ]
            else:
                fp = None
            self = PowerLoad(
                id=data["id"],
                bus=data["bus"],
                powers=powers,
                phases=data["phases"],
                flexible_params=fp,
                connect_neutral=data["connect_neutral"],
            )
        elif load_type == "current":
            currents = [complex(i[0], i[1]) for i in data["currents"]]
            self = CurrentLoad(id=data["id"], bus=data["bus"], currents=currents, phases=data["phases"])
        elif load_type == "impedance":
            impedances = [complex(z[0], z[1]) for z in data["impedances"]]
            self = ImpedanceLoad(
                id=data["id"],
                bus=data["bus"],
                impedances=impedances,
                phases=data["phases"],
                connect_neutral=data["connect_neutral"],
            )
        else:
            msg = f"Unknown load type {load_type!r} for load {data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        if include_results and "results" in data:
            self._res_currents = np.array(
                [complex(i[0], i[1]) for i in data["results"]["currents"]], dtype=np.complex128
            )
            self._res_potentials = np.array(
                [complex(i[0], i[1]) for i in data["results"]["potentials"]], dtype=np.complex128
            )
            if "flexible_powers" in data["results"]:
                self._res_flexible_powers = np.array(
                    [complex(p[0], p[1]) for p in data["results"]["flexible_powers"]], dtype=np.complex128
                )

            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        complex_array = getattr(self, f"_{self.type}s")
        res = {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            "type": self.type,
            f"{self.type}s": [[value.real, value.imag] for value in complex_array],
            "connect_neutral": self._connect_neutral,
        }
        if include_results:
            currents = self._res_currents_getter(warning=True)
            res["results"] = {"currents": [[i.real, i.imag] for i in currents]}
            potentials = self._res_potentials_getter(warning=True)
            res["results"]["potentials"] = [[v.real, v.imag] for v in potentials]
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents = self._res_currents_getter(warning)
        results = {
            "id": self.id,
            "phases": self.phases,
            "type": self.type,
            "currents": [[i.real, i.imag] for i in currents],
        }
        potentials = self._res_potentials_getter(warning=False)
        results["potentials"] = [[v.real, v.imag] for v in potentials]
        if full:
            powers = self._res_powers_getter(warning=False, currents=currents, potentials=potentials)
            results["powers"] = [[s.real, s.imag] for s in powers]
        return results


class PowerLoad(AbstractLoad):
    """A constant power load."""

    type: Final = "power"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        powers: ComplexScalarOrArrayLike1D,
        phases: str | None = None,
        flexible_params: list[FlexibleParameter] | None = None,
        connect_neutral: bool | None = None,
    ) -> None:
        """PowerLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            powers:
                A single power value or an array-like of power values for each phase component.
                Either complex values (VA) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

                When a scalar value is provided, it creates a balanced load with the same power for
                each phase. The scalar value passed is assumed to be the power of each component of
                the load, not the total multi-phase power. To create an unbalanced load, provide a
                vector of power values with the same length as the number of components of the load.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to be
                connected to buses that don't have a neutral if ``connect_neutral`` is not set to
                ``True``.

            flexible_params:
                A list of :class:`FlexibleParameters` object, one for each phase. When provided,
                the load is considered as flexible (or controllable) and the parameters are used
                to compute the flexible power of the load.

            connect_neutral:
                Specifies whether the load's neutral should be connected to the bus's neutral or
                left floating. By default, the load's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the load's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        super().__init__(id=id, bus=bus, phases=phases, connect_neutral=connect_neutral)

        if bus.short_circuits:
            msg = (
                f"The power load {self.id!r} is connected on bus {bus.id!r} that already has a short-circuit. "
                f"It makes the short-circuit calculation impossible."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)
        if flexible_params and len(flexible_params) != self._size:
            msg = f"Incorrect number of parameters: {len(flexible_params)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)

        self._flexible_params = flexible_params
        self.powers = powers
        self._res_flexible_powers: ComplexArray | None = None

        if self.is_flexible:
            cy_parameters = np.array([p._cy_fp for p in flexible_params])  # type: ignore
            if self.phases == "abc":
                self._cy_element = CyDeltaFlexibleLoad(n=self._n, powers=self._powers, parameters=cy_parameters)
            else:
                self._cy_element = CyFlexibleLoad(n=self._n, powers=self._powers, parameters=cy_parameters)
        else:
            if self.phases == "abc":
                self._cy_element = CyDeltaPowerLoad(n=self._n, powers=self._powers)
            else:
                self._cy_element = CyPowerLoad(n=self._n, powers=self._powers)
        self._cy_connect()

    @property
    def flexible_params(self) -> list[FlexibleParameter] | None:
        return self._flexible_params

    @property
    def is_flexible(self) -> bool:
        return self._flexible_params is not None

    @property
    @ureg_wraps("VA", (None,))
    def powers(self) -> Q_[ComplexArray]:
        """The powers of the load (VA).

        Setting the powers will update the load's power values and invalidate the network results.
        """
        return self._powers

    @powers.setter
    @ureg_wraps(None, (None, "VA"))
    def powers(self, value: ComplexScalarOrArrayLike1D) -> None:
        value = self._validate_value(value)
        if self._flexible_params is not None:
            for power, fp in zip(value, self._flexible_params, strict=True):
                if fp.control_p.type == "constant" and fp.control_q.type == "constant":
                    continue  # No checks for this case
                if abs(power) > fp._s_max:
                    msg = f"The power is greater than the parameter s_max for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if power.imag < fp._q_min:
                    msg = f"The reactive power is lower than the parameter q_min for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if power.imag > fp._q_max:
                    msg = f"The reactive power is greater than the parameter q_max for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if fp.control_p.type == "p_max_u_production" and power.real > 0:
                    msg = f"There is a production control but a positive power for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if fp.control_p.type == "p_max_u_consumption" and power.real < 0:
                    msg = f"There is a consumption control but a negative power for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
        self._powers = value
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_powers(self._powers)

    def _refresh_results(self) -> None:
        super()._refresh_results()
        if self.is_flexible:
            self._res_flexible_powers = self._cy_element.get_powers(self._n)

    def _res_flexible_powers_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_flexible_powers, warning=warning)

    @property
    @ureg_wraps("VA", (None,))
    def res_flexible_powers(self) -> Q_[ComplexArray]:
        """The load flow result of the load flexible powers (VA).

        This property is only available for flexible loads.

        It returns the powers actually consumed or produced by each component of the load instead
        of the "line powers" flowing into the load connection points (as the :meth:`res_powers`
        property does). The two properties are the same for Wye-connected loads but are different
        for Delta-connected loads.
        """
        if not self.is_flexible:
            msg = f"The load {self.id!r} is not flexible and does not have flexible powers"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        return self._res_flexible_powers_getter(warning=True)

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        res = super()._to_dict(include_results=include_results)
        if self.flexible_params is not None:
            res["flexible_params"] = [fp.to_dict(include_results=include_results) for fp in self.flexible_params]
            if include_results:
                res["results"]["flexible_powers"] = [
                    [s.real, s.imag] for s in self._res_flexible_powers_getter(warning=False)
                ]
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        if self.is_flexible:
            return {
                **super()._results_to_dict(warning=warning, full=full),
                "flexible_powers": [[s.real, s.imag] for s in self._res_flexible_powers_getter(False)],
            }
        else:
            return super()._results_to_dict(warning=warning, full=full)


class CurrentLoad(AbstractLoad):
    """A constant current load."""

    type: Final = "current"

    def __init__(self, id: Id, bus: Bus, *, currents: ComplexScalarOrArrayLike1D, phases: str | None = None) -> None:
        """CurrentLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            currents:
                A single current value or an array-like of current values for each phase component.
                Either complex values (A) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

                When a scalar value is provided, it is interpreted as the first value of the load
                currents vector to create a balanced load. The other values are calculated based on
                the number of phases of the load. For a single-phase load, the passed scalar value
                is used. For a two-phase load, the second current value is the negative of the first
                value (180° phase shift). For a three-phase load, the second and third current
                values are obtained by rotating the first value by -120° and 120°, respectively
                (120° phase shift clockwise).

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus.
        """
        super().__init__(id=id, phases=phases, bus=bus)
        if self.has_floating_neutral:
            msg = (
                f"Constant current loads cannot have a floating neutral. {type(self).__name__} "
                f"{id!r} has phases {phases!r} while bus {bus.id!r} has phases {bus.phases!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        self.currents = currents  # handles size checks and unit conversion
        if self.phases == "abc":
            self._cy_element = CyDeltaCurrentLoad(n=self._n, currents=self._currents)
        else:
            self._cy_element = CyCurrentLoad(n=self._n, currents=self._currents)
        self._cy_connect()

    @property
    @ureg_wraps("A", (None,))
    def currents(self) -> Q_[ComplexArray]:
        """The currents of the load (Amps).

        Setting the currents will update the load's currents and invalidate the network results.
        """
        return self._currents

    @currents.setter
    @ureg_wraps(None, (None, "A"))
    def currents(self, value: ComplexScalarOrArrayLike1D) -> None:
        self._currents = self._validate_value(value)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_currents(self._currents)


class ImpedanceLoad(AbstractLoad):
    """A constant impedance load."""

    type: Final = "impedance"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        impedances: ComplexScalarOrArrayLike1D,
        phases: str | None = None,
        connect_neutral: bool | None = None,
    ) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            impedances:
                A single impedance value or an array-like of impedance values for each phase component.
                Either complex values (Ohms) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

                When a scalar value is provided, it creates a balanced load with the same impedance
                for each phase. To create an unbalanced load, provide a vector of impedance values
                with the same length as the number of components of the load.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to be
                connected to buses that don't have a neutral if ``connect_neutral`` is not set to
                ``True``.

            connect_neutral:
                Specifies whether the load's neutral should be connected to the bus's neutral or
                left floating. By default, the load's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the load's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        super().__init__(id=id, phases=phases, bus=bus, connect_neutral=connect_neutral)
        self.impedances = impedances
        if self.phases == "abc":
            self._cy_element = CyDeltaAdmittanceLoad(n=self._n, admittances=1.0 / self._impedances)
        else:
            self._cy_element = CyAdmittanceLoad(n=self._n, admittances=1.0 / self._impedances)
        self._cy_connect()

    @property
    @ureg_wraps("ohm", (None,))
    def impedances(self) -> Q_[ComplexArray]:
        """The impedances of the load (Ohms)."""
        return self._impedances

    @impedances.setter
    @ureg_wraps(None, (None, "ohm"))
    def impedances(self, impedances: ComplexScalarOrArrayLike1D) -> None:
        self._impedances = self._validate_value(impedances)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_admittances(1.0 / self._impedances)
