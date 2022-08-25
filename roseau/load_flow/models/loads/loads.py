import logging
from abc import ABCMeta
from collections.abc import Sequence
from typing import Any, Optional

import numpy as np
from pint import Quantity

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import AbstractBus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class AbstractLoad(Element, JsonMixin, metaclass=ABCMeta):
    """An abstract class to depict a load."""

    power_load_class: Optional[type["PowerLoad"]] = None
    delta_power_load_class: Optional[type["DeltaPowerLoad"]] = None
    impedance_load_class: Optional[type["ImpedanceLoad"]] = None
    delta_impedance_load_class: Optional[type["DeltaImpedanceLoad"]] = None
    admittance_load_class: Optional[type["AdmittanceLoad"]] = None
    delta_admittance_load_class: Optional[type["DeltaAdmittanceLoad"]] = None
    flexible_load_class: Optional[type["FlexibleLoad"]] = None

    def __init__(self, id: Any, n: int, bus: AbstractBus, **kwargs) -> None:
        """Load constructor.

        Args:
            id:
                The id of the load.

            n:
                Number of ports

            bus:
                Bus to be attached to.
        """
        super().__init__(**kwargs)
        self.connected_elements = [bus]
        bus.connected_elements.append(self)

        self.id = id
        self.n = n
        self.bus = bus
        self._currents = None

    def __str__(self) -> str:
        return f"id={self.id} - n={self.n}"

    @property
    @ureg.wraps("A", None, strict=False)
    def currents(self) -> np.ndarray:
        """Get the actual currents of the load.

        Returns:
            An array containing the actual currents of each phase.
        """
        return self._currents

    @currents.setter
    def currents(self, value: np.ndarray):
        self._currents = value

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data, bus):
        if data["function"] == "flexible":
            return cls.flexible_load_class.from_dict(data=data, bus=bus)
        if "ys" in data["function"] or "ds" in data["function"]:
            s = data["powers"]
            powers = [s["sa"][0] + 1j * s["sa"][1], s["sb"][0] + 1j * s["sb"][1], s["sc"][0] + 1j * s["sc"][1]]
            if "ys" in data["function"]:
                return cls.power_load_class(id=data["id"], n=4, bus=bus, s=powers)
            else:
                return cls.delta_power_load_class(id=data["id"], bus=bus, s=powers)
        elif "yy" in data["function"] or "dy" in data["function"]:
            y = data["admittances"]
            admittances = [y["ya"][0] + 1j * y["ya"][1], y["yb"][0] + 1j * y["yb"][1], y["yc"][0] + 1j * y["yc"][1]]
            if "yy" in data["function"]:
                return cls.admittance_load_class(id=data["id"], n=4, bus=bus, y=admittances)
            else:
                return cls.delta_admittance_load_class(id=data["id"], bus=bus, y=admittances)
        elif "yz" in data["function"] or "dz" in data["function"]:
            z = data["impedances"]
            impedances = [z["za"][0] + 1j * z["za"][1], z["zb"][0] + 1j * z["zb"][1], z["zc"][0] + 1j * z["zc"][1]]
            if "yz" in data["function"]:
                return cls.impedance_load_class(id=data["id"], n=4, bus=bus, z=impedances)
            else:
                return cls.delta_impedance_load_class(id=data["id"], bus=bus, z=impedances)
        else:
            msg = f"Unknown load type for load {data['id']}: {data['function']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)


