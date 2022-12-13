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


def _temporarily_check_only_s_or_z(
    s: Optional[Sequence[complex]], i: Optional[Sequence[complex]], z: Optional[Sequence[complex]]
) -> None:
    # Temporarily block loads that are not yet available until we implement the full load equation
    # Remove this check later

    # Constant current loads are not implemented
    if i is not None:
        raise RoseauLoadFlowException(
            msg=(
                "Load currently expects s (constant power) or z (constant impedance), "
                "i (constant current) is not implemented"
            ),
            code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE,
        )

    # Mixed constant power and constant impedance loads are not implemented
    if s is not None and z is not None:
        raise RoseauLoadFlowException(
            msg="Load currently expects only s (constant power) or z (constant impedance), not both.",
            code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE,
        )
    elif s is None and z is None:
        raise RoseauLoadFlowException(
            msg="Load currently expects either s (constant power) or z (constant impedance), non given.",
            code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE,
        )


class Load(Element, JsonMixin):
    """An electrical load."""

    def __init__(
        self,
        id: Any,
        n: int,
        bus: Bus,
        s: Optional[Sequence[complex]] = None,
        i: Optional[Sequence[complex]] = None,
        z: Optional[Sequence[complex]] = None,
        **kwargs: Any,
    ) -> None:
        r"""Generic electrical load constructor.

        A load is characterized by its complex power `S`, current `I` and impedance `Z`. The ``s``
        parameter is the constant power part of the load, the ``i`` parameter is the constant
        current part, and the ``z`` parameter is the constant impedance part. The load is then
        characterized by the following equations:

        1. Star loads (aka Wye loads):

            .. math::
                \mathbf{I}_{\mathrm{abc}} &=
                    \left(\frac{S_{\mathrm{abc}}}{V_{\mathrm{abc}}-V_{\mathrm{n}}}\right)^{\star}
                    + I_{\mathrm{abc}}
                    + \left(\frac{V_{\mathrm{abc}}-V_{\mathrm{n}}}{Z_{\mathrm{abc}}}\right)^{\star} \\
                \mathbf{I}_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}

        2. Delta loads:

            .. math::
                \mathbf{I}_{\mathrm{ab}} &=
                    \left(\frac{S_{\mathrm{ab}}}{V_{\mathrm{a}}-V_{\mathrm{b}}}\right)^{\star}
                    + I_{\mathrm{ab}}
                    + \left(\frac{V_{\mathrm{a}}-V_{\mathrm{b}}}{Z_{\mathrm{ab}}}\right)^{\star} \\
                \mathbf{I}_{\mathrm{bc}} &=
                    \left(\frac{S_{\mathrm{bc}}}{V_{\mathrm{b}}-V_{\mathrm{c}}}\right)^{\star}
                    + I_{\mathrm{bc}}
                    + \left(\frac{V_{\mathrm{b}}-V_{\mathrm{c}}}{Z_{\mathrm{bc}}}\right)^{\star} \\
                \mathbf{I}_{\mathrm{ca}} &=
                    \left(\frac{S_{\mathrm{ca}}}{V_{\mathrm{c}}-V_{\mathrm{a}}}\right)^{\star}
                    + I_{\mathrm{ca}}
                    + \left(\frac{V_{\mathrm{b}}-V_{\mathrm{c}}}{Z_{\mathrm{ca}}}\right)^{\star}

        .. important::
            The full load equation is not implemented yet. Only constant power loads or constant
            impedance loads are currently supported. Use either the ``s`` or ``z`` parameter, but
            not both.

        Args:
            id:
                The unique id of the load.

            n:
                The number of ports (phases) of the load.

            bus:
                The bus to connect the load to.

            s:
                An optional sequence of complex values of the apparent powers of each phase.

            i:
                An optional sequence of complex values of the currents of each phase.
                (This option is not implemented yet.)

            z:
                An optional sequence of complex values of the impedances of each phase.
        """
        super().__init__(**kwargs)
        self.connected_elements = [bus]
        bus.connected_elements.append(self)

        # Element attributes
        self.id = id
        self.n = n
        self.bus = bus
        self._currents = None

        # Load equation
        _temporarily_check_only_s_or_z(s=s, i=i, z=z)
        self.s = self._clean_value(s, type="s") if s is not None else None
        self.i = self._clean_value(i, type="i") if i is not None else None
        self.z = self._clean_value(z, type="z") if z is not None else None

        # Control
        self.flexible_parameters: Optional[list[FlexibleParameter]] = None
        self._powers = None

    def _clean_value(self, value: Sequence[complex], type: Literal["s", "z", "i"]) -> Sequence[complex]:
        if isinstance(value, Quantity):
            unit = {"s": "VA", "z": "ohm", "i": "A"}[type]
            value = value.m_as(unit)
        if len(value) != 3:  # currently only three, later it will depend on the phases
            error_code = RoseauLoadFlowExceptionCode.from_string(f"BAD_{type.upper()}_SIZE")
            qty = {"s": "power", "z": "impedance", "i": "current"}[type]
            msg = f"Incorrect number of {qty}: {len(value)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=error_code)
        if type == "z" and np.isclose(value, 0).any():
            msg = f"An impedance for load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.id!r}, n={self.n}, bus={self.bus.id!r})"

    def __str__(self) -> str:
        return f"id={self.id!r} - n={self.n}"

    @property
    @ureg.wraps("A", None, strict=False)
    def currents(self) -> np.ndarray:
        """An array of the actual currents of each phase of the load as computed by the load flow."""
        return self._currents

    @currents.setter
    def currents(self, value: np.ndarray) -> None:
        self._currents = value

    @property
    @ureg.wraps("VA", None, strict=False)
    def powers(self) -> np.ndarray:
        """An array of the actual powers of each phase of the load as computed by the load flow."""
        if not self.is_flexible():
            msg = f"Cannot get the power of a non flexible load {self.id!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        return self._powers

    @powers.setter
    def powers(self, value: np.ndarray) -> None:
        if not self.is_flexible():
            msg = f"Cannot set the power of a non flexible load {self.id!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        self._powers = value

    @ureg.wraps(None, (None, "VA"), strict=False)
    def update_powers(self, value: Sequence[complex]) -> None:
        """Update the constant power of the load."""
        _temporarily_check_only_s_or_z(s=value, i=self.i, z=self.z)
        self.s = self._clean_value(value, type="s")

    @ureg.wraps(None, (None, "A"), strict=False)
    def update_currents(self, value: Sequence[complex]) -> None:
        """Update the constant current of the load."""
        _temporarily_check_only_s_or_z(s=self.s, i=value, z=self.z)
        self.i = self._clean_value(value, type="i")

    @ureg.wraps(None, (None, "ohm"), strict=False)
    def update_impedances(self, value: Sequence[complex]) -> None:
        """Update the constant impedance of the load."""
        _temporarily_check_only_s_or_z(s=self.s, i=self.i, z=value)
        self.z = self._clean_value(value, type="z")

    def is_flexible(self) -> bool:
        """Check if the load is flexible.

        Returns:
            True if the load is flexible, False otherwise.
        """
        return self.flexible_parameters is not None

    def add_control(self, parameters: list[FlexibleParameter]) -> None:
        """Make the load flexible load i.e. a load with control.

        .. important::
            Only constant power loads with star connection currently can be made flexible.

        Args:
            parameters:
                List of flexible parameters for each phase.
        """
        if self.s is None or self.n != 4:
            msg = "Flexible parameters are currently only available for power loads with neutral connection"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)

        if len(parameters) != 3:  # currently only three, later it will depend on the phases
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
        self.flexible_parameters = parameters

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any], bus: Bus) -> "Load":
        s = data.get("powers")
        i = data.get("currents")
        z = data.get("impedances")
        const_s = [complex(*s["sa"]), complex(*s["sb"]), complex(*s["sc"])] if s is not None else None
        const_i = [complex(*i["ia"]), complex(*i["ib"]), complex(*i["ic"])] if i is not None else None
        const_z = [complex(*z["za"]), complex(*z["zb"]), complex(*z["zc"])] if z is not None else None

        load = Load(id=data["id"], n=len(data["phases"]), bus=bus, s=const_s, i=const_i, z=const_z)

        params_list = data.get("parameters")
        if params_list is not None:
            parameters = [FlexibleParameter.from_dict(param) for param in params_list]
            load.add_control(parameters)

        return load

    def to_dict(self) -> dict[str, Any]:
        _temporarily_check_only_s_or_z(s=self.s, i=self.i, z=self.z)
        res = {"id": self.id, "phases": "abc" if self.n == 3 else "abcn"}
        if self.is_flexible():
            res["parameters"] = [param.to_dict() for param in self.flexible_parameters]
        if self.s is not None:
            a, b, c = self.s
            res["powers"] = {"sa": [a.real, a.imag], "sb": [b.real, b.imag], "sc": [c.real, c.imag]}
        elif self.i is not None:
            a, b, c = self.i
            res["currents"] = {"ia": [a.real, a.imag], "ib": [b.real, b.imag], "ic": [c.real, c.imag]}
        elif self.z is not None:
            a, b, c = self.z
            res["impedances"] = {"za": [a.real, a.imag], "zb": [b.real, b.imag], "zc": [c.real, c.imag]}
        return res
