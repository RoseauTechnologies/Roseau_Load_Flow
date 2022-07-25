import logging
from abc import ABCMeta
from typing import Any, Sequence

from roseau.load_flow.models.buses.buses import AbstractBus
from roseau.load_flow.models.core.core import Element
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.utils.exceptions import ThundersIOError, ThundersValueError
from roseau.load_flow.utils.json_mixin import JsonMixin

logger = logging.getLogger(__name__)


class AbstractLoad(Element, JsonMixin, metaclass=ABCMeta):
    def __init__(self, id_: Any, n: int, bus: AbstractBus) -> None:
        """Load constructor.

        Args:
            id_:
                The id of the load.

            n:
                Number of ports

            bus:
                Bus to be attached to.
        """
        super().__init__()
        self.connected_elements = [bus]
        bus.connected_elements.append(self)

        self.id = id_
        self.n = n
        self.bus = bus

    @staticmethod
    def from_dict(data, bus):
        if data["function"] == "flexible":
            return FlexibleLoad.from_dict(data=data, bus=bus)
        if "ys" in data["function"]:
            s = data["powers"]
            powers = [s["sa"][0] + 1j * s["sa"][1], s["sb"][0] + 1j * s["sb"][1], s["sc"][0] + 1j * s["sc"][1]]
            return PowerLoad(id_=data["id"], n=4, bus=bus, s=powers)
        elif "yy" in data["function"]:
            y = data["admittances"]
            admittances = [y["ya"][0] + 1j * y["ya"][1], y["yb"][0] + 1j * y["yb"][1], y["yc"][0] + 1j * y["yc"][1]]
            return AdmittanceLoad(id_=data["id"], n=4, bus=bus, y=admittances)
        elif "yz" in data["function"]:
            z = data["impedances"]
            impedances = [z["za"][0] + 1j * z["za"][1], z["zb"][0] + 1j * z["zb"][1], z["zc"][0] + 1j * z["zc"][1]]
            return ImpedanceLoad(id_=data["id"], n=4, bus=bus, z=impedances)
        else:
            raise ThundersIOError(f"Unknown load type for load {data['id']}: {data['function']}")

    def __str__(self) -> str:
        return f"id={self.id} - n={self.n}"


class PowerLoad(AbstractLoad):
    def __init__(self, id_: Any, n: int, bus: AbstractBus, s: Sequence[complex]) -> None:
        """PowerLoad constructor.

        Args:
            id_:
                The id of the load.

            n:
                Number of ports

            bus:
                Bus to be attached to

            s:
                List of power for each phase (Volts).
        """
        super().__init__(id_=id_, n=n, bus=bus)
        if len(s) != n - 1:
            msg = f"Incorrect number of powers: {len(s)} instead of {n - 1}"
            logger.error(msg)
            raise ThundersValueError(msg)

        self.s = s

    def update_powers(self, powers: Sequence[complex]) -> None:
        """Change the power of the load.

        Args:
            powers:
                the new powers to set (Volts).
        """
        if len(powers) != self.n - 1:
            msg = f"Incorrect number of powers: {len(powers)} instead of {self.n - 1}"
            logger.error(msg)
            raise ThundersValueError(msg)
        self.s = powers

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


class AdmittanceLoad(AbstractLoad):
    def __init__(self, id_: Any, n: int, bus: AbstractBus, y: Sequence[complex]) -> None:
        """AdmittanceLoad constructor.

        Args:
            id_:
                The id of the load.

            n:
                Number of ports.

            bus:
                Bus to be attached to.

            y:
                List of admittance for each phase (Siemens).
        """
        super().__init__(id_=id_, n=n, bus=bus)
        if len(y) != n - 1:
            msg = f"Incorrect number of admittance: {len(y)} instead of {n - 1}"
            logger.error(msg)
            raise ThundersValueError(msg)

        self.y = y

    def update_admittances(self, admittances: Sequence[complex]) -> None:
        """Change the admittances of the load

        Args:
            admittances:
                The new admittances to set (Siemens).
        """
        if len(admittances) != self.n - 1:
            msg = f"Incorrect number of admittances: {len(admittances)} instead of {self.n - 1}"
            logger.error(msg)
            raise ThundersValueError(msg)
        self.y = admittances

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