class PowerLoad(AbstractLoad):
    """A constant power load.

    The equations are the following (star loads):

    .. math::
        I_{\\mathrm{abc}}=\\left(\frac{S_{\\mathrm{abc}}}{V_{\\mathrm{abc}}-V_{\\mathrm{n}}}\right)^{\\star}
        I_{\\mathrm{n}}=-\\sum_{p\\in\\{\\mathrm{a},\\mathrm{b},\\mathrm{c}\\}}I_{p}
    """

    def __init__(self, id: Any, n: int, bus: AbstractBus, s: Sequence[complex], **kwargs) -> None:
        """PowerLoad constructor.

        Args:
            id:
                The id of the load.

            n:
                Number of ports

            bus:
                Bus to be attached to

            s:
                List of power for each phase (VA).
        """
        super().__init__(id=id, n=n, bus=bus, **kwargs)
        if len(s) != n - 1:
            msg = f"Incorrect number of powers: {len(s)} instead of {n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_SIZE)

        if isinstance(s, Quantity):
            s = s.m_as("VA")
        self.s = s

    @ureg.wraps(None, (None, "VA"), strict=False)
    def update_powers(self, s: Sequence[complex]) -> None:
        """Change the power of the load.

        Args:
            s:
                The new powers to set (VA).
        """
        if len(s) != self.n - 1:
            msg = f"Incorrect number of powers: {len(s)} instead of {self.n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_SIZE)
        self.s = s

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        if self.bus.n == 3:
            load_type = "ys"
        else:
            load_type = "ys_neutral"
        sa, sb, sc = self.s
        return {
            "id": self.id,
            "function": load_type,
            "powers": {
                "sa": [sa.real, sa.imag],
                "sb": [sb.real, sb.imag],
                "sc": [sc.real, sc.imag],
            },
        }


class DeltaPowerLoad(AbstractLoad):
    """A constant power load.

    The equations are the following (delta loads):

    .. math::
        I_{\\mathrm{ab}}=\\left(\frac{S_{\\mathrm{ab}}}{V_{\\mathrm{a}}-V_{\\mathrm{b}}}\right)^{\\star}
        I_{\\mathrm{bc}}=\\left(\frac{S_{\\mathrm{bc}}}{V_{\\mathrm{b}}-V_{\\mathrm{c}}}\right)^{\\star}
        I_{\\mathrm{ca}}=\\left(\frac{S_{\\mathrm{ca}}}{V_{\\mathrm{c}}-V_{\\mathrm{a}}}\right)^{\\star}
    """

    def __init__(self, id: Any, bus: AbstractBus, s: Sequence[complex], **kwargs) -> None:
        """PowerLoad constructor.

        Args:
            id:
                The id of the load.

            bus:
                Bus to be attached to

            s:
                List of power for each phase (VA).
        """
        if "n" in kwargs:
            kwargs.pop("n")
        super().__init__(id=id, n=3, bus=bus, **kwargs)
        if len(s) != 3:
            msg = f"Incorrect number of powers: {len(s)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_SIZE)

        if isinstance(s, Quantity):
            s = s.m_as("VA")
        self.s = s

    @ureg.wraps(None, (None, "VA"), strict=False)
    def update_powers(self, s: Sequence[complex]) -> None:
        """Change the power of the load.

        Args:
            s:
                The new powers to set (VA).
        """
        if len(s) != 3:
            msg = f"Incorrect number of powers: {len(s)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_SIZE)
        self.s = s

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        load_type = "ds"
        sa, sb, sc = self.s
        return {
            "id": self.id,
            "function": load_type,
            "powers": {
                "sa": [sa.real, sa.imag],
                "sb": [sb.real, sb.imag],
                "sc": [sc.real, sc.imag],
            },
        }


class AdmittanceLoad(AbstractLoad):
    """A constant admittance load.

    The equations are the following (star loads):

    .. math::
        I_{\\mathrm{abc}}=Y_{\\mathrm{abc}}\\left(V_{\\mathrm{abc}}-V_{\\mathrm{n}}\right)
        I_{\\mathrm{n}}=-\\sum_{p\\in\\{\\mathrm{a},\\mathrm{b},\\mathrm{c}\\}}I_{p}
    """

    def __init__(self, id: Any, n: int, bus: AbstractBus, y: Sequence[complex], **kwargs) -> None:
        """AdmittanceLoad constructor.

        Args:
            id:
                The id of the load.

            n:
                Number of ports.

            bus:
                Bus to be attached to.

            y:
                List of admittance for each phase (Siemens).
        """
        super().__init__(id=id, n=n, bus=bus, **kwargs)
        if len(y) != n - 1:
            msg = f"Incorrect number of admittance: {len(y)} instead of {n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SIZE)

        if isinstance(y, Quantity):
            y = y.m_as("S")

        self.y = y

    @ureg.wraps(None, (None, "S"), strict=False)
    def update_admittances(self, y: Sequence[complex]) -> None:
        """Change the admittances of the load

        Args:
            y:
                The new admittances to set (Siemens).
        """
        if len(y) != self.n - 1:
            msg = f"Incorrect number of admittances: {len(y)} instead of {self.n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SIZE)
        self.y = y

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        if self.bus.n == 3:
            load_type = "yy"
        else:
            load_type = "yy_neutral"
        ya, yb, yc = self.y
        return {
            "id": self.id,
            "function": load_type,
            "admittances": {
                "ya": [ya.real, ya.imag],
                "yb": [yb.real, yb.imag],
                "yc": [yc.real, yc.imag],
            },
        }


