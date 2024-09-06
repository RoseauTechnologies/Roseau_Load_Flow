import logging

import numpy as np
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.single.core import Element
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyVoltageSource

logger = logging.getLogger(__name__)


class VoltageSource(Element):
    """A voltage source fixes the voltages on the phases of the bus it is connected to.

    The source can be connected in a wye or star configuration (i.e with a neutral) or in a delta
    configuration (i.e without a neutral).

    See Also:
        The :ref:`Voltage source documentation page <models-voltage-source-usage>` for example usage.
    """

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        voltage: float,
    ) -> None:
        """Voltage source constructor.

        Args:
            id:
                A unique ID of the voltage source in the network sources.

            bus:
                The bus of the voltage source.

            voltage:
                TODO
        """
        super().__init__(id)
        self._connect(bus)
        self._bus = bus
        self._n = 2
        self.voltage = voltage
        self._cy_element = CyVoltageSource(n=self._n, voltages=np.array([self._voltage], dtype=np.complex128))
        self._cy_connect()

        # Results
        self._res_currents: ComplexArray | None = None
        self._res_potentials: ComplexArray | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"<{type(self).__name__}: id={self.id!r}, bus={bus_id!r}>"

    @property
    def bus(self) -> Bus:
        """The bus of the source."""
        return self._bus

    @property
    @ureg_wraps("V", (None,))
    def voltage(self) -> Q_[ComplexArray]:
        """The complex voltages of the source (V).

        Setting the voltages will update the source voltages and invalidate the network results.

        Note:
            Setting a scalar value updates the complex voltages of all phases of the source, not
            just their magnitudes. The phase angles are calculated based on the number of phases of
            the source. For a single-phase source, the phase angle is 0°. For a two-phase source,
            the phase angle of the second phase is 180°. For a three-phase source, the phase angles
            of the second and third phases are -120° and 120°, respectively (120° phase shift
            clockwise).
        """
        return self._voltage

    @voltage.setter
    @ureg_wraps(None, (None, "V"))
    def voltage(self, value: float) -> None:
        """Set the voltages of the source."""
        self._voltage = value
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_voltages([self._voltage])

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
        """The load flow result of the source currents (A)."""
        return self._res_currents_getter(warning=True)[0]

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_potentials, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potential(self) -> Q_[ComplexArray]:  # TODO delete ?
        """The load flow result of the source potentials (V)."""
        return self._res_potentials_getter(warning=True)[0]

    def _res_voltages_getter(self, warning: bool) -> ComplexArray:
        potentials = self._res_potentials_getter(warning)
        return np.array([potentials[0] - potentials[1]])

    @property
    @ureg_wraps("V", (None,))
    def res_voltages(self) -> Q_[ComplexArray]:
        """The load flow result of the source voltages (V)."""
        return self._res_voltages_getter(warning=True)[0]

    def _res_powers_getter(
        self, warning: bool, currents: ComplexArray | None = None, potentials: ComplexArray | None = None
    ) -> ComplexArray:
        if currents is None:
            currents = self._res_currents_getter(warning=warning)
            warning = False  # we warn only once
        if potentials is None:
            potentials = self._res_potentials_getter(warning=warning)
        return potentials * currents.conj()

    @property
    @ureg_wraps("VA", (None,))
    def res_powers(self) -> Q_[ComplexArray]:
        """The load flow result of the source powers (VA)."""
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
            self._res_currents = np.array(
                [data["results"]["currents"][0] + 1j * data["results"]["currents"][1]], dtype=np.complex128
            )
            self._res_potentials = np.array(
                [complex(data["results"]["potentials"][0], data["results"]["potentials"][1])], dtype=np.complex128
            )
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
            current = self._res_currents_getter(warning=True)[0]
            res["results"] = {"current": [current.real, current.imag]}
            potential = self._res_potentials_getter(warning=False)[0]
            res["results"]["potential"] = [potential.real, potential.imag]
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current = self._res_currents_getter(warning)[0]
        results = {
            "id": self.id,
            "current": [current.real, current.imag],
        }
        potential = self._res_potentials_getter(warning=False)[0]
        results["potential"] = [potential.real, potential.imag]
        if full:
            powers = self._res_powers_getter(warning=False, currents=current, potentials=potential)  # TODO
            results["powers"] = [powers.real, powers.imag]
        return results
