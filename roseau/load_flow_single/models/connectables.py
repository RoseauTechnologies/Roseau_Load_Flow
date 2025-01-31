import logging
from abc import ABC
from typing import ClassVar

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import _CyE
from roseau.load_flow_single.models.terminals import BaseTerminal

logger = logging.getLogger(__name__)


class BaseConnectable(BaseTerminal[_CyE], ABC):
    """A base class for connectable elements in the network (loads, sources, etc.)."""

    type: ClassVar[str]

    def __init__(self, id: Id, bus: Bus) -> None:
        """BaseConnectable constructor.

        Args:
            id:
                A unique ID of the element in its dictionary in the network.

            bus:
                The bus to connect the element to.
        """
        if type(self) is BaseConnectable:
            raise TypeError("Can't instantiate abstract class BaseConnectable")
        super().__init__(id)
        self._connect(bus)
        self._bus = bus
        self._res_current: complex | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"<{type(self).__name__}: id={self.id!r}, bus={bus_id!r}>"

    @property
    def bus(self) -> Bus:
        """The bus this element is connected to."""
        return self._bus

    def _cy_connect(self) -> None:
        assert self._cy_element is not None
        connections = [(i, i) for i in range(self._n)]
        self.bus._cy_element.connect(self._cy_element, connections)

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            super()._refresh_results()
            self._res_current = self._cy_element.get_currents(self._n)[0]

    def _res_current_getter(self, warning: bool) -> complex:
        self._refresh_results()
        return self._res_getter(value=self._res_current, warning=warning)

    def _res_power_getter(self, warning: bool) -> complex:
        current = self._res_current_getter(warning=warning)
        voltage = self._res_voltage_getter(warning=False)  # warn only once
        return voltage * current.conjugate() * SQRT3

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The load flow result of the element's current (A)."""
        return self._res_current_getter(warning=True)

    @property
    @ureg_wraps("VA", (None,))
    def res_power(self) -> Q_[complex]:
        """The load flow result of the element's power (VA)."""
        return self._res_power_getter(warning=True)

    #
    # Disconnect
    #
    def disconnect(self) -> None:
        """Disconnect this element from the network. It cannot be used afterwards."""
        self._disconnect()
        self._bus = None

    def _raise_disconnected_error(self) -> None:
        """Raise an error if the element is disconnected."""
        if self._bus is None:
            msg = f"The {self.element_type} {self.id!r} is disconnected and cannot be used anymore."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT)

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            super()._parse_results_from_dict(data, include_results=include_results)
            self._res_current = complex(*data["results"]["current"])

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        data: JsonDict = {"id": self.id, "bus": self.bus.id, "type": self.type}
        if include_results:
            current = self._res_current_getter(warning=True)
            voltage = self._res_voltage_getter(warning=False)  # warn only once
            data["results"] = {
                "current": [current.real, current.imag],
                "voltage": [voltage.real, voltage.imag],
            }
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current = self._res_current_getter(warning)
        voltage = self._res_voltage_getter(warning=False)  # warn only once
        results: JsonDict = {
            "id": self.id,
            "type": self.type,
            "current": [current.real, current.imag],
            "voltage": [voltage.real, voltage.imag],
        }
        if full:
            power = voltage * current.conjugate() * SQRT3
            results["power"] = [power.real, power.imag]
        return results