class DeltaAdmittanceLoad(AbstractLoad):
    """A constant admittance load.

    The equations are the following (delta loads):

    .. math::
        I_{\\mathrm{ab}}=Y_{\\mathrm{ab}}\\left(V_{\\mathrm{a}}-V_{\\mathrm{b}}\right)
        I_{\\mathrm{bc}}=Y_{\\mathrm{bc}}\\left(V_{\\mathrm{b}}-V_{\\mathrm{c}}\right)
        I_{\\mathrm{ca}}=Y_{\\mathrm{ca}}\\left(V_{\\mathrm{c}}-V_{\\mathrm{a}}\right)
    """

    def __init__(self, id: Any, bus: AbstractBus, y: Sequence[complex], **kwargs) -> None:
        """AdmittanceLoad constructor.

        Args:
            id:
                The id of the load.

            bus:
                Bus to be attached to.

            y:
                List of admittance for each phase (Siemens).
        """
        if "n" in kwargs:
            kwargs.pop("n")
        super().__init__(id=id, n=3, bus=bus, **kwargs)
        if len(y) != 3:
            msg = f"Incorrect number of admittance: {len(y)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SIZE)

        if isinstance(y, Quantity):
            y = y.m_as("S")

        self.y = y

    @ureg.wraps(None, (None, "S"), strict=False)
    def update_admittances(self, y: Sequence[complex]) -> None:
        """Change the admittances of the load

        Args:
            y:
                The new admittances to set (Siemens).
        """
        if len(y) != 3:
            msg = f"Incorrect number of admittances: {len(y)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SIZE)
        self.y = y

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        load_type = "dy"
        ya, yb, yc = self.y
        return {
            "id": self.id,
            "function": load_type,
            "admittances": {
                "ya": [ya.real, ya.imag],
                "yb": [yb.real, yb.imag],
                "yc": [yc.real, yc.imag],
            },
        }


class ImpedanceLoad(AbstractLoad):
    """Constant impedance loads.

    The equations are the same as in the constance admittance load implementation.
    """

    def __init__(self, id: Any, n: int, bus: AbstractBus, z: Sequence[complex], **kwargs) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                The id of the load.

            n:
                Number of ports.

            bus:
                Bus to be attached to.

            z:
                List of impedance for each phase (Ohms).
        """
        super().__init__(id=id, n=n, bus=bus, **kwargs)
        if len(z) != n - 1:
            msg = f"Incorrect number of impedance: {len(z)} instead of {n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_SIZE)

        if isinstance(z, Quantity):
            z = z.m_as("ohm")

        for zi in z:
            if np.isclose(zi, 0):
                msg = f"An impedance for load {self.id!r} is null"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)

        self.z = z

    @ureg.wraps(None, (None, "ohm"), strict=False)
    def update_impedance(self, z: Sequence[complex]) -> None:
        """Change the admittances of the load

        Args:
            z:
                The new impedance to set (Ohms).
        """
        if len(z) != self.n - 1:
            msg = f"Incorrect number of impedance: {len(z)} instead of {self.n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_SIZE)

        for zi in z:
            if np.isclose(zi, 0):
                msg = f"An impedance for load {self.id!r} is null"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        self.z = z

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        if self.bus.n == 3:
            load_type = "yz"
        else:
            load_type = "yz_neutral"
        za, zb, zc = self.z
        return {
            "id": self.id,
            "function": load_type,
            "impedances": {
                "za": [za.real, za.imag],
                "zb": [zb.real, zb.imag],
                "zc": [zc.real, zc.imag],
            },
        }


class DeltaImpedanceLoad(AbstractLoad):
    """Constant delta impedance loads.

    The equations are the same as in the constance admittance delta load implementation.
    """

    def __init__(self, id: Any, bus: AbstractBus, z: Sequence[complex], **kwargs) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                The id of the load.

            bus:
                Bus to be attached to.

            z:
                List of impedance for each phase (Ohms).
        """
        if "n" in kwargs:
            kwargs.pop("n")
        super().__init__(id=id, n=3, bus=bus, **kwargs)
        if len(z) != 3:
            msg = f"Incorrect number of impedance: {len(z)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_SIZE)

        if isinstance(z, Quantity):
            z = z.m_as("ohm")

        for zi in z:
            if np.isclose(zi, 0):
                msg = f"An impedance for load {self.id!r} is null"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)

        self.z = z

    @ureg.wraps(None, (None, "ohm"), strict=False)
    def update_impedance(self, z: Sequence[complex]) -> None:
        """Change the admittances of the load

        Args:
            z:
                The new impedance to set (Ohms).
        """
        if len(z) != 3:
            msg = f"Incorrect number of impedance: {len(z)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_SIZE)

        for zi in z:
            if np.isclose(zi, 0):
                msg = f"An impedance for load {self.id!r} is null"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        self.z = z

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        load_type = "dz"
        za, zb, zc = self.z
        return {
            "id": self.id,
            "function": load_type,
            "impedances": {
                "za": [za.real, za.imag],
                "zb": [zb.real, zb.imag],
                "zc": [zc.real, zc.imag],
            },
        }


