import logging
from collections.abc import Sequence
from typing import Any, Literal, Optional

import numpy as np
from pint import Quantity

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)

LoadType = Literal["power", "admittance", "impedance"]  # TODO constant "current" loads?
Connection = Literal["star", "delta"]


class Load(Element, JsonMixin):
    """An electrical load."""

    _UNITS = {
        "power": "VA",
        "admittance": "S",
        "impedance": "ohm",
    }
    _FUNCTIONS = {
        "power": {"star": "ys", "star_neutral": "ys_neutral", "delta": "ds"},
        "admittance": {"star": "yy", "star_neutral": "yy_neutral", "delta": "dy"},
        "impedance": {"star": "yz", "star_neutral": "yz_neutral", "delta": "dz"},
    }

    _ERRORS = {"power": "S", "admittance": "Y", "impedance": "Z"}

    def __init__(
        self,
        id: Any,
        n: int,
        bus: Bus,
        type: LoadType,
        value: Sequence[complex],
        connection: Connection = "star",
        **kwargs: Any,
    ) -> None:
        """Generic electrical load constructor.

        Args:
            id:
                The unique id of the load.

            n:
                The number of ports (phases) of the load.

            bus:
                The bus to connect the load to.

            type:
                The type of the load. Available choices:
                    * ``"power"``: "Constant Power" load. See :meth:`constant_power` for details.
                    * ``"admittance"``: "Constant Admittance" load. See :meth:`constant_admittance`
                      for details.
                    * ``"impedance"``: "Constant Impedance" load. See :meth:`constant_impedance`
                      for details.

            value:
                The value of the load quantity according to its type:
                    * ``"power"``: A sequence of complex values representing the apparent powers
                      of each phase.
                    * ``"admittance"``: A sequence of complex values representing the admittances
                      of each phase.
                    * ``"impedance"``: A sequence of complex values representing the impedances
                      of each phase.

            connection:
                The connection type of the load. Can be ``"star"`` or ``"delta"``.
        """
        super().__init__(**kwargs)
        self.connected_elements = [bus]
        bus.connected_elements.append(self)

        if connection == "delta":
            dimension = 3
            if n != 3:
                msg = f"Delta connection requires 3 ports, not {n}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            dimension = n - 1
            if n == 4:  # is n ever 3 here!!!
                connection = "star_neutral"

        self._unit = self._UNITS[type]
        self._function = self._FUNCTIONS[type][connection]
        self._dimension = dimension
        self._powers = None

        self.id = id
        self.n = n
        self.bus = bus
        self._currents = None

        self.flexible_parameters: Optional[list[FlexibleParameter]] = None
        self.type = type
        self.value = self._check_value(value)

    def _check_value(self, value: Sequence[complex]) -> Sequence[complex]:
        if isinstance(value, Quantity):
            value = value.m_as(self._unit)
        if len(value) != self._dimension:
            error_code = RoseauLoadFlowExceptionCode.from_string(f"BAD_{self._ERRORS[self.type]}_SIZE")
            msg = f"Incorrect number of {self.type}: {len(value)} instead of {self._dimension}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=error_code)
        if self.type == "impedance" and np.isclose(value, 0).any():
            msg = f"An impedance for load {id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.id!r}, n={self.n}, bus={self.bus.id!r})"

    def __str__(self) -> str:
        return f"id={self.id} - n={self.n}"

    @property
    @ureg.wraps("A", None, strict=False)
    def currents(self) -> np.ndarray:
        """An array containing the actual currents of each phase."""
        return self._currents

    @currents.setter
    def currents(self, value: np.ndarray) -> None:
        self._currents = value

    @property
    @ureg.wraps("VA", None, strict=False)
    def powers(self) -> np.ndarray:
        """Compute the actual power consumed by the loads.

        Returns:
            An array containing the actual powers of each phase (VA)
        """
        return self._powers

    @powers.setter
    def powers(self, value: np.ndarray) -> None:
        if not self.is_flexible():
            msg = f"Cannot set the power of a non flexible load {self.id!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        self._powers = value

    def update(self, value: Sequence[complex]) -> None:
        """Update the load.

        Args:
            value:
                The value to be updated.
        """
        self.value = self._check_value(value)

    def is_flexible(self) -> bool:
        """Check if the load is flexible.

        Returns:
            True if the load is flexible, False otherwise.
        """
        return self.flexible_parameters is not None

    @classmethod
    def constant_power(
        cls,
        id: Any,
        n: int,
        bus: Bus,
        power: Sequence[complex],
        connection: Connection = "star",
        **kwargs: Any,
    ) -> "Load":
        r"""Create a constant power load.

        A constant power load is a load whose power value does not depend on the voltage. It is
        characterized its apparent power.

        The equations are the following (star loads):

        .. math::
            I_{\mathrm{abc}} &= \left(\frac{S_{\mathrm{abc}}}{V_{\mathrm{abc}}-V_{\mathrm{n}}}\right)^{\star} \\
            I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}

        And the following (delta loads):

        .. math::
            I_{\mathrm{ab}} &= \left(\frac{S_{\mathrm{ab}}}{V_{\mathrm{a}}-V_{\mathrm{b}}}\right)^{\star} \\
            I_{\mathrm{bc}} &= \left(\frac{S_{\mathrm{bc}}}{V_{\mathrm{b}}-V_{\mathrm{c}}}\right)^{\star} \\
            I_{\mathrm{ca}} &= \left(\frac{S_{\mathrm{ca}}}{V_{\mathrm{c}}-V_{\mathrm{a}}}\right)^{\star}

        Args:
            id:
                The unique id of the load.

            n:
                The number of ports (phases) of the load.

            bus:
                The bus to connect the load to.

            value:
                A sequence of complex values representing the apparent power of each phase.

            connection:
                The connection type of the load. Can be ``"star"`` or ``"delta"``.
        """
        return cls(id, n=n, bus=bus, value=power, type="power", connection=connection, **kwargs)

    @classmethod
    def constant_admittance(
        cls,
        id: Any,
        n: int,
        bus: Bus,
        admittance: Sequence[complex],
        connection: Connection = "star",
        **kwargs: Any,
    ) -> "Load":
        r"""A constant admittance load.

        A constant admittance load is a load whose power value is proportional to the square of the
        voltage. It is characterized its admittance.

        The equations are the following (star loads):

        .. math::
            I_{\mathrm{abc}} &= Y_{\mathrm{abc}}\left(V_{\mathrm{abc}}-V_{\mathrm{n}}\right) \\
            I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}

        And the following (delta loads):

        .. math::
            I_{\mathrm{ab}} &= Y_{\mathrm{ab}}\left(V_{\mathrm{a}}-V_{\mathrm{b}}\right) \\
            I_{\mathrm{bc}} &= Y_{\mathrm{bc}}\left(V_{\mathrm{b}}-V_{\mathrm{c}}\right) \\
            I_{\mathrm{ca}} &= Y_{\mathrm{ca}}\left(V_{\mathrm{c}}-V_{\mathrm{a}}\right)

        Args:
            id:
                The unique id of the load.

            n:
                The number of ports (phases) of the load.

            bus:
                The bus to connect the load to.

            value:
                A sequence of complex values representing the admittance of each phase.

            connection:
                The connection type of the load. Can be ``"star"`` or ``"delta"``.
        """
        return cls(id, n=n, bus=bus, value=admittance, type="admittance", connection=connection, **kwargs)

    @classmethod
    def constant_impedance(
        cls,
        id: Any,
        n: int,
        bus: Bus,
        impedance: Sequence[complex],
        connection: Connection = "star",
        **kwargs: Any,
    ) -> "Load":
        r"""A constant impedance load.

        A constant impedance load is a load whose power value is proportional to the square of the
        voltage. It is characterized its impedance.

        The equations are the following (star loads):

        .. math::
            I_{\mathrm{abc}} &= Y_{\mathrm{abc}}\left(V_{\mathrm{abc}}-V_{\mathrm{n}}\right) \\
            I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}

        And the following (delta loads):

        .. math::
            I_{\mathrm{ab}} &= Y_{\mathrm{ab}}\left(V_{\mathrm{a}}-V_{\mathrm{b}}\right) \\
            I_{\mathrm{bc}} &= Y_{\mathrm{bc}}\left(V_{\mathrm{b}}-V_{\mathrm{c}}\right) \\
            I_{\mathrm{ca}} &= Y_{\mathrm{ca}}\left(V_{\mathrm{c}}-V_{\mathrm{a}}\right)

        Args:
            id:
                The unique id of the load.

            n:
                The number of ports (phases) of the load.

            bus:
                The bus to connect the load to.

            value:
                A sequence of complex values representing the impedance of each phase.

            connection:
                The connection type of the load. Can be ``"star"`` or ``"delta"``.
        """
        return cls(id, n=n, bus=bus, value=impedance, type="impedance", connection=connection, **kwargs)

    def add_control(self, parameters: list[FlexibleParameter]) -> None:
        """Make the load flexible load i.e. a load with control.

        .. note::
            Only constant power loads with star connection can be made flexible.

        Args:
            parameters:
                List of flexible parameters for each phase.
        """
        if self.type != "power" or not self._function.startswith("y"):
            msg = "Flexible parameters are only available for power loads (star connection)"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)

        if len(parameters) != self._dimension:
            msg = f"Incorrect number of parameters: {len(parameters)} instead of {self._dimension}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)

        for power, parameter in zip(self.value, parameters):
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
        self.flexible_parameters = parameters

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any], bus: Bus) -> "Load":
        if data["function"].startswith(("ys", "ds", "flexible")):
            # Power load
            s = data["powers"]
            powers = [complex(*s["sa"]), complex(*s["sb"]), complex(*s["sc"])]
            if data["function"].startswith("ds"):
                return cls.constant_power(id=data["id"], n=3, bus=bus, power=powers, connection="delta")
            else:
                load = cls.constant_power(id=data["id"], n=4, bus=bus, power=powers)
                if data["function"] == "flexible":
                    parameters = [FlexibleParameter.from_dict(param) for param in data["parameters"]]
                    load.add_control(parameters)
                return load
        elif data["function"].startswith(("yy", "dy")):
            # Admittance load
            y = data["admittances"]
            admittances = [complex(*y["ya"]), complex(*y["yb"]), complex(*y["yc"])]
            if data["function"].startswith("yy"):
                return cls.constant_admittance(id=data["id"], n=4, bus=bus, admittance=admittances)
            else:
                return cls.constant_admittance(id=data["id"], bus=bus, admittance=admittances, connection="delta")
        elif data["function"].startswith(("yz", "dz")):
            # Impedance load
            z = data["impedances"]
            impedances = [complex(*z["za"]), complex(*z["zb"]), complex(*z["zc"])]
            if data["function"].startswith("yz"):
                return cls.constant_impedance(id=data["id"], n=4, bus=bus, impedance=impedances)
            else:
                return cls.constant_impedance(id=data["id"], bus=bus, impedance=impedances, connection="delta")
        else:
            msg = f"Unknown load type for load {data['id']}: {data['function']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)

    def to_dict(self) -> dict[str, Any]:
        # function was computed using self.bus.n instead of self.n for star loads!!!
        res = {"id": self.id, "function": self._function}
        if self.is_flexible():
            res["function"] = "flexible"  # overwrite the function
            res["parameters"] = [param.to_dict() for param in self.flexible_parameters]
        a, b, c = self.value
        if self.type == "power":
            res["powers"] = {"sa": [a.real, a.imag], "sb": [b.real, b.imag], "sc": [c.real, c.imag]}
        elif self.type == "admittance":
            res["admittances"] = {"ya": [a.real, a.imag], "yb": [b.real, b.imag], "yc": [c.real, c.imag]}
        elif self.type == "impedance":
            res["impedances"] = {"za": [a.real, a.imag], "zb": [b.real, b.imag], "zc": [c.real, c.imag]}
        return res
