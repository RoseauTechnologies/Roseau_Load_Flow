import logging

from shapely.geometry.base import BaseGeometry

from roseau.load_flow import Ground
from roseau.load_flow.models.lines import Line as TriLine
from roseau.load_flow.models.switches import Switch as TriSwitch
from roseau.load_flow.single.buses import Bus
from roseau.load_flow.single.lines.parameters import LineParameters
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_

logger = logging.getLogger(__name__)


class Switch(TriSwitch):
    """A general purpose switch branch."""

    def __init__(self, id: Id, bus1: Bus, bus2: Bus, *, geometry: BaseGeometry | None = None) -> None:
        """Switch constructor.

        Args:
            id:
                A unique ID of the switch in the network branches.

            bus1:
                Bus to connect to the switch.

            bus2:
                Bus to connect to the switch.

            geometry:
                The geometry of the switch.
        """
        super().__init__(id=id, bus1=bus1, bus2=bus2, geometry=geometry, phases="a")


class Line(TriLine):
    """An electrical line PI model with series impedance and optional shunt admittance."""

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        parameters: LineParameters,
        length: float | Q_[float],
        ground: Ground | None = None,
        geometry: BaseGeometry | None = None,
    ) -> None:
        """Line constructor.

        Args:
            id:
                A unique ID of the line in the network branches.

            bus1:
                The first bus (aka `"from_bus"`) to connect to the line.

            bus2:
                The second bus (aka `"to_bus"`) to connect to the line.

            parameters:
                Parameters defining the electric model of the line using its impedance and shunt
                admittance matrices. This is an instance of the :class:`LineParameters` class and
                can be used by multiple lines.

            length:
                The length of the line (in km).

            ground:
                The ground element attached to the line if it has shunt admittance.

            geometry:
                The geometry of the line i.e. the linestring.
        """
        super().__init__(
            id, bus1, bus2, geometry=geometry, parameters=parameters, length=length, ground=ground, phases="a"
        )
