import logging
from abc import ABC
from typing import ClassVar, Final, Literal

import numpy as np

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.single.core import Element
from roseau.load_flow.typing import Complex, ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import (
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
        self._res_currents: ComplexArray | None = None
        self._res_potentials: ComplexArray | None = None

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
        self._res_currents = self._cy_element.get_currents(self._n)
        self._res_potentials = self._cy_element.get_potentials(self._n)

    def _res_currents_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[ComplexArray]:
        """The load flow result of the load currents (A)."""
        return self._res_currents_getter(warning=True)[0]

    def _validate_value(self, value: Complex) -> Complex:
        # A load cannot have any zero impedance
        if self.type == "impedance" and np.isclose(value, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return value

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_potentials, warning=warning)

    def _res_voltages_getter(self, warning: bool) -> ComplexArray:
        potentials = self._res_potentials_getter(warning)
        return np.array([potentials[0] - potentials[1]])

    @property
    @ureg_wraps("V", (None,))
    def res_voltage(self) -> Q_[ComplexArray]:
        """The load flow result of the load voltages (V)."""
        return self._res_voltages_getter(warning=True)[0]

    def _res_powers_getter(
        self, warning: bool, currents: ComplexArray | None = None, potentials: ComplexArray | None = None
    ) -> ComplexArray:
        if currents is None:
            currents = self._res_currents_getter(warning=warning)
            warning = False  # we warn only one
        if potentials is None:
            potentials = self._res_potentials_getter(warning=warning)
        return potentials * currents.conj()

    @property
    @ureg_wraps("VA", (None,))
    def res_power(self) -> Q_[ComplexArray]:
        """The load flow result of the "line powers" flowing into the load (VA)."""
        return self._res_powers_getter(warning=True)[0]

    def _cy_connect(self):
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
        # elif load_type == "current": TODO
        #     currents = [complex(i[0], i[1]) for i in data["currents"]]
        #     self = CurrentLoad(id=data["id"], bus=data["bus"], currents=currents, phases=data["phases"])
        # elif load_type == "impedance":
        #     impedances = [complex(z[0], z[1]) for z in data["impedances"]]
        #     self = ImpedanceLoad(
        #         id=data["id"],
        #         bus=data["bus"],
        #         impedances=impedances,
        #         phases=data["phases"],
        #         connect_neutral=data.get("connect_neutral"),
        #     )
        else:
            msg = f"Unknown load type {load_type!r} for load {data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        if include_results and "results" in data:
            self._res_currents = np.array(
                [complex(data["results"]["current"][0], data["results"]["current"][1])], dtype=np.complex128
            )
            self._res_potentials = np.array(
                [complex(data["results"]["potential"][0], data["results"]["potential"][1])], dtype=np.complex128
            )
            if "flexible_powers" in data["results"]:
                self._res_flexible_powers = np.array(
                    [complex(data["results"]["flexible_power"][0], data["results"]["flexible_power"][1])],
                    dtype=np.complex128,
                )

            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        complex_value = getattr(self, f"_{self.type}")
        res = {
            "id": self.id,
            "bus": self.bus.id,
            "type": self.type,
            f"{self.type}s": [complex_value.real, complex_value.imag],
        }
        if include_results:
            currents = self._res_currents_getter(warning=True)
            res["results"] = {"current": [[i.real, i.imag] for i in currents]}
            potentials = self._res_potentials_getter(warning=True)
            res["results"]["potential"] = [[v.real, v.imag] for v in potentials]
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents = self._res_currents_getter(warning)
        results = {
            "id": self.id,
            "type": self.type,
            "currents": [[i.real, i.imag] for i in currents],
        }
        potentials = self._res_potentials_getter(warning=False)
        results["potentials"] = [[v.real, v.imag] for v in potentials]
        if full:
            powers = self._res_powers_getter(warning=False, currents=currents, potentials=potentials)
            results["powers"] = [[s.real, s.imag] for s in powers]
        return results


class PowerLoad(AbstractLoad):
    """A constant power load."""

    type: Final = "power"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        power: Complex,
        flexible_param: FlexibleParameter | None = None,
    ) -> None:
        """PowerLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            powers:
                A single power value or an array-like of power values for each phase component.
                Either complex values (VA) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

                When a scalar value is provided, it creates a balanced load with the same power for
                each phase. The scalar value passed is assumed to be the power of each component of
                the load, not the total multi-phase power. To create an unbalanced load, provide a
                vector of power values with the same length as the number of components of the load.

            flexible_params:
                A list of :class:`FlexibleParameters` object, one for each phase. When provided,
                the load is considered as flexible (or controllable) and the parameters are used
                to compute the flexible power of the load.
        """
        super().__init__(id=id, bus=bus)

        self._flexible_param = flexible_param
        self.power = power
        self._res_flexible_powers: ComplexArray | None = None

        if self.is_flexible:
            cy_parameters = np.array([flexible_param._cy_fp])  # type: ignore
            self._cy_element = CyFlexibleLoad(
                n=self._n, powers=np.array([self._power], dtype=np.complex128), parameters=cy_parameters
            )
        else:
            self._cy_element = CyPowerLoad(n=self._n, powers=np.array([self._power], dtype=np.complex128))
        self._cy_connect()

    @property
    def flexible_param(self) -> FlexibleParameter | None:
        return self._flexible_param

    @property
    def is_flexible(self) -> bool:
        return self._flexible_param is not None

    @property
    @ureg_wraps("VA", (None,))
    def power(self) -> Q_[Complex]:
        """The powers of the load (VA).

        Setting the powers will update the load's power values and invalidate the network results.
        """
        return self._power

    @power.setter
    @ureg_wraps(None, (None, "VA"))
    def power(self, value: Complex) -> None:
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
            self._cy_element.update_powers([self._power])

    def _refresh_results(self) -> None:
        super()._refresh_results()
        if self.is_flexible:
            self._res_flexible_powers = self._cy_element.get_powers(self._n)

    def _res_flexible_powers_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_flexible_powers, warning=warning)

    @property
    @ureg_wraps("VA", (None,))
    def res_flexible_power(self) -> Q_[ComplexArray]:
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
        return self._res_flexible_powers_getter(warning=True)[0]

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        res = super()._to_dict(include_results=include_results)
        if self.flexible_param is not None:
            res["flexible_param"] = self.flexible_param.to_dict(include_results=include_results)
            if include_results:
                power = self._res_flexible_powers_getter(warning=False)[0]
                res["results"]["flexible_power"] = [power.real, power.imag]
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        if self.is_flexible:
            power = self._res_flexible_powers_getter(warning=False)[0]
            return {
                **super()._results_to_dict(warning=warning, full=full),
                "flexible_power": [power.real, power.imag],
            }
        else:
            return super()._results_to_dict(warning=warning, full=full)
