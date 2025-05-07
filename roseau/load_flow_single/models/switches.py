import logging
from typing import Final

from shapely.geometry.base import BaseGeometry

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id
from roseau.load_flow_engine.cy_engine import CySwitch
from roseau.load_flow_single.models.branches import AbstractBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.sources import VoltageSource

logger = logging.getLogger(__name__)


class Switch(AbstractBranch[CySwitch]):
    """A general purpose switch branch."""

    element_type: Final = "switch"

    def __init__(self, id: Id, bus1: Bus, bus2: Bus, *, geometry: BaseGeometry | None = None) -> None:
        """Switch constructor.

        Args:
            id:
                A unique ID of the switch in the network switches.

            bus1:
                First bus to connect to the switch.

            bus2:
                Second bus to connect to the switch.

            geometry:
                The geometry of the switch.
        """
        super().__init__(id=id, bus1=bus1, bus2=bus2, n=1, geometry=geometry)
        self._check_elements()
        self._check_loop()
        self._check_same_voltage_level()
        self._set_cy_element(CySwitch(1))
        self._cy_connect()
        self._connect(bus1, bus2)

    def _check_loop(self) -> None:
        """Check that there are no switch loops, raise an exception if it is the case."""
        visited_1: set[Element] = set()
        elements: list[Element] = [self.bus1]
        while elements:
            element = elements.pop(-1)
            visited_1.add(element)
            for e in element._connected_elements:
                if e not in visited_1 and (isinstance(e, (Bus, Switch))) and e != self:
                    elements.append(e)
        visited_2: set[Element] = set()
        elements = [self.bus2]
        while elements:
            element = elements.pop(-1)
            visited_2.add(element)
            for e in element._connected_elements:
                if e not in visited_2 and (isinstance(e, (Bus, Switch))) and e != self:
                    elements.append(e)
        if visited_1.intersection(visited_2):
            msg = (
                f"Connecting switch {self.id!r} between buses {self.bus1.id!r} and {self.bus2.id!r} "
                f"creates a switch loop. Current flow in several switch-only branches between buses "
                f"cannot be computed."
            )
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
