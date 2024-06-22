import logging
from abc import ABC
from functools import cached_property
from typing import ClassVar, Final, Literal

import numpy as np

from roseau.load_flow.converters import _calculate_voltages, calculate_voltage_phases
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.typing import ComplexArray, ComplexArrayLike1D, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
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

    def __init__(self, id: Id, bus: Bus, *, phases: str | None = None) -> None:
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
                be present in the phases of the connected bus. Multiphase loads are allowed to have
                a floating neutral (i.e. they can be connected to buses that don't have a neutral).
        """
        if type(self) is AbstractLoad:
            raise TypeError("Can't instantiate abstract class AbstractLoad")
        super().__init__(id)
        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id, phases=phases)
            # Also check they are in the bus phases
            phases_not_in_bus = set(phases) - set(bus.phases)
            # "n" is allowed to be absent from the bus only if the load has more than 2 phases
            floating_neutral = phases_not_in_bus == {"n"} and len(phases) > 2
            if phases_not_in_bus and not floating_neutral:
                msg = (
                    f"Phases {sorted(phases_not_in_bus)} of load {id!r} are not in bus {bus.id!r} "
                    f"phases {bus.phases!r}"
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        self._connect(bus)

        self._phases = phases
        self._bus = bus
        self._n = len(self._phases)
        self._symbol = {"power": "S", "current": "I", "impedance": "Z"}[self.type]
        if len(phases) == 2 and "n" not in phases:
            # This is a delta load that has one element connected between two phases
            self._size = 1
        else:
            self._size = len(set(phases) - {"n"})

        # Results
        self._res_currents: ComplexArray | None = None
        self._res_potentials: ComplexArray | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r}, bus={bus_id!r})"

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

    @property
    def has_floating_neutral(self) -> bool:
        """Does this load have a floating neutral?"""
        return "n" in self._phases and "n" not in self._bus._phases

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

    def _validate_value(self, value: ComplexArrayLike1D) -> ComplexArray:
        if len(value) != self._size:
            msg = f"Incorrect number of {self.type}s: {len(value)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{self._symbol}_SIZE"])
        # A load cannot have any zero impedance
        if self.type == "impedance" and np.isclose(value, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return np.array(value, dtype=np.complex128)

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

    def _res_powers_getter(self, warning: bool) -> ComplexArray:
        curs = self._res_currents_getter(warning)
        pots = self._res_potentials_getter(warning=False)  # we warn on the previous line
        return pots * curs.conj()

    @property
    @ureg_wraps("VA", (None,))
    def res_powers(self) -> Q_[ComplexArray]:
        """The load flow result of the "line powers" flowing into the load (VA)."""
        return self._res_powers_getter(warning=True)

    def _cy_connect(self):
        connections = []
        for i, phase in enumerate(self.bus.phases):
            if phase in self.phases:
                j = self.phases.find(phase)
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
        if (s_list := data.get("powers")) is not None:
            powers = [complex(s[0], s[1]) for s in s_list]
            if (fp_data_list := data.get("flexible_params")) is not None:
                fp = [FlexibleParameter.from_dict(fp_dict, include_results=include_results) for fp_dict in fp_data_list]
            else:
                fp = None
            self = PowerLoad(data["id"], data["bus"], powers=powers, phases=data["phases"], flexible_params=fp)
        elif (i_list := data.get("currents")) is not None:
            currents = [complex(i[0], i[1]) for i in i_list]
            self = CurrentLoad(data["id"], data["bus"], currents=currents, phases=data["phases"])
        elif (z_list := data.get("impedances")) is not None:
            impedances = [complex(z[0], z[1]) for z in z_list]
            self = ImpedanceLoad(data["id"], data["bus"], impedances=impedances, phases=data["phases"])
        else:
            msg = f"Unknown load type for load {data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        if include_results and "results" in data:
            self._res_currents = np.array(
                [complex(i[0], i[1]) for i in data["results"]["currents"]], dtype=np.complex128
            )
            if "potentials" in data["results"]:
                self._res_potentials = np.array(
                    [complex(i[0], i[1]) for i in data["results"]["potentials"]], dtype=np.complex128
                )
            elif not self.has_floating_neutral:
                self._res_potentials = data["bus"]._get_potentials_of(self.phases, warning=False)
            else:
                msg = f"{type(self).__name__} {self.id!r} with floating neutral is missing results of potentials."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)
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
            f"{self.type}s": [[value.real, value.imag] for value in complex_array],
        }
        if include_results:
            currents = self._res_currents_getter(warning=True)
            res["results"] = {"currents": [[i.real, i.imag] for i in currents]}
            if self.has_floating_neutral:
                potentials = self._res_potentials_getter(warning=True)
                res["results"]["potentials"] = [[v.real, v.imag] for v in potentials]
        return res

    def _results_to_dict(self, warning: bool) -> JsonDict:
        results = {
            "id": self.id,
            "phases": self.phases,
            "currents": [[i.real, i.imag] for i in self._res_currents_getter(warning)],
        }
        if self.has_floating_neutral:
            potentials = self._res_potentials_getter(warning=True)
            results["potentials"] = [[v.real, v.imag] for v in potentials]
        return results


class PowerLoad(AbstractLoad):
    """A constant power load."""

    type: Final = "power"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        powers: ComplexArrayLike1D,
        phases: str | None = None,
        flexible_params: list[FlexibleParameter] | None = None,
    ) -> None:
        """PowerLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            powers:
                An array-like of the powers for each phase component. Either complex values (VA)
                or a :class:`Quantity <roseau.load_flow.units.Q_>` of complex values.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to have
                a floating neutral (i.e. they can be connected to buses that don't have a neutral).

            flexible_params:
                A list of :class:`FlexibleParameters` object, one for each phase. When provided,
                the load is considered as flexible (or controllable) and the parameters are used
                to compute the flexible power of the load.
        """
        super().__init__(id=id, bus=bus, phases=phases)

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
            cy_parameters = []
            for p in flexible_params:
                cy_parameters.append(p._cy_fp)
            if self.phases == "abc":
                self._cy_element = CyDeltaFlexibleLoad(
                    n=self._n, powers=self._powers, parameters=np.array(cy_parameters)
                )
            else:
                self._cy_element = CyFlexibleLoad(n=self._n, powers=self._powers, parameters=np.array(cy_parameters))
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
        """The powers of the load (VA)."""
        return self._powers

    @powers.setter
    @ureg_wraps(None, (None, "VA"))
    def powers(self, value: ComplexArrayLike1D) -> None:
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

    def _res_flexible_powers_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._res_flexible_powers = self._cy_element.get_powers(self._n)
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
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> AbstractLoad:
        self = super().from_dict(data, include_results=include_results)
        if self.is_flexible and include_results and "results" in data:
            self._res_flexible_powers = np.array(
                [complex(p[0], p[1]) for p in data["results"]["powers"]], dtype=np.complex128
            )
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = super()._to_dict(include_results=include_results)
        if self.flexible_params is not None:
            res["flexible_params"] = [fp.to_dict(include_results=include_results) for fp in self.flexible_params]
        if self.is_flexible and include_results:
            flexible_powers = self._res_flexible_powers_getter(warning=False)
            res["results"]["powers"] = [[s.real, s.imag] for s in flexible_powers]
        return res

    def _results_to_dict(self, warning: bool) -> JsonDict:
        if self.is_flexible:
            return {
                **super()._results_to_dict(warning),
                "powers": [[s.real, s.imag] for s in self._res_flexible_powers_getter(False)],
            }
        else:
            return super()._results_to_dict(warning)


class CurrentLoad(AbstractLoad):
    """A constant current load."""

    type: Final = "current"

    def __init__(self, id: Id, bus: Bus, *, currents: ComplexArrayLike1D, phases: str | None = None) -> None:
        """CurrentLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            currents:
                An array-like of the currents for each phase component. Either complex values (A)
                or a :class:`Quantity <roseau.load_flow.units.Q_>` of complex values.

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
        """The currents of the load (Amps)."""
        return self._currents

    @currents.setter
    @ureg_wraps(None, (None, "A"))
    def currents(self, value: ComplexArrayLike1D) -> None:
        self._currents = self._validate_value(value)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_currents(self._currents)


class ImpedanceLoad(AbstractLoad):
    """A constant impedance load."""

    type: Final = "impedance"

    def __init__(self, id: Id, bus: Bus, *, impedances: ComplexArrayLike1D, phases: str | None = None) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            impedances:
                An array-like of the impedances for each phase component. Either complex values
                (Ohms) or a :class:`Quantity <roseau.load_flow.units.Q_>` of complex values.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to have
                a floating neutral (i.e. they can be connected to buses that don't have a neutral).
        """
        super().__init__(id=id, phases=phases, bus=bus)
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
    def impedances(self, impedances: ComplexArrayLike1D) -> None:
        self._impedances = self._validate_value(impedances)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_admittances(1.0 / self._impedances)
