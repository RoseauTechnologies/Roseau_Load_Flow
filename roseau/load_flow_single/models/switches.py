import logging
from typing import Final, Literal

from shapely.geometry.base import BaseGeometry

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import id_sort_key, one_or_more_repr
from roseau.load_flow_engine.cy_engine import CyOpenSwitch, CySwitch
from roseau.load_flow_single.models.branches import AbstractBranch, AbstractBranchSide
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.sources import VoltageSource

logger = logging.getLogger(__name__)


class Switch(AbstractBranch["SwitchSide", CySwitch | CyOpenSwitch]):
    """A general purpose switch branch."""

    element_type: Final = "switch"

    def __init__(
        self, id: Id, bus1: Bus, bus2: Bus, *, closed: bool = True, geometry: BaseGeometry | None = None
    ) -> None:
        """Switch constructor.

        Args:
            id:
                A unique ID of the switch in the network switches.

            bus1:
                First bus to connect to the switch.

            bus2:
                Second bus to connect to the switch.

            closed:
                Whether the switch is closed or not. If ``True`` (default), the switch is closed and
                the current can flow through it. If ``False``, the switch is open and no current can
                flow through it.

            geometry:
                The geometry of the switch.
        """
        super().__init__(id=id, bus1=bus1, bus2=bus2, n=1, geometry=geometry)
        self._side1 = SwitchSide(branch=self, side=1, bus=bus1)
        self._side2 = SwitchSide(branch=self, side=2, bus=bus2)
        self._closed = closed
        self._check_elements()
        if closed:
            self._check_loop(operation="connecting")
        self._check_same_voltage_level()
        self._cy_element = CySwitch(1) if closed else CyOpenSwitch(1)
        self._cy_connect()
        self._connect(bus1, bus2)

    def __repr__(self) -> str:
        parts = [
            f"id={self.id!r}",
            f"bus1={self._side1.bus.id!r}",
            f"bus2={self._side2.bus.id!r}",
            f"closed={self.closed}",
        ]
        return f"<{type(self).__name__}: {', '.join(parts)}>"

    def _check_loop(self, operation: Literal["connecting", "closing"]) -> None:
        """Check that there are no switch loops, raise an exception if it is the case."""
        visited_1: set[Element] = set()
        elements: list[Element] = [self.bus1]
        while elements:
            element = elements.pop(-1)
            visited_1.add(element)
            for e in element._connected_elements:
                if (
                    e not in visited_1
                    and e is not self
                    and ((isinstance(e, Switch) and e.closed) or isinstance(e, Bus))
                ):
                    elements.append(e)
        visited_2: set[Element] = set()
        elements = [self.bus2]
        while elements:
            element = elements.pop(-1)
            visited_2.add(element)
            for e in element._connected_elements:
                if (
                    e not in visited_2
                    and e is not self
                    and ((isinstance(e, Switch) and e.closed) or isinstance(e, Bus))
                ):
                    elements.append(e)
        if loop_switches := visited_1.intersection(visited_2):
            other_switches, _ = one_or_more_repr(
                sorted(
                    (e.id for e in loop_switches if isinstance(e, Switch)),
                    key=lambda eid: id_sort_key({"id": eid}),
                ),
                "switch",
                "switches",
            )
            msg = (
                f"{operation.capitalize()} switch {self.id!r} between buses {self.bus1.id!r} and "
                f"{self.bus2.id!r} creates a loop with {other_switches}. Current flow in several "
                f"switch-only branches between buses cannot be computed."
            )
            if operation == "closing":
                msg += " Open the other switches first."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.SWITCHES_LOOP)

    def _check_elements(self) -> None:
        """Check that we can connect both elements."""
        if any(isinstance(e, VoltageSource) for e in self.bus1._connected_elements) and any(
            isinstance(e, VoltageSource) for e in self.bus2._connected_elements
        ):
            msg = (
                f"Connecting switch {self.id!r} between buses {self.bus1.id!r} and {self.bus2.id!r} "
                f"that both have a voltage source is not allowed."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION)

    @property
    def closed(self) -> bool:
        """Whether the switch is closed or not."""
        return self._closed

    def open(self) -> None:
        """Open the switch."""
        if self.closed:
            self._invalidate_network_results()
            if self._network is not None:
                self._network._valid = False
            self._cy_element.disconnect()
            self._cy_element = CyOpenSwitch(1)
            self._cy_connect()
        self._closed = False

    def close(self) -> None:
        """Close the switch."""
        if not self.closed:
            self._check_loop(operation="closing")
            self._invalidate_network_results()
            if self._network is not None:
                self._network._valid = False
            self._cy_element.disconnect()
            self._cy_element = CySwitch(1)
            self._cy_connect()
        self._closed = True

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results)
        data["closed"] = self._closed
        if include_results:
            data["results"] = data.pop("results")  # move results to the end
        return data


class SwitchSide(AbstractBranchSide):
    element_type = "switch"
    _branch: Switch
