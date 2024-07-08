import logging
from functools import cached_property
from typing import Final

import numpy as np
from typing_extensions import Self

from roseau.load_flow.converters import calculate_voltage_phases
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import ComplexArray, ComplexArrayLike1D, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyDeltaVoltageSource, CyVoltageSource

logger = logging.getLogger(__name__)


class VoltageSource(Element):
    """A voltage source."""

    allowed_phases: Final = Bus.allowed_phases
    """The allowed phases for a voltage source are the same as for a :attr:`bus<Bus.allowed_phases>`."""

    def __init__(self, id: Id, bus: Bus, *, voltages: ComplexArrayLike1D, phases: str | None = None) -> None:
        """Voltage source constructor.

        Args:
            id:
                A unique ID of the voltage source in the network sources.

            bus:
                The bus of the voltage source.

            voltages:
                An array-like of the voltages of the source. They will be set on the connected bus.
                If the source has a neutral connection, the voltages are considered phase-to-neutral
                voltages, otherwise they are the phase-to-phase voltages. Either complex values (V)
                or a :class:`Quantity <roseau.load_flow.units.Q_>` of complex values.

            phases:
                The phases of the source. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the source must
                be present in the phases of the connected bus. Multiphase sources are allowed to have
                a floating neutral (i.e. they can be connected to buses that don't have a neutral).
        """
        super().__init__(id)
        self._connect(bus)

        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id, phases=phases)
            # Also check they are in the bus phases
            phases_not_in_bus = set(phases) - set(bus.phases)
            # "n" is allowed to be absent from the bus only if the source has more than 2 phases
            floating_neutral = phases_not_in_bus == {"n"} and len(phases) > 2
            if phases_not_in_bus and not floating_neutral:
                msg = (
                    f"Phases {sorted(phases_not_in_bus)} of source {id!r} are not in bus "
                    f"{bus.id!r} phases {bus.phases!r}"
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        if len(phases) == 2 and "n" not in phases:
            # This is a delta source that has one element connected between two phases
            self._size = 1
        else:
            self._size = len(set(phases) - {"n"})

        self._phases = phases
        self._bus = bus
        self.voltages = voltages

        self._n = len(self._phases)
        if self.phases == "abc":
            self._cy_element = CyDeltaVoltageSource(n=self._n, voltages=self._voltages)
        else:
            self._cy_element = CyVoltageSource(n=self._n, voltages=self._voltages)
        self._cy_connect()

        # Results
        self._res_currents: ComplexArray | None = None
        self._res_potentials: ComplexArray | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"<{type(self).__name__}: id={self.id!r}, bus={bus_id!r}, phases={self.phases!r}>"

    @property
    def phases(self) -> str:
        """The phases of the source."""
        return self._phases

    @property
    def bus(self) -> Bus:
        """The bus of the source."""
        return self._bus

    @property
    @ureg_wraps("V", (None,))
    def voltages(self) -> Q_[ComplexArray]:
        """The voltages of the source (V)."""
        return self._voltages

    @voltages.setter
    @ureg_wraps(None, (None, "V"))
    def voltages(self, voltages: ComplexArrayLike1D) -> None:
        if len(voltages) != self._size:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)
        self._voltages = np.array(voltages, dtype=np.complex128)
        self._invalidate_network_results()
        if self._cy_element is not None:
            self._cy_element.update_voltages(self._voltages)

    @property
    def has_floating_neutral(self) -> bool:
        """Does this source have a floating neutral?"""
        return "n" in self._phases and "n" not in self._bus._phases

    @cached_property
    def voltage_phases(self) -> list[str]:
        """The phases of the source voltages."""
        return calculate_voltage_phases(self.phases)

    def _refresh_results(self) -> None:
        self._res_currents = self._cy_element.get_currents(self._n)
        self._res_potentials = self._cy_element.get_potentials(self._n)

    def _res_currents_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps("A", (None,))
    def res_currents(self) -> Q_[ComplexArray]:
        """The load flow result of the source currents (A)."""
        return self._res_currents_getter(warning=True)

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        if self._fetch_results:
            self._refresh_results()
        return self._res_getter(value=self._res_potentials, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potentials(self) -> Q_[ComplexArray]:
        """The load flow result of the source potentials (V)."""
        return self._res_potentials_getter(warning=True)

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
        return self._res_powers_getter(warning=True)

    def _cy_connect(self):
        connections = []
        for i, phase in enumerate(self.bus.phases):
            if phase in self.phases:
                j = self.phases.find(phase)
                connections.append((i, j))
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
        voltages = [complex(v[0], v[1]) for v in data["voltages"]]
        self = cls(id=data["id"], bus=data["bus"], voltages=voltages, phases=data["phases"])
        if include_results and "results" in data:
            self._res_currents = np.array(
                [complex(i[0], i[1]) for i in data["results"]["currents"]], dtype=np.complex128
            )
            if "potentials" in data["results"]:
                self._res_potentials = np.array(
                    [complex(i[0], i[1]) for i in data["results"]["potentials"]], dtype=np.complex128
                )
            elif not self.has_floating_neutral:
                self._res_potentials = data["bus"]._get_potentials_of(self.phases, warning=False)
            else:
                msg = f"{type(self).__name__} {self.id!r} with floating neutral is missing results of potentials."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        res = {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            "voltages": [[v.real, v.imag] for v in self._voltages],
        }
        if include_results:
            currents = self._res_currents_getter(warning=True)
            res["results"] = {"currents": [[i.real, i.imag] for i in currents]}
            if self.has_floating_neutral:
                potentials = self._res_potentials_getter(warning=False)
                res["results"]["potentials"] = [[v.real, v.imag] for v in potentials]
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents = self._res_currents_getter(warning)
        results = {
            "id": self.id,
            "phases": self.phases,
            "currents": [[i.real, i.imag] for i in currents],
        }
        if self.has_floating_neutral or full:
            potentials = self._res_potentials_getter(warning=False)
            results["potentials"] = [[v.real, v.imag] for v in potentials]

            if full:
                powers = self._res_powers_getter(warning=False, currents=currents, potentials=potentials)
                results["powers"] = [[s.real, s.imag] for s in powers]
        return results
