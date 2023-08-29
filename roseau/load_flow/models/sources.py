import logging
from collections.abc import Sequence
from typing import Any, Optional

import numpy as np
from typing_extensions import Self

from roseau.load_flow.converters import calculate_voltage_phases
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps

logger = logging.getLogger(__name__)


class VoltageSource(Element):
    """A voltage source.

    See Also:
        :doc:`Voltage source model documentation </models/VoltageSource>`
    """

    allowed_phases = Bus.allowed_phases
    """The allowed phases for a voltage source are the same as for a :attr:`bus<Bus.allowed_phases>`."""
    _floating_neutral_allowed: bool = False

    def __init__(
        self, id: Id, bus: Bus, *, voltages: Sequence[complex], phases: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Voltage source constructor.

        Args:
            id:
                A unique ID of the voltage source in the network sources.

            bus:
                The bus of the voltage source.

            voltages:
                The voltages of the source. They will be fixed on the connected bus. If the source
                has a neutral connection, the voltages are the phase-to-neutral voltages, otherwise
                they are the phase-to-phase voltages.

            phases:
                The phases of the source. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the source, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.
        """
        super().__init__(id, **kwargs)
        self._connect(bus)

        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id, phases=phases)
            # Also check they are in the bus phases
            phases_not_in_bus = set(phases) - set(bus.phases)
            # "n" is allowed to be absent from the bus only if the load has more than 2 phases
            floating_neutral = self._floating_neutral_allowed and phases_not_in_bus == {"n"} and len(phases) > 2
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

        self.phases = phases
        self.bus = bus
        self.voltages = voltages

        # Results
        self._res_currents: Optional[np.ndarray] = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return (
            f"{type(self).__name__}(id={self.id!r}, bus={bus_id!r}, voltages={self.voltages!r}, "
            f"phases={self.phases!r})"
        )

    @property
    @ureg_wraps("V", (None,), strict=False)
    def voltages(self) -> Q_[np.ndarray]:
        """The voltages of the source (V)."""
        return self._voltages

    @voltages.setter
    @ureg_wraps(None, (None, "V"), strict=False)
    def voltages(self, voltages: Sequence[complex]) -> None:
        if len(voltages) != self._size:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)
        self._voltages = np.asarray(voltages, dtype=complex)
        self._invalidate_network_results()

    @property
    def voltage_phases(self) -> list[str]:
        """The phases of the source voltages."""
        return calculate_voltage_phases(self.phases)

    def _res_currents_getter(self, warning: bool) -> np.ndarray:
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps("A", (None,), strict=False)
    def res_currents(self) -> Q_[np.ndarray]:
        """The load flow result of the source currents (A)."""
        return self._res_currents_getter(warning=True)

    def _res_potentials_getter(self, warning: bool) -> np.ndarray:
        self._raise_disconnected_error()
        return self.bus._get_potentials_of(self.phases, warning)

    @property
    @ureg_wraps("V", (None,), strict=False)
    def res_potentials(self) -> Q_[np.ndarray]:
        """The load flow result of the source potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_powers_getter(self, warning: bool) -> np.ndarray:
        curs = self._res_currents_getter(warning)
        pots = self._res_potentials_getter(warning=False)  # we warn on the previous line
        return pots * curs.conj()

    @property
    @ureg_wraps("VA", (None,), strict=False)
    def res_powers(self) -> Q_[np.ndarray]:
        """The load flow result of the source powers (VA)."""
        return self._res_powers_getter(warning=True)

    #
    # Disconnect
    #
    def disconnect(self) -> None:
        """Disconnect this voltage source from the network. It cannot be used afterwards."""
        self._disconnect()
        self.bus = None

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
    def from_dict(cls, data: JsonDict) -> Self:
        voltages = [complex(v[0], v[1]) for v in data["voltages"]]
        return cls(data["id"], data["bus"], voltages=voltages, phases=data["phases"])

    def to_dict(self, include_geometry: bool = True) -> JsonDict:
        self._raise_disconnected_error()
        return {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            "voltages": [[v.real, v.imag] for v in self._voltages],
        }

    def results_from_dict(self, data: JsonDict) -> None:
        self._res_currents = np.array([complex(i[0], i[1]) for i in data["currents"]], dtype=complex)

    def _results_to_dict(self, warning: bool) -> JsonDict:
        return {
            "id": self.id,
            "phases": self.phases,
            "currents": [[i.real, i.imag] for i in self._res_currents_getter(warning)],
        }