class ImpedanceLoad(AbstractLoad):
    def __init__(self, id_: Any, n: int, bus: AbstractBus, z: Sequence[complex]) -> None:
        """ImpedanceLoad constructor.

        Args:
            id_:
                The id of the load.

            n:
                Number of ports.

            bus:
                Bus to be attached to.

            z:
                List of impedance for each phase (Ohms).
        """
        super().__init__(id_=id_, n=n, bus=bus)
        if len(z) != n - 1:
            msg = f"Incorrect number of impedance: {len(z)} instead of {n - 1}"
            logger.error(msg)
            raise ThundersValueError(msg)

        y = []
        for zi in z:
            if zi == 0.0:
                msg = f"An impedance for load {self.id!r} is null"
                logger.error(msg)
                raise ThundersValueError(msg)
            y.append(1.0 / zi)
        self.z = z

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

    def update_impedance(self, impedances: Sequence[complex]) -> None:
        """Change the admittances of the load

        Args:
            impedances:
                The new impedances to set (Ohms).
        """
        if len(impedances) != self.n - 1:
            msg = f"Incorrect number of impedance: {len(impedances)} instead of {self.n - 1}"
            logger.error(msg)
            raise ThundersValueError(msg)

        y = []
        for zi in impedances:
            if zi == 0.0:
                msg = f"An impedance for load {self.id!r} is null"
                logger.error(msg)
                raise ThundersValueError(msg)
            y.append(1.0 / zi)
        self.z = impedances


class FlexibleLoad(AbstractLoad):
    def __init__(
        self,
        id_: Any,
        n: int,
        bus: AbstractBus,
        s: Sequence[complex],
        parameters: list[FlexibleParameter],
    ):
        """FlexibleLoad constructor.

        Args:
            id_:
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
        super().__init__(id_=id_, n=n, bus=bus)
        if len(s) != n - 1:
            msg = f"Incorrect number of powers: {len(s)} instead of {n - 1}"
            logger.error(msg)
            raise ThundersValueError(msg)
        if len(parameters) != n - 1:
            msg = f"Incorrect number of parameters: {len(parameters)} instead of {n}"
            logger.error(msg)
            raise ThundersValueError(msg)

        for power, parameter in zip(s, parameters):
            if abs(power) > parameter.s_max and (
                parameter.control_p.type != "constant" or parameter.control_q.type != "constant"
            ):
                msg = f"The power is greater than the parameter s_max for flexible load {self.id!r}"
                logger.error(msg)
                raise ThundersValueError(msg)
            if parameter.control_p.type == "p_max_u_production" and power.real > 0:
                msg = f"There is a production control but a positive power for flexible load {self.id!r}"
                logger.error(msg)
                raise ThundersValueError(msg)
            if parameter.control_p.type == "p_max_u_consumption" and power.real < 0:
                msg = f"There is a consumption control but a negative power for flexible load {self.id!r}"
                logger.error(msg)
                raise ThundersValueError(msg)
            if parameter.control_p.type != "constant" and power.real == 0:
                msg = f"There is a P control but a null active power for flexible load {self.id!r}"
                logger.error(msg)
                raise ThundersValueError(msg)

        cy_parameters = []
        for p in parameters:
            cy_parameters.append(p.cy_fp)
        self.s = s
        self.parameters = parameters

    @classmethod
    def from_dict(cls, data: dict[str, Any], bus: AbstractBus) -> "FlexibleLoad":
        s = data["powers"]
        powers = [s["sa"][0] + 1j * s["sa"][1], s["sb"][0] + 1j * s["sb"][1], s["sc"][0] + 1j * s["sc"][1]]
        parameters = list()
        for parameter in data["parameters"]:
            parameters.append(FlexibleParameter.from_dict(parameter))
        return cls(id_=data["id"], n=4, bus=bus, s=powers, parameters=parameters)

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
