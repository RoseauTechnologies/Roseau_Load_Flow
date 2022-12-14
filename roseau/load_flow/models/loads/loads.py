import logging
from abc import ABCMeta
from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
from pint import Quantity

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element, Phases
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class AbstractLoad(Element, JsonMixin, metaclass=ABCMeta):
    """An abstract class of an electric load."""

    _power_load_class: type["PowerLoad"]
    _current_load_class: type["CurrentLoad"]
    _impedance_load_class: type["ImpedanceLoad"]
    _flexible_load_class: type["FlexibleLoad"]

    _type: Literal["power", "current", "impedance"]

    def __init__(self, id: Any, phases: Phases, bus: Bus, **kwargs) -> None:
        """AbstractLoad constructor.

        Args:
            id:
                The unique id of the load.

            phases:
                The phases of the load. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

            bus:
                The bus to connect the load to.
        """
        self._check_phases(id, phases=phases)
        super().__init__(**kwargs)
        self.connected_elements = [bus]
        bus.connected_elements.append(self)

        self.id = id
        self.phases = phases
        self.bus = bus
        self._currents = None
        self._symbol = {"power": "S", "current": "I", "impedance": "Z"}[self._type]

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.id!r}, phases={self.phases!r}, bus={self.bus.id!r})"

    def __str__(self) -> str:
        return f"id={self.id!r} - phases={self.phases!r}"

    @property
    @ureg.wraps("A", None, strict=False)
    def currents(self) -> np.ndarray:
        """An array of the actual currents of each phase (A) as computed by the load flow."""
        return self._currents

    @currents.setter
    def currents(self, value: np.ndarray) -> None:
        self._currents = value

    def _validate_value(self, value: Sequence[complex]) -> Sequence[complex]:
        if len(value) != 3:  # TODO change the test when we have phases
            msg = f"Incorrect number of {self._type}s: {len(value)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(
                msg=msg, code=RoseauLoadFlowExceptionCode.from_string(f"BAD_{self._symbol}_SIZE")
            )
        # A load cannot have any zero impedance
        if self._type == "impedance" and np.isclose(value, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return value

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any], bus: Bus) -> "AbstractLoad":
        id = data["id"]
        phases = data["phases"]
        if (params := data.get("parameters")) is not None:
            s = data["powers"]
            s_complex = [complex(*s["sa"]), complex(*s["sb"]), complex(*s["sc"])]
            parameters = [cls._flexible_load_class._flexible_parameter_class.from_dict(p) for p in params]
            return cls._flexible_load_class(id, phases, bus, s=s_complex, parameters=parameters)
        elif (s := data.get("powers")) is not None:
            s_complex = [complex(*s["sa"]), complex(*s["sb"]), complex(*s["sc"])]
            return cls._power_load_class(id, phases, bus, s=s_complex)
        elif (i := data.get("currents")) is not None:
            i_complex = [complex(*i["ia"]), complex(*i["ib"]), complex(*i["ic"])]
            return cls._current_load_class(id, phases, bus, i=i_complex)
        elif (z := data.get("impedances")) is not None:
            z_complex = [complex(*z["za"]), complex(*z["zb"]), complex(*z["zc"])]
            return cls._impedance_load_class(id, phases, bus, z=z_complex)
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

    def __init__(self, id: Any, phases: Phases, bus: Bus, s: Sequence[complex], **kwargs) -> None:
        """PowerLoad constructor.

        Args:
            id:
                The unique id of the load.

            phases:
                The phases of the load. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

            bus:
                The bus to connect the load to.

            s:
                List of power for each phase (VA).
        """
        super().__init__(id=id, phases=phases, bus=bus, **kwargs)
        if isinstance(s, Quantity):
            s = s.m_as("VA")
        self.s = self._validate_value(s)

    @ureg.wraps(None, (None, "VA"), strict=False)
    def update_powers(self, s: Sequence[complex]) -> None:
        """Change the powers of the load.

        Args:
            s:
                The new powers to set (VA).
        """
        self.s = self._validate_value(s)

    def to_dict(self) -> dict[str, Any]:
        sa, sb, sc = self.s
        return {
            "id": self.id,
            "phases": self.phases,
            "powers": {
                "sa": [sa.real, sa.imag],
                "sb": [sb.real, sb.imag],
                "sc": [sc.real, sc.imag],
            },
        }


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

    def __init__(self, id: Any, phases: Phases, bus: Bus, i: Sequence[complex], **kwargs) -> None:
        """CurrentLoad constructor.

        Args:
            id:
                The unique id of the load.

            phases:
                The phases of the load. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

            bus:
                The bus to connect the load to.

            i:
                List of currents for each phase (Amps).
        """
        super().__init__(id=id, phases=phases, bus=bus, **kwargs)
        if isinstance(i, Quantity):
            i = i.m_as("A")
        self.i = self._validate_value(i)

    @ureg.wraps(None, (None, "A"), strict=False)
    def update_currents(self, i: Sequence[complex]) -> None:
        """Change the currents of the load.

        Args:
            i:
                The new currents to set (Amps).
        """
        self.i = self._validate_value(i)

    def to_dict(self) -> dict[str, Any]:
        ia, ib, ic = self.i
        return {
            "id": self.id,
            "phases": self.phases,
            "currents": {
                "ia": [ia.real, ia.imag],
                "ib": [ib.real, ib.imag],
                "ic": [ic.real, ic.imag],
            },
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

    def __init__(self, id: Any, phases: Phases, bus: Bus, z: Sequence[complex], **kwargs) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                The unique id of the load.

            phases:
                The phases of the load. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

            bus:
                The bus to connect the load to.

            z:
                List of impedances for each phase (Ohms).
        """
        super().__init__(id=id, phases=phases, bus=bus, **kwargs)
        if isinstance(z, Quantity):
            z = z.m_as("ohm")
        self.z = self._validate_value(z)

    @ureg.wraps(None, (None, "ohm"), strict=False)
    def update_impedances(self, z: Sequence[complex]) -> None:
        """Change the impedances of the load.

        Args:
            z:
                The new impedances to set (Ohms).
        """
        self.z = self._validate_value(z)

    def to_dict(self) -> dict[str, Any]:
        za, zb, zc = self.z
        return {
            "id": self.id,
            "phases": self.phases,
            "impedances": {
                "za": [za.real, za.imag],
                "zb": [zb.real, zb.imag],
                "zc": [zc.real, zc.imag],
            },
        }


class FlexibleLoad(PowerLoad):
    """A flexible power load i.e. a load with control."""

    _flexible_parameter_class: type[FlexibleParameter] = FlexibleParameter

    def __init__(
        self, id: Any, phases: Phases, bus: Bus, s: Sequence[complex], parameters: list[FlexibleParameter], **kwargs
    ):
        """FlexibleLoad constructor.

        Args:
            id:
                The unique id of the load.

            phases:
                The phases of the load. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

            bus:
                The bus to connect the load to.

            s:
                List of theoretical powers for each phase.

            parameters:
                List of flexible parameters for each phase.
        """
        super().__init__(id=id, phases=phases, bus=bus, s=s, **kwargs)
        if len(parameters) != 3:
            msg = f"Incorrect number of parameters: {len(parameters)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)

        for power, parameter in zip(self.s, parameters):
            if abs(power) > parameter.s_max and (
                parameter.control_p.type != "constant" or parameter.control_q.type != "constant"
            ):
                msg = f"The power is greater than the parameter s_max for flexible load {self.id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
            if parameter.control_p.type == "p_max_u_production" and power.real > 0:
                msg = f"There is a production control but a positive power for flexible load {self.id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
            if parameter.control_p.type == "p_max_u_consumption" and power.real < 0:
                msg = f"There is a consumption control but a negative power for flexible load {self.id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
            if parameter.control_p.type != "constant" and power.real == 0:
                msg = f"There is a P control but a null active power for flexible load {self.id!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)

        self.parameters = parameters
        self._powers = None

    @property
    @ureg.wraps("VA", None, strict=False)
    def powers(self) -> np.ndarray:
        """An array of the actual powers of each phase (VA) as computed by the load flow."""
        return self._powers

    @powers.setter
    def powers(self, value: np.ndarray):
        self._powers = value

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "parameters": [p.to_dict() for p in self.parameters]}


AbstractLoad._power_load_class = PowerLoad
AbstractLoad._current_load_class = CurrentLoad
AbstractLoad._impedance_load_class = ImpedanceLoad
AbstractLoad._flexible_load_class = FlexibleLoad
