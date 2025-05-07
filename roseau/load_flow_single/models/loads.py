import cmath
import logging
from abc import ABC
from typing import Final

import numpy as np
from typing_extensions import TypeVar

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Complex, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyAdmittanceLoad, CyCurrentLoad, CyFlexibleLoad, CyLoad, CyPowerLoad
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.connectables import AbstractConnectable
from roseau.load_flow_single.models.flexible_parameters import FlexibleParameter

logger = logging.getLogger(__name__)

_CyL_co = TypeVar("_CyL_co", bound=CyLoad, default=CyLoad, covariant=True)


class AbstractLoad(AbstractConnectable[_CyL_co], ABC):
    """An abstract class of an electric load."""

    element_type: Final = "load"

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
        super().__init__(id, bus)

    @property
    def is_flexible(self) -> bool:
        """Whether the load is flexible or not. Only :class:`PowerLoad` can be flexible."""
        return False

    def _validate_value(self, value: Complex) -> complex:
        return complex(value)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> "AbstractLoad":
        load_type = data["type"]
        if load_type == "power":
            power = complex(data["power"][0], data["power"][1])
            if (fp_data := data.get("flexible_param")) is not None:
                fp = FlexibleParameter.from_dict(data=fp_data, include_results=include_results)
            else:
                fp = None
            self = PowerLoad(id=data["id"], bus=data["bus"], power=power, flexible_param=fp)
        elif load_type == "current":
            current = complex(data["current"][0], data["current"][1])
            self = CurrentLoad(id=data["id"], bus=data["bus"], current=current)
        elif load_type == "impedance":
            impedance = complex(data["impedance"][0], data["impedance"][1])
            self = ImpedanceLoad(id=data["id"], bus=data["bus"], impedance=impedance)
        else:
            msg = f"Unknown load type {load_type!r} for load {data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        self._parse_results_from_dict(data, include_results=include_results)
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        value: complex = getattr(self, f"_{self.type}")
        load_dict = {
            **super()._to_dict(include_results=include_results),
            f"{self.type}": [value.real, value.imag],
        }
        if include_results:
            load_dict["results"] = load_dict.pop("results")  # move results to the end
        return load_dict


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

        if bus.short_circuit:
            msg = (
                f"The power load {self.id!r} is connected on bus {bus.id!r} that already has a short-circuit. "
                f"It makes the short-circuit calculation impossible."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)

        self._flexible_param = flexible_param
        self.power = power

        if self.is_flexible:
            self._set_cy_element(
                CyFlexibleLoad(
                    n=self._n,
                    powers=np.array([self._power / 3.0], dtype=np.complex128),
                    parameters=np.array([flexible_param._cy_fp]),
                )
            )
        else:
            self._set_cy_element(CyPowerLoad(n=self._n, powers=np.array([self._power / 3.0], dtype=np.complex128)))
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
        if self._cy_initialized:
            self._cy_element.update_powers(np.array([self._power / 3.0], dtype=np.complex128))

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results=include_results)
        if self.flexible_param is not None:
            data["flexible_param"] = self.flexible_param.to_dict(include_results=include_results)
        if include_results:
            data["results"] = data.pop("results")  # move results to the end
        return data


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

        if bus.short_circuit:
            msg = (
                f"The current load {self.id!r} is connected on bus {bus.id!r} that already has a short-circuit. "
                f"It makes the short-circuit calculation impossible."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)

        self.current = current
        self._set_cy_element(CyCurrentLoad(n=self._n, currents=np.array([self._current], dtype=np.complex128)))
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
        if self._cy_initialized:
            self._cy_element.update_currents(np.array([self._current], dtype=np.complex128))


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
        self._set_cy_element(
            CyAdmittanceLoad(n=self._n, admittances=np.array([1.0 / self._impedance], dtype=np.complex128))
        )
        self._cy_connect()

    def _validate_value(self, value: Complex) -> complex:
        # A load cannot have a zero impedance
        if cmath.isclose(value, 0):
            msg = f"The impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return super()._validate_value(value)

    @property
    @ureg_wraps("ohm", (None,))
    def impedance(self) -> Q_[complex]:
        """The impedance of the load (Ohms).

        Setting the impedance will update the load's impedance and invalidate the network results.
        """
        return self._impedance

    @impedance.setter
    @ureg_wraps(None, (None, "ohm"))
    def impedance(self, value: Complex | Q_[Complex]) -> None:
        self._impedance = self._validate_value(value)
        self._invalidate_network_results()
        if self._cy_initialized:
            self._cy_element.update_admittances(np.array([1.0 / self._impedance], dtype=np.complex128))
