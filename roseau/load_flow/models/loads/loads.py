import logging
from abc import ABC
from typing import Any, Literal

import numpy as np

from roseau.load_flow.converters import calculate_voltage_phases, calculate_voltages
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

    _type: Literal["power", "current", "impedance"]
    _floating_neutral_allowed: bool = False

    allowed_phases = Bus.allowed_phases
    """The allowed phases for a load are the same as for a :attr:`bus<Bus.allowed_phases>`."""

    def __init__(self, id: Id, bus: Bus, *, phases: str | None = None, **kwargs: Any) -> None:
        """AbstractLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the load, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.
        """
        super().__init__(id, **kwargs)
        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id, phases=phases)
            # Also check they are in the bus phases
            phases_not_in_bus = set(phases) - set(bus.phases)
            # "n" is allowed to be absent from the bus only if the load has more than 2 phases
            floating_neutral = self._floating_neutral_allowed and phases_not_in_bus == {"n"} and len(phases) > 2
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
        self._symbol = {"power": "S", "current": "I", "impedance": "Z"}[self._type]
        if len(phases) == 2 and "n" not in phases:
            # This is a delta load that has one element connected between two phases
            self._size = 1
        else:
            self._size = len(set(phases) - {"n"})

        # Results
        self._res_currents: ComplexArray | None = None

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
    def voltage_phases(self) -> list[str]:
        """The phases of the load voltages."""
        return calculate_voltage_phases(self.phases)

    def _res_currents_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._res_currents = self._cy_element.get_currents(self._n)
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps("A", (None,))
    def res_currents(self) -> Q_[ComplexArray]:
        """The load flow result of the load currents (A)."""
        return self._res_currents_getter(warning=True)

    def _validate_value(self, value: ComplexArrayLike1D) -> ComplexArray:
        if len(value) != self._size:
            msg = f"Incorrect number of {self._type}s: {len(value)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{self._symbol}_SIZE"])
        # A load cannot have any zero impedance
        if self._type == "impedance" and np.isclose(value, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return np.array(value, dtype=np.complex128)

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        self._raise_disconnected_error()
        return self.bus._get_potentials_of(self.phases, warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potentials(self) -> Q_[ComplexArray]:
        """The load flow result of the load potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(self, warning: bool) -> ComplexArray:
        potentials = self._res_potentials_getter(warning)
        return calculate_voltages(potentials, self.phases)

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
        """The load flow result of the load powers (VA)."""
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
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        complex_array = getattr(self, f"_{self._type}s")
        res = {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            f"{self._type}s": [[value.real, value.imag] for value in complex_array],
        }
        if include_results:
            currents = self._res_currents_getter(warning=True)
            res["results"] = {"currents": [[i.real, i.imag] for i in currents]}
        return res

    def _results_from_dict(self, data: JsonDict) -> None:
        self._res_currents = np.array([complex(i[0], i[1]) for i in data["currents"]], dtype=np.complex128)
        self._fetch_results = False
        self._no_results = False

    def _results_to_dict(self, warning: bool) -> JsonDict:
        return {
            "id": self.id,
            "phases": self.phases,
            "currents": [[i.real, i.imag] for i in self._res_currents_getter(warning)],
        }


class PowerLoad(AbstractLoad):
    """A constant power load."""

    _type = "power"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        powers: ComplexArrayLike1D,
        phases: str | None = None,
        flexible_params: list[FlexibleParameter] | None = None,
        **kwargs: Any,
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
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the load, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.

            flexible_params:
                A list of :class:`FlexibleParameters` object, one for each phase. When provided,
                the load is considered as flexible (or controllable) and the parameters are used
                to compute the flexible power of the load.
        """
        super().__init__(id=id, bus=bus, phases=phases, **kwargs)

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
        if self.is_flexible:
            for power, fp in zip(value, self._flexible_params, strict=True):
                if fp.control_p.type == "constant" and fp.control_q.type == "constant":
                    continue  # No checks for this case
                if abs(power) > fp.s_max.m_as("VA"):
                    msg = f"The power is greater than the parameter s_max for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if power.imag < fp.q_min.m_as("VAr"):
                    msg = f"The reactive power is lesser than the parameter q_min for flexible load {id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if power.imag > fp.q_max.m_as("VAr"):
                    msg = f"The reactive power is greater than the parameter q_max for flexible load {id!r}"
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
                if fp.control_p.type != "constant" and power.real == 0:
                    msg = f"There is a P control but a null active power for flexible load {self.id!r}"
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
        """The load flow result of the load flexible powers (VA)."""
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

    def _results_from_dict(self, data: JsonDict) -> None:
        super()._results_from_dict(data=data)
        if self.is_flexible:
            self._res_flexible_powers = np.array([complex(p[0], p[1]) for p in data["powers"]], dtype=np.complex128)

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

    _type = "current"

    def __init__(
        self, id: Id, bus: Bus, *, currents: ComplexArrayLike1D, phases: str | None = None, **kwargs: Any
    ) -> None:
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
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the load, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.
        """
        super().__init__(id=id, phases=phases, bus=bus, **kwargs)
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

    _type = "impedance"

    def __init__(
        self, id: Id, bus: Bus, *, impedances: ComplexArrayLike1D, phases: str | None = None, **kwargs: Any
    ) -> None:
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
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the load, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.
        """
        super().__init__(id=id, phases=phases, bus=bus, **kwargs)
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
