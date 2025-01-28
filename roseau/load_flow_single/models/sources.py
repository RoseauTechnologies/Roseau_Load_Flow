import logging

import numpy as np
from typing_extensions import Self

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Complex, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyVoltageSource
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element

logger = logging.getLogger(__name__)


class VoltageSource(Element[CyVoltageSource]):
    """A voltage source fixes the voltages of the bus it is connected to.

    The source can be connected in a wye or star configuration (i.e with a neutral) or in a delta
    configuration (i.e without a neutral).

    See Also:
        The :ref:`Voltage source documentation page <models-voltage-source-usage>` for example usage.
    """

    def __init__(self, id: Id, bus: Bus, *, voltage: Complex | Q_[Complex]) -> None:
        """Voltage source constructor.

        Args:
            id:
                A unique ID of the voltage source in the network sources.

            bus:
                The bus of the voltage source.

            voltage:
                The complex voltage of the source (V).
        """
        super().__init__(id)
        self._connect(bus)
        self._bus = bus
        self._n = 2
        self.voltage = voltage
        self._cy_element = CyVoltageSource(n=self._n, voltages=np.array([self._voltage / SQRT3], dtype=np.complex128))
        self._cy_connect()

        # Results
        self._res_current: complex | None = None
        self._res_voltage: complex | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"<{type(self).__name__}: id={self.id!r}, bus={bus_id!r}>"

    @property
    def bus(self) -> Bus:
        """The bus of the source."""
        return self._bus

    @property
    @ureg_wraps("V", (None,))
    def voltage(self) -> Q_[complex]:
        """The complex voltage of the source (V).

        Setting the voltage will update the source voltage and invalidate the network results.
        """
        return self._voltage

    @voltage.setter
    @ureg_wraps(None, (None, "V"))
    def voltage(self, value: Complex | Q_[Complex]) -> None:
        """Set the voltages of the source."""
        self._voltage = complex(value)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_voltages(np.array([self._voltage / SQRT3], dtype=np.complex128))

    def _refresh_results(self) -> None:
        self._res_current = self._cy_element.get_currents(self._n)[0]
        self._res_voltage = self._cy_element.get_potentials(self._n)[0] * SQRT3

    def _res_current_getter(self, warning: bool) -> Complex:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_current, warning=warning)

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The load flow result of the source currents (A)."""
        return self._res_current_getter(warning=True)

    def _res_voltage_getter(self, warning: bool) -> complex:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_voltage, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_voltage(self) -> Q_[complex]:
        """The load flow result of the source voltages (V)."""
        return self._res_voltage_getter(warning=True)

    def _res_power_getter(
        self, warning: bool, current: complex | None = None, voltage: complex | None = None
    ) -> complex:
        if current is None:
            current = self._res_current_getter(warning=warning)
            warning = False  # we warn only once
        if voltage is None:
            voltage = self._res_voltage_getter(warning=warning)
        return voltage * current.conjugate() * SQRT3

    @property
    @ureg_wraps("VA", (None,))
    def res_power(self) -> Q_[complex]:
        """The load flow result of the source powers (VA)."""
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
        """Disconnect this voltage source from the network. It cannot be used afterwards."""
        self._disconnect()
        self._bus = None

    def _raise_disconnected_error(self) -> None:
        """Raise an error if the voltage source is disconnected."""
        if self.bus is None:
            msg = f"The voltage source {self.id!r} is disconnected and cannot be used anymore."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        voltage = data["voltage"][0] + 1j * data["voltage"][1]
        self = cls(id=data["id"], bus=data["bus"], voltage=voltage)
        if include_results and "results" in data:
            self._res_current = complex(data["results"]["current"][0], data["results"]["current"][1])
            self._res_voltage = complex(data["results"]["voltage"][0], data["results"]["voltage"][1])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        res = {
            "id": self.id,
            "bus": self.bus.id,
            "voltage": [self._voltage.real, self._voltage.imag],
        }
        if include_results:
            current = self._res_current_getter(warning=True)
            voltage = self._res_voltage_getter(warning=False)
            res["results"] = {
                "current": [current.real, current.imag],
                "voltage": [voltage.real, voltage.imag],
            }
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current = self._res_current_getter(warning)
        voltage = self._res_voltage_getter(warning=False)
        results = {
            "id": self.id,
            "current": [current.real, current.imag],
            "voltage": [voltage.real, voltage.imag],
        }
        if full:
            power = self._res_power_getter(warning=False, current=current, voltage=voltage)
            results["power"] = [power.real, power.imag]
        return results
