import logging
import warnings
from abc import ABC
from functools import cached_property
from typing import ClassVar

import numpy as np

from roseau.load_flow.converters import _calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import _CyE
from roseau.load_flow.models.terminals import BaseTerminal
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level

logger = logging.getLogger(__name__)


class BaseConnectable(BaseTerminal[_CyE], ABC):
    """A base class for connectable elements in the network (loads, sources, etc.)."""

    type: ClassVar[str]

    def __init__(self, id: Id, bus: Bus, *, phases: str | None = None, connect_neutral: bool | None = None) -> None:
        """BaseConnectable constructor.

        Args:
            id:
                A unique ID of the element in its dictionary in the network.

            bus:
                The bus to connect the element to.

            phases:
                The phases of the element. A string like ``"abc"`` or ``"an"`` etc. The bus phases
                are used by default. The order of the phases is important. For a full list of
                supported phases, see the class attribute :attr:`allowed_phases`. All phases of the
                element must be present in the phases of the connected bus. Multiphase elements are
                allowed to be connected to buses that don't have a neutral if ``connect_neutral`` is
                not set to ``True``.

            connect_neutral:
                Specifies whether the element's neutral should be connected to the bus's neutral or
                left floating. By default, the elements's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the element's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        if type(self) is BaseConnectable:
            raise TypeError("Can't instantiate abstract class BaseConnectable")

        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id=id, phases=phases)
            # Also check they are in the bus phases
            phases_not_in_bus = set(phases) - set(bus.phases)
            # "n" is allowed to be absent from the bus only if the element has more than 2 phases
            missing_ok = phases_not_in_bus == {"n"} and len(phases) > 2 and not connect_neutral
            if phases_not_in_bus and not missing_ok:
                msg = f"Phases {sorted(phases_not_in_bus)} of {self.element_type} {id!r} are not in bus {bus.id!r} phases {bus.phases!r}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

        super().__init__(id, phases=phases)

        if connect_neutral is not None:
            connect_neutral = bool(connect_neutral)  # to allow np.bool
        if connect_neutral and "n" not in phases:
            warnings.warn(
                message=f"Neutral connection requested for {self.element_type} {id!r} with no neutral phase",
                category=UserWarning,
                stacklevel=find_stack_level(),
            )
            connect_neutral = None

        self._connect(bus)
        self._bus = bus
        self._connect_neutral = connect_neutral
        self._res_currents: ComplexArray | None = None

    def __repr__(self) -> str:
        bus_id = self.bus.id if self.bus is not None else None
        return f"<{type(self).__name__}: id={self.id!r}, bus={bus_id!r}, phases={self.phases!r}>"

    @property
    def bus(self) -> Bus:
        """The bus of the element."""
        return self._bus

    @cached_property
    def has_floating_neutral(self) -> bool:
        """Does this element have a floating neutral?"""
        if "n" not in self._phases:
            return False
        if self._connect_neutral is False:
            return True
        if self._connect_neutral is None:
            return "n" not in self.bus.phases
        return False

    def _cy_connect(self) -> None:
        connections = []
        bus_phases = self.bus.phases.removesuffix("n") if self.has_floating_neutral else self.bus.phases
        for i, phase in enumerate(bus_phases):
            if phase in self.phases:
                j = self.phases.index(phase)
                connections.append((i, j))
        self.bus._cy_element.connect(self._cy_element, connections)

    #
    # Disconnect
    #
    def disconnect(self) -> None:
        """Disconnect this element from the network. It cannot be used afterwards."""
        self._disconnect()
        self._bus = None

    def _raise_disconnected_error(self) -> None:
        """Raise an error if the element is disconnected."""
        if self.bus is None:
            msg = f"The {self.element_type} {self.id!r} is disconnected and cannot be used anymore."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT)

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            super()._refresh_results()
            self._res_currents = self._cy_element.get_currents(self._n)

    def _res_currents_getter(self, warning: bool) -> ComplexArray:
        self._refresh_results()
        return self._res_getter(value=self._res_currents, warning=warning)

    def _res_powers_getter(self, warning: bool) -> ComplexArray:
        currents = self._res_currents_getter(warning=warning)
        potentials = self._res_potentials_getter(warning=False)  # warn only once
        return potentials * currents.conjugate()

    @property
    @ureg_wraps("A", (None,))
    def res_currents(self) -> Q_[ComplexArray]:
        """The load flow result of the element currents (A)."""
        return self._res_currents_getter(warning=True)

    @property
    @ureg_wraps("VA", (None,))
    def res_powers(self) -> Q_[ComplexArray]:
        """The load flow result of the "line powers" flowing into the element (VA)."""
        return self._res_powers_getter(warning=True)

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            super()._parse_results_from_dict(data, include_results=include_results)
            self._res_currents = np.array([complex(*i) for i in data["results"]["currents"]], dtype=np.complex128)

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        data = {
            "id": self.id,
            "bus": self.bus.id,
            "phases": self.phases,
            "type": self.type,
            "connect_neutral": self._connect_neutral,
        }
        if include_results:
            currents = self._res_currents_getter(warning=True)
            potentials = self._res_potentials_getter(warning=False)  # warn only once
            data["results"] = {
                "currents": [[i.real, i.imag] for i in currents],
                "potentials": [[v.real, v.imag] for v in potentials],
            }
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents = self._res_currents_getter(warning)
        potentials = self._res_potentials_getter(warning=False)  # warn only once
        results = {
            "id": self.id,
            "phases": self.phases,
            "type": self.type,
            "currents": [[i.real, i.imag] for i in currents],
            "potentials": [[v.real, v.imag] for v in potentials],
        }
        if full:
            powers = potentials * currents.conjugate()
            voltages = _calculate_voltages(potentials, self.phases)
            results["powers"] = [[s.real, s.imag] for s in powers]
            results["voltages"] = [[v.real, v.imag] for v in voltages]
        return results