class FlexibleLoad(AbstractLoad):
    """A class to depict a flexible load i.e. a load with control."""

    flexible_parameter_class: type[FlexibleParameter] = FlexibleParameter

    def __init__(
        self, id: Any, n: int, bus: AbstractBus, s: Sequence[complex], parameters: list[FlexibleParameter], **kwargs
    ):
        """FlexibleLoad constructor.

        Args:
            id:
                The id of the load.

            n:
                Number of ports.

            bus:
                Bus to be attached to.

            s:
                List of theoretic powers for each phase.

            parameters:
                List of flexible parameters for each phase.
        """
        super().__init__(id=id, n=n, bus=bus, **kwargs)
        if len(s) != n - 1:
            msg = f"Incorrect number of powers: {len(s)} instead of {n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_SIZE)
        if len(parameters) != n - 1:
            msg = f"Incorrect number of parameters: {len(parameters)} instead of {n}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)

        if isinstance(s, Quantity):
            s = s.m_as("VA")

        for power, parameter in zip(s, parameters):
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

        self.s = s
        self.parameters = parameters
        self._powers = None

    def update_powers(self, s: Sequence[complex]) -> None:
        """Change the power of the load.

        Args:
            s:
                the new powers to set (Volts).
        """
        self.s = s

    @property
    @ureg.wraps("VA", None, strict=False)
    def powers(self) -> np.ndarray:
        """Compute the actual power consumed by the loads.

        Returns:
            An array containing the actual powers of each phase (VA)
        """
        return self._powers

    @powers.setter
    def powers(self, value: np.ndarray):
        self._powers = value

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any], bus: AbstractBus) -> "FlexibleLoad":
        s = data["powers"]
        powers = [s["sa"][0] + 1j * s["sa"][1], s["sb"][0] + 1j * s["sb"][1], s["sc"][0] + 1j * s["sc"][1]]
        parameters = list()
        for parameter in data["parameters"]:
            parameters.append(cls.flexible_parameter_class.from_dict(parameter))
        return cls(id=data["id"], n=4, bus=bus, s=powers, parameters=parameters)

    def to_dict(self) -> dict[str, Any]:
        parameter_res = []
        for parameter in self.parameters:
            parameter_res.append(parameter.to_dict())
        sa, sb, sc = self.s
        return {
            "id": self.id,
            "function": "flexible",
            "powers": {
                "sa": [sa.real, sa.imag],
                "sb": [sb.real, sb.imag],
                "sc": [sc.real, sc.imag],
            },
            "parameters": parameter_res,
        }


AbstractLoad.power_load_class = PowerLoad
AbstractLoad.power_load_class = DeltaPowerLoad
AbstractLoad.impedance_load_class = ImpedanceLoad
AbstractLoad.impedance_load_class = DeltaImpedanceLoad
AbstractLoad.admittance_load_class = AdmittanceLoad
AbstractLoad.admittance_load_class = DeltaAdmittanceLoad
AbstractLoad.flexible_load_class = FlexibleLoad
