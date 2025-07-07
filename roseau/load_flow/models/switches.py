import logging
from typing import Final

from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch, AbstractBranchSide
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.sources import VoltageSource
from roseau.load_flow.typing import Id
from roseau.load_flow_engine.cy_engine import CySwitch

logger = logging.getLogger(__name__)


class Switch(AbstractBranch["SwitchSide", CySwitch]):
    """A general purpose switch branch."""

    element_type: Final = "switch"
    allowed_phases: Final = frozenset(Bus.allowed_phases | {"a", "b", "c", "n"})
    """The allowed phases for a switch are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"``
    - P-P or P-P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"abn"``, ``"bcn"``, ``"can"``
    - P or P-N: ``"a"``, ``"b"``, ``"c"``, ``"an"``, ``"bn"``, ``"cn"``
    - N: ``"n"``
    """

    def __init__(
        self, id: Id, bus1: Bus, bus2: Bus, *, phases: str | None = None, geometry: BaseGeometry | None = None
    ) -> None:
        """Switch constructor.

        Args:
            id:
                A unique ID of the switch in the network switches.

            bus1:
                Bus to connect to the switch.

            bus2:
                Bus to connect to the switch.

            phases:
                The phases of the switch. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the switch must be present in the phases of
                both connected buses. By default, the phases common to both buses are used.

            geometry:
                The geometry of the switch.
        """
        phases = self._check_phases_common(id, bus1=bus1, bus2=bus2, phases=phases)
        super().__init__(id=id, phases1=phases, phases2=phases, bus1=bus1, bus2=bus2, geometry=geometry)
        self._side1 = SwitchSide(branch=self, side=1, bus=bus1, phases=phases, connect_neutral=None)
        self._side2 = SwitchSide(branch=self, side=2, bus=bus2, phases=phases, connect_neutral=None)
        self._check_elements()
        self._check_loop()
        self._check_same_voltage_level()
        self._cy_element = CySwitch(self._side1._n)
        self._cy_connect()
        self._connect(bus1, bus2)

    @property
    def phases(self) -> str:
        """The phases of the switch. This is an alias for :attr:`phases1` and :attr:`phases2`."""
        return self._side1.phases

    def _check_loop(self) -> None:
        """Check that there are no switch loop, raise an exception if it is the case"""
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
            msg = f"There is a loop of switch involving the switch {self.id!r}. It is not allowed."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.SWITCHES_LOOP)

    def _check_elements(self) -> None:
        """Check that we can connect both elements."""
        if any(isinstance(e, VoltageSource) for e in self.bus1._connected_elements) and any(
            isinstance(e, VoltageSource) for e in self.bus2._connected_elements
        ):
            msg = (
                f"The buses {self.bus1.id!r} and {self.bus2.id!r} both have a voltage source and "
                f"are connected with the switch {self.id!r}. It is not allowed."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION)


class SwitchSide(AbstractBranchSide):
    element_type = "switch"
    allowed_phases = Switch.allowed_phases  # type: ignore
    _branch: Switch
