import logging
from abc import ABC, abstractmethod
from functools import cached_property
from typing import ClassVar

import numpy as np

from roseau.load_flow.converters import _calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import _CyE_co
from roseau.load_flow.models.terminals import AbstractTerminal
from roseau.load_flow.sym import phasor_to_sym
from roseau.load_flow.typing import ComplexArray, Id, JsonDict, Side
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import SIDE_DESC, abstractattrs, ensure_startsupper, one_or_more_repr, warn_external
from roseau.load_flow_engine.cy_engine import CyBranch

logger = logging.getLogger(__name__)


class AbstractConnectable(AbstractTerminal[_CyE_co], ABC):
    """A base class for elements connected to a bus."""

    @abstractmethod
    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        phases: str | None = None,
        connect_neutral: bool | None = None,
        side: Side | None = None,
    ) -> None:
        """AbstractConnectable constructor.

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

            side:
                For branches, this is the side of the branch associated with to be connected to the
                bus. It can be ``"HV"`` or ``"LV"`` for transformers or ``1`` or ``2`` for lines and
                switches. This is ``None`` for other elements.
        """
        self._check_compatible_phase_tech(bus, id=id)
        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id=id, phases=phases)
            connect_neutral = self._check_bus_phases(
                bus, id=id, phases=phases, connect_neutral=connect_neutral, side=side
            )

        super().__init__(id, phases=phases, side=side)
        self._connect(bus)
        self._bus = bus
        self._connect_neutral = connect_neutral
        self._res_currents: ComplexArray | None = None

    def __repr__(self) -> str:
        args = [f"id={self.id!r}", f"bus={self._bus.id!r}", f"phases={self.phases!r}"]
        if self._connect_neutral is not None:
            args.append(f"connect_neutral={self._connect_neutral!r}")
        side = f"-{self._side_value}" if self._side_value is not None else ""
        return f"<{type(self).__name__}{side}: {', '.join(args)}>"

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
            return "n" not in self.bus._phases
        return False

    def _check_bus_phases(
        self, bus: Bus, id: Id, phases: str, connect_neutral: bool | None, side: Side | None
    ) -> bool | None:
        side_desc = SIDE_DESC[side]
        if connect_neutral is not None:
            connect_neutral = bool(connect_neutral)  # to allow np.bool
        if connect_neutral and "n" not in phases:
            warn_external(
                message=(
                    f"{ensure_startsupper(f'{side_desc}neutral')} connection requested for "
                    f"{self.element_type} {id!r} with no neutral phase."
                ),
                category=UserWarning,
            )
            connect_neutral = None
        # Also check they are in the bus phases
        phases_not_in_bus = set(phases) - set(bus.phases)
        # "n" is allowed to be absent from the bus only if the element has more than 2 phases
        missing_ok = phases_not_in_bus == {"n"} and len(phases) > 2 and not connect_neutral
        if phases_not_in_bus and not missing_ok:
            ph, be = one_or_more_repr(sorted(phases_not_in_bus), "phase")
            msg = (
                f"{ensure_startsupper(f'{side_desc}{ph}')} of {self.element_type} {id!r} {be} not "
                f"in phases {bus.phases!r} of its bus {bus.id!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        return connect_neutral

    def _cy_connect(self) -> None:
        bus_phases = self.bus.phases.removesuffix("n") if self.has_floating_neutral else self.bus.phases
        connections = [(i, bus_phases.index(phase)) for i, phase in enumerate(self.phases) if phase in bus_phases]
        if isinstance(self._cy_element, CyBranch):
            self._cy_element.connect_side(self.bus._cy_element, connections, beginning=self._side_index == 0)
        else:
            self.bus._cy_element.connect(self._cy_element, [(j, i) for (i, j) in connections])

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

    @ureg_wraps("percent", (None,))
    def res_current_unbalance(self) -> Q_[float]:
        """Calculate the current unbalance (CU) on this element.

        The calculation depends on the definition of current unbalance:

        - Current Unbalance Factor (CUF):

          :math:`CUF = \\dfrac{I_\\mathrm{2}}{I_\\mathrm{1}} \\times 100 \\, (\\%)`

          Where :math:`I_{\\mathrm{2}}` is the magnitude of the negative-sequence (inverse) current
          and :math:`I_{\\mathrm{1}}` is the magnitude of the positive-sequence (direct) current.
        """

        if self.phases not in {"abc", "abcn"}:
            msg = (
                f"Current unbalance is only available for three-phase elements, {self._element_info} "
                f"has phases {self.phases!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        currents = self._res_currents_getter(warning=True)
        _, i1, i2 = phasor_to_sym(currents[:3])  # (0, +, -)
        return abs(i2) / abs(i1) * 100  # type: ignore

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            super()._parse_results_from_dict(data, include_results=include_results)
            self._res_currents = np.array(
                [complex(*i) for i in data["results"][f"currents{self._side_suffix}"]], dtype=np.complex128
            )

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = {
            "id": self.id,
            f"bus{self._side_suffix}": self.bus.id,
            f"phases{self._side_suffix}": self.phases,
            f"connect_neutral{self._side_suffix}": self._connect_neutral,
        }
        if include_results:
            currents = self._res_currents_getter(warning=True)
            potentials = self._res_potentials_getter(warning=False)  # warn only once
            data["results"] = {
                f"currents{self._side_suffix}": [[i.real, i.imag] for i in currents.tolist()],
                f"potentials{self._side_suffix}": [[v.real, v.imag] for v in potentials.tolist()],
            }
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents = self._res_currents_getter(warning)
        potentials = self._res_potentials_getter(warning=False)  # warn only once
        results = {
            "id": self.id,
            f"phases{self._side_suffix}": self.phases,
            f"currents{self._side_suffix}": [[i.real, i.imag] for i in currents.tolist()],
            f"potentials{self._side_suffix}": [[v.real, v.imag] for v in potentials.tolist()],
        }
        if full:
            powers = potentials * currents.conjugate()
            voltages = _calculate_voltages(potentials, self.phases)
            results[f"powers{self._side_suffix}"] = [[s.real, s.imag] for s in powers.tolist()]
            results[f"voltages{self._side_suffix}"] = [[v.real, v.imag] for v in voltages.tolist()]
        return results


@abstractattrs("type")
class AbstractDisconnectable(AbstractConnectable[_CyE_co], ABC):
    """A base class for disconnectable elements in the network (loads, sources, etc.)."""

    type: ClassVar[str]

    def __repr__(self) -> str:
        s = super().__repr__()
        if self._is_disconnected:
            return f"{s} (disconnected)"
        return s

    @property
    def is_disconnected(self) -> bool:
        """Is this element disconnected from the network?"""
        return self._is_disconnected

    @property
    def bus(self) -> Bus | None:
        """The bus of the element, or None if it is disconnected.

        .. deprecated:: 0.13.0

            Accessing the bus of a disconnected element will change in the future to return the bus
            it was connected to before disconnection instead of `None`. If you rely on this behavior
            to check if the element is disconnected, please use the `is_disconnected` property instead.
        """
        if self._is_disconnected:
            warn_external(
                f"Accessing the bus of the disconnected {self._element_info} will change in the "
                f"future to return the bus it was connected to before disconnection instead of None. "
                f"If you rely on this behavior to check if the element is disconnected, please use "
                f"`is_disconnected` instead."
            )
            return None
        return self._bus

    def disconnect(self) -> None:
        """Disconnect this element from the network. It cannot be used afterwards."""
        for element in self._connected_elements:
            if element.element_type == "ground connection":
                element._disconnect()
        self._disconnect()

    def _refresh_results(self) -> None:
        self._raise_disconnected_error()
        super()._refresh_results()

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        return super()._to_dict(include_results=include_results) | {"type": self.type}

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        return super()._results_to_dict(warning=warning, full=full) | {"type": self.type}
