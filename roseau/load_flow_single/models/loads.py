import logging
from abc import ABC
from typing import ClassVar, Final, Literal, TypeVar

import numpy as np

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Complex, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyAdmittanceLoad, CyCurrentLoad, CyFlexibleLoad, CyLoad, CyPowerLoad
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.flexible_parameters import FlexibleParameter

logger = logging.getLogger(__name__)

_CyL = TypeVar("_CyL", bound=CyLoad)


class AbstractLoad(Element[_CyL], ABC):
    """An abstract class of an electric load."""

    type: ClassVar[Literal["power", "current", "impedance"]]

    def __init__(self, id: Id, bus: Bus) -> None:
        """AbstractLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.
        """
        if type(self) is AbstractLoad:
            raise TypeError("Can't instantiate abstract class AbstractLoad")
        super().__init__(id)
        self._connect(bus)

        self._bus = bus
        self._n = 2
        self._symbol = {"power": "S", "current": "I", "impedance": "Z"}[self.type]

        # Results
        self._res_current: complex | None = None
        self._res_voltage: complex | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"<{type(self).__name__}: id={self.id!r}, bus={bus_id!r}>"

    @property
    def bus(self) -> Bus:
        """The bus of the load."""
        return self._bus

    @property
    def is_flexible(self) -> bool:
        """Whether the load is flexible or not. Only :class:`PowerLoad` can be flexible."""
        return False

    def _refresh_results(self) -> None:
        self._res_current = self._cy_element.get_currents(self._n)[0]
        self._res_voltage = self._cy_element.get_potentials(self._n)[0] * SQRT3

    def _res_current_getter(self, warning: bool) -> complex:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_current, warning=warning)

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The load flow result of the load currents (A)."""
        return self._res_current_getter(warning=True)

    def _validate_value(self, value: Complex) -> complex:
        # A load cannot have any zero impedance
        if self.type == "impedance" and np.isclose(value, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return complex(value)

    def _res_voltage_getter(self, warning: bool) -> complex:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_voltage, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_voltage(self) -> Q_[complex]:
        """The load flow result of the load voltages (V)."""
        return self._res_voltage_getter(warning=True)

    def _res_power_getter(
        self, warning: bool, current: complex | None = None, voltage: complex | None = None
    ) -> complex:
        if current is None:
            current = self._res_current_getter(warning=warning)
            warning = False  # we warn only one
        if voltage is None:
            voltage = self._res_voltage_getter(warning=warning)
        return voltage * current.conjugate() * SQRT3

    @property
    @ureg_wraps("VA", (None,))
    def res_power(self) -> Q_[complex]:
        """The load flow result of the "line powers" flowing into the load (VA)."""
        return self._res_power_getter(warning=True)

    def _cy_connect(self) -> None:
        connections = []
        for i in range(self._n):
            connections.append((i, i))
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
            power = complex(data["power"][0], data["power"][1])
            if (fp_data := data.get("flexible_param")) is not None:
                fp = FlexibleParameter.from_dict(data=fp_data, include_results=include_results)
            else:
                fp = None
            self = PowerLoad(
                id=data["id"],
                bus=data["bus"],
                power=power,
                flexible_param=fp,
            )
        elif load_type == "current":
            current = complex(data["current"][0], data["current"][1])
            self = CurrentLoad(id=data["id"], bus=data["bus"], current=current)
        elif load_type == "impedance":
            impedance = complex(data["impedance"][0], data["impedance"][1])
            self = ImpedanceLoad(
                id=data["id"],
                bus=data["bus"],
                impedance=impedance,
            )
        else:
            msg = f"Unknown load type {load_type!r} for load {data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        if include_results and "results" in data:
            self._res_current = complex(data["results"]["current"][0], data["results"]["current"][1])
            self._res_voltage = complex(data["results"]["voltage"][0], data["results"]["voltage"][1])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        value: complex = getattr(self, f"_{self.type}")
        res = {"id": self.id, "bus": self.bus.id, "type": self.type, f"{self.type}": [value.real, value.imag]}
        if include_results:
            current = self._res_current_getter(warning=True)
            voltage = self._res_voltage_getter(warning=True)
            res["results"] = {"current": [current.real, current.imag], "voltage": [voltage.real, voltage.imag]}
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current = self._res_current_getter(warning)
        voltage = self._res_voltage_getter(warning=False)
        results = {
            "id": self.id,
            "type": self.type,
            "current": [current.real, current.imag],
            "voltage": [voltage.real, voltage.imag],
        }
        if full:
            power = self._res_power_getter(warning=False, current=current, voltage=voltage)
            results["power"] = [power.real, power.imag]
        return results


class PowerLoad(AbstractLoad[CyPowerLoad | CyFlexibleLoad]):
    """A constant power load."""

    type: Final = "power"

    def __init__(
        self, id: Id, bus: Bus, *, power: Complex | Q_[Complex], flexible_param: FlexibleParameter | None = None
    ) -> None:
        """PowerLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            power:
                A single power value, either complex value (VA) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex value.

            flexible_param:
                A :class:`FlexibleParameters` object. When provided, the load is considered as flexible
                (or controllable) and the parameters are used to compute the flexible power of the load.
        """
        super().__init__(id=id, bus=bus)

        self._flexible_param = flexible_param
        self.power = power

        if self.is_flexible:
            cy_parameters = np.array([flexible_param._cy_fp])  # type: ignore
            self._cy_element = CyFlexibleLoad(
                n=self._n, powers=np.array([self._power / 3.0], dtype=np.complex128), parameters=cy_parameters
            )
        else:
            self._cy_element = CyPowerLoad(n=self._n, powers=np.array([self._power / 3.0], dtype=np.complex128))
        self._cy_connect()

    @property
    def flexible_param(self) -> FlexibleParameter | None:
        return self._flexible_param

    @property
    def is_flexible(self) -> bool:
        return self._flexible_param is not None

    @property
    @ureg_wraps("VA", (None,))
    def power(self) -> Q_[complex]:
        """The power of the load (VA).

        Setting the power will update the load's power values and invalidate the network results.
        """
        return self._power

    @power.setter
    @ureg_wraps(None, (None, "VA"))
    def power(self, value: Complex | Q_[Complex]) -> None:
        value = self._validate_value(value)
        if self._flexible_param is not None:
            power, fp = value, self._flexible_param
            if fp.control_p.type != "constant" or fp.control_q.type != "constant":
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
        self._power = value
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_powers(np.array([self._power / 3.0], dtype=np.complex128))

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        res = super()._to_dict(include_results=include_results)
        if self.flexible_param is not None:
            res["flexible_param"] = self.flexible_param.to_dict(include_results=include_results)
        return res


class CurrentLoad(AbstractLoad[CyCurrentLoad]):
    """A constant current load."""

    type: Final = "current"

    def __init__(self, id: Id, bus: Bus, *, current: Complex | Q_[Complex]) -> None:
        """CurrentLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            current:
                A single current value, either complex value (A) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex value.
        """
        super().__init__(id=id, bus=bus)
        self.current = current
        self._cy_element = CyCurrentLoad(n=self._n, currents=np.array([self._current], dtype=np.complex128))
        self._cy_connect()

    @property
    @ureg_wraps("A", (None,))
    def current(self) -> Q_[complex]:
        """The current of the load (Amps).

        Setting the current will update the load's current and invalidate the network results.
        """
        return self._current

    @current.setter
    @ureg_wraps(None, (None, "A"))
    def current(self, value: Complex | Q_[Complex]) -> None:
        self._current = self._validate_value(value)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_currents(self._current)


class ImpedanceLoad(AbstractLoad[CyAdmittanceLoad]):
    """A constant impedance load."""

    type: Final = "impedance"

    def __init__(self, id: Id, bus: Bus, *, impedance: Complex | Q_[Complex]) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            impedance:
                A single impedance value, either complex value (Ohms) or a :class:`Quantity <roseau.load_flow.units.Q_>`
                of complex value.
        """
        super().__init__(id=id, bus=bus)
        self.impedance = impedance
        self._cy_element = CyAdmittanceLoad(
            n=self._n, admittances=np.array([1.0 / self._impedance], dtype=np.complex128)
        )
        self._cy_connect()

    @property
    @ureg_wraps("ohm", (None,))
    def impedance(self) -> Q_[complex]:
        """The impedance of the load (Ohms).

        Setting the impedance will update the load's impedance and invalidate the network results.
        """
        return self._impedance

    @impedance.setter
    @ureg_wraps(None, (None, "ohm"))
    def impedance(self, impedance: Complex | Q_[Complex]) -> None:
        self._impedance = self._validate_value(impedance)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_admittances(1.0 / self._impedance)
