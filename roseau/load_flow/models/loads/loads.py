import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Sequence
from typing import Any, Literal, Optional

import numpy as np
from pint import Quantity

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class AbstractLoad(Element, metaclass=ABCMeta):
    """An abstract class of an electric load."""

    _power_load_class: type["PowerLoad"]
    _current_load_class: type["CurrentLoad"]
    _impedance_load_class: type["ImpedanceLoad"]
    _flexible_parameter_class = FlexibleParameter

    _type: Literal["power", "current", "impedance"]
    _floating_neutral_allowed: bool = False

    allowed_phases = Bus.allowed_phases

    def __init__(self, id: Id, bus: Bus, *, phases: Optional[str] = None, **kwargs: Any) -> None:
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

        self.phases = phases
        self.bus = bus
        self._symbol = {"power": "S", "current": "I", "impedance": "Z"}[self._type]
        self._unit = {"power": "VA", "current": "A", "impedance": "ohm"}[self._type]
        if len(phases) == 2 and "n" not in phases:
            # This is a delta load that has one element connected between two phases
            self._size = 1
        else:
            self._size = len(set(phases) - {"n"})

        # Results
        self._res_currents: Optional[np.ndarray] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r}, bus={self.bus.id!r})"

    @property
    def is_flexible(self) -> bool:
        """Whether the load is flexible or not. Only :class:`PowerLoad` can be flexible."""
        return False

    @property
    def res_currents(self) -> np.ndarray:
        """The load flow result of the load currents (A)."""
        if self._res_currents is None:
            self._raise_load_flow_not_run()
        return self._res_currents

    def _validate_value(self, value: Sequence[complex]) -> np.ndarray:
        if isinstance(value, Quantity):
            value = value.m_as(self._unit)
        if len(value) != self._size:
            msg = f"Incorrect number of {self._type}s: {len(value)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(
                msg=msg, code=RoseauLoadFlowExceptionCode.from_string(f"BAD_{self._symbol}_SIZE")
            )
        # A load cannot have any zero impedance
        if self._type == "impedance" and np.isclose(value, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return np.asarray(value, dtype=complex)

    def _get_res_voltages_from_bus(self) -> np.ndarray:
        if "n" in self.phases:
            # Wye load: get the phase-to-neutral voltages
            bus_voltages = self.bus.res_voltages
        else:
            # Delta load: get the phase-to-phase voltages
            bus_voltages = np.roll(self.bus.res_potentials, -1) - self.bus.res_potentials
        current_phases = self.phases.removesuffix("n")

        # filter to the voltages of this load
        voltages = []
        for v, (p1, _) in zip(bus_voltages, self.bus.voltage_phases):
            if p1 in current_phases:
                voltages.append(v)
        return np.array(voltages)

    @abstractmethod
    def _get_delta_res_powers(self) -> np.ndarray:
        raise NotImplementedError

    @property
    def res_powers(self) -> np.ndarray:
        """The load flow result of the load powers (VA)."""
        currents = self.res_currents[: self._size]  # without the neutral
        voltages = self._get_res_voltages_from_bus()
        if "n" in self.phases:
            # Wye load: trivial
            return voltages * currents.conj()
        else:
            # Delta load: two cases
            if len(self.phases) == 2:
                # 1. A phase-to-phase connection: line current is the same as phase current
                return voltages * currents[0].conj()  # Example: Sab = Vab x Iab*; Iab = Ia = - Ib
            else:
                # 2. We don't know the phase currents. We can use the load inputs to compute S.
                # CurrentLoad: S = V x I_in*; PowerLoad: S = S_in; ImpedanceLoad: S = |V|² / Z*
                return self._get_delta_res_powers()

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> "AbstractLoad":
        if (s_list := data.get("powers")) is not None:
            powers = [complex(s[0], s[1]) for s in s_list]
            if (fp_data_list := data.get("flexible_params")) is not None:
                fp = [cls._flexible_parameter_class.from_dict(fp_dict) for fp_dict in fp_data_list]
            else:
                fp = None
            return cls._power_load_class(
                data["id"], data["bus"], powers=powers, phases=data["phases"], flexible_params=fp
            )
        elif (i_list := data.get("currents")) is not None:
            currents = [complex(i[0], i[1]) for i in i_list]
            return cls._current_load_class(data["id"], data["bus"], currents=currents, phases=data["phases"])
        elif (z_list := data.get("impedances")) is not None:
            impedances = [complex(z[0], z[1]) for z in z_list]
            return cls._impedance_load_class(data["id"], data["bus"], impedances=impedances, phases=data["phases"])
        else:
            msg = f"Unknown load type for load {data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)


class PowerLoad(AbstractLoad):
    r"""A constant power load.

    The equations are the following (star loads):

    .. math::
        I_{\mathrm{abc}} &= \left(\frac{S_{\mathrm{abc}}}{V_{\mathrm{abc}}-V_{\mathrm{n}}}\right)^{\star} \\
        I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}

    and the following (delta loads):

    .. math::
        I_{\mathrm{ab}} &= \left(\frac{S_{\mathrm{ab}}}{V_{\mathrm{a}}-V_{\mathrm{b}}}\right)^{\star} \\
        I_{\mathrm{bc}} &= \left(\frac{S_{\mathrm{bc}}}{V_{\mathrm{b}}-V_{\mathrm{c}}}\right)^{\star} \\
        I_{\mathrm{ca}} &= \left(\frac{S_{\mathrm{ca}}}{V_{\mathrm{c}}-V_{\mathrm{a}}}\right)^{\star}

    """

    _type = "power"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        powers: Sequence[complex],
        phases: Optional[str] = None,
        flexible_params: Optional[list[FlexibleParameter]] = None,
        **kwargs: Any,
    ) -> None:
        """PowerLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            powers:
                List of power for each phase (VA).

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
        self.powers = powers

        if flexible_params:
            if len(flexible_params) != self._size:
                msg = f"Incorrect number of parameters: {len(flexible_params)} instead of {self._size}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
            for power, fp in zip(self.powers, flexible_params):
                if fp.control_p.type == "constant" and fp.control_q.type == "constant":
                    continue  # No checks for this case
                if abs(power) > fp.s_max:
                    msg = f"The power is greater than the parameter s_max for flexible load {id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if fp.control_p.type == "p_max_u_production" and power.real > 0:
                    msg = f"There is a production control but a positive power for flexible load {id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if fp.control_p.type == "p_max_u_consumption" and power.real < 0:
                    msg = f"There is a consumption control but a negative power for flexible load {id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if fp.control_p.type != "constant" and power.real == 0:
                    msg = f"There is a P control but a null active power for flexible load {id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)

        self.flexible_params = flexible_params
        self._res_flexible_powers: Optional[np.ndarray] = None

    @property
    def is_flexible(self) -> bool:
        return self.flexible_params is not None

    @property
    def powers(self) -> np.ndarray:
        """The powers of the load (VA)."""
        return self._powers

    @powers.setter
    @ureg.wraps(None, (None, "VA"), strict=False)
    def powers(self, value: Sequence[complex]) -> None:
        self._powers = self._validate_value(value)

    @property
    def res_flexible_powers(self) -> np.ndarray:
        """The load flow result of the load flexible powers (VA)."""
        if self._res_flexible_powers is None:
            self._raise_load_flow_not_run()
        return self._res_flexible_powers

    def _get_delta_res_powers(self) -> np.ndarray:
        return self._powers  # S = S

    def to_dict(self) -> JsonDict:
        res = {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            "powers": [[s.real, s.imag] for s in self.powers],
        }
        if self.flexible_params is not None:
            res["flexible_params"] = [fp.to_dict() for fp in self.flexible_params]
        return res


class CurrentLoad(AbstractLoad):
    r"""A constant current load.

    The equations are the following (star loads):

    .. math::
        I_{\mathrm{abc}} &= constant \\
        I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}

    and the following (delta loads):

    .. math::
        I_{\mathrm{ab}} &= constant \\
        I_{\mathrm{bc}} &= constant \\
        I_{\mathrm{ca}} &= constant
    """

    _type = "current"

    def __init__(
        self, id: Id, bus: Bus, *, currents: Sequence[complex], phases: Optional[str] = None, **kwargs: Any
    ) -> None:
        """CurrentLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            currents:
                List of currents for each phase (Amps).

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the load, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.
        """
        super().__init__(id=id, phases=phases, bus=bus, **kwargs)
        self.currents = currents  # handles size checks and unit conversion

    @property
    def currents(self) -> np.ndarray:
        """The currents of the load (Amps)."""
        return self._currents

    @currents.setter
    @ureg.wraps(None, (None, "A"), strict=False)
    def currents(self, value: Sequence[complex]) -> None:
        self._currents = self._validate_value(value)

    def _get_delta_res_powers(self) -> np.ndarray:
        voltages = self._get_res_voltages_from_bus()
        return voltages * self.currents.conj()  # S = V x I*

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            "currents": [[i.real, i.imag] for i in self.currents],
        }


class ImpedanceLoad(AbstractLoad):
    r"""A constant impedance load.

    The equations are the following (star loads):

    .. math::
        I_{\mathrm{abc}} &= \frac{\left(V_{\mathrm{abc}}-V_{\mathrm{n}}\right)}{Z_{\mathrm{abc}}} \\
        I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}

    and the following (delta loads):

    .. math::
        I_{\mathrm{ab}} &= \frac{\left(V_{\mathrm{a}}-V_{\mathrm{b}}\right)}{Z_{\mathrm{ab}}} \\
        I_{\mathrm{bc}} &= \frac{\left(V_{\mathrm{b}}-V_{\mathrm{c}}\right)}{Z_{\mathrm{bc}}} \\
        I_{\mathrm{ca}} &= \frac{\left(V_{\mathrm{c}}-V_{\mathrm{a}}\right)}{Z_{\mathrm{ca}}}

    """

    _type = "impedance"

    def __init__(
        self, id: Id, bus: Bus, *, impedances: Sequence[complex], phases: Optional[str] = None, **kwargs: Any
    ) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            impedances:
                List of impedances for each phase (Ohms).

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the load, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.
        """
        super().__init__(id=id, phases=phases, bus=bus, **kwargs)
        self.impedances = impedances

    @property
    def impedances(self) -> np.ndarray:
        """The impedances of the load (Ohms)."""
        return self._impedances

    @impedances.setter
    @ureg.wraps(None, (None, "ohm"), strict=False)
    def impedances(self, impedances: Sequence[complex]) -> None:
        self._impedances = self._validate_value(impedances)

    def _get_delta_res_powers(self) -> np.ndarray:
        voltages = self._get_res_voltages_from_bus()
        return np.abs(voltages) ** 2 / self.impedances  # S = |V|² / Z

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            "impedances": [[z.real, z.imag] for z in self.impedances],
        }


AbstractLoad._power_load_class = PowerLoad
AbstractLoad._current_load_class = CurrentLoad
AbstractLoad._impedance_load_class = ImpedanceLoad
