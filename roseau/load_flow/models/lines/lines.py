import logging
from typing import Any, Optional

from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.models.buses.buses import AbstractBus, VoltageSource
from roseau.load_flow.models.core.core import AbstractBranch, Ground
from roseau.load_flow.models.lines.line_characteristics import LineCharacteristics
from roseau.load_flow.utils.exceptions import ThundersValueError
from roseau.load_flow.utils.types import BranchType

logger = logging.getLogger(__name__)


class Switch(AbstractBranch):
    type = BranchType.SWITCH

    def __init__(
        self, id_: Any, n: int, bus1: AbstractBus, bus2: AbstractBus, geometry: Optional[Point] = None
    ) -> None:
        """Switch constructor.

        Args:
            id_:
                The id of the branch.

            bus1:
                Bus to connect to the switch.

            bus2:
                Bus to connect to the switch.

            geometry:
                The geometry of the switch.
        """
        if geometry is not None and not isinstance(geometry, Point):
            msg = f"The geometry for a {type(self)} must be a point: {geometry.geom_type} provided."
            logger.error(msg)
            raise ThundersValueError(msg)
        super().__init__(id_=id_, n1=n, n2=n, bus1=bus1, bus2=bus2, geometry=geometry)
        self._check_elements()
        self._check_loop()

    def to_dict(self) -> dict[str, Any]:
        res = super().to_dict()
        res["type"] = "switch"
        return res

    def _check_loop(self):
        """Check that there are no switch loop, raise an exception if it is the case"""
        visited_1 = set()
        elements = [self.connected_elements[0]]
        while elements:
            element = elements.pop(-1)
            visited_1.add(element)
            for e in element.connected_elements:
                if e not in visited_1 and (isinstance(e, AbstractBus) or isinstance(e, Switch)) and e != self:
                    elements.append(e)
        visited_2 = set()
        elements = [self.connected_elements[1]]
        while elements:
            element = elements.pop(-1)
            visited_2.add(element)
            for e in element.connected_elements:
                if e not in visited_2 and (isinstance(e, AbstractBus) or isinstance(e, Switch)) and e != self:
                    elements.append(e)
        if visited_1.intersection(visited_2):
            msg = f"There is a loop of switch involving the switch {self.id!r}. It is not allowed."
            logger.error(msg)
            raise ThundersValueError(msg)

    def _check_elements(self):
        """Check that we can connect both elements."""
        element1 = self.connected_elements[0]
        element2 = self.connected_elements[1]
        if isinstance(element1, VoltageSource) and isinstance(element2, VoltageSource):
            msg = (
                f"The voltage sources {element1.id!r} and {element2.id!r} are "
                f"connected with the switch {self.id!r}. It is not allowed."
            )
            logger.error(msg)
            raise ThundersValueError(msg)


class Line(AbstractBranch):
    type = BranchType.LINE

    def __init__(
        self,
        id_: Any,
        n: int,
        bus1: AbstractBus,
        bus2: AbstractBus,
        line_characteristics: LineCharacteristics,
        length: float,
        geometry: Optional[LineString] = None,
    ):
        """Line constructor.

        Args:
            id_:
                The id of the branch.

            n:
                number of phases of the line.

            bus1:
                bus to connect to the line.

            bus2:
                bus to connect to the line.

            line_characteristics:
                The characteristics of the line.

            length:
                The length of the line in km.

            geometry:
                The geometry of the line.
        """
        if geometry is not None and not isinstance(geometry, LineString):
            msg = f"The geometry for a {type(self)} must be a linestring: {geometry.geom_type} provided."
            logger.error(msg)
            raise ThundersValueError(msg)

        if line_characteristics.z_line.shape != (n, n):
            msg = (
                f"Incorrect z_line dimensions for line {id_!r}: {line_characteristics.z_line.shape} instead of "
                f"({n}, {n})"
            )
            logger.error(msg)
            raise ThundersValueError(msg)
        if line_characteristics.y_shunt is not None and line_characteristics.y_shunt.shape != (n, n):
            msg = (
                f"Incorrect y_shunt dimensions for line {id_!r}: {line_characteristics.y_shunt.shape} instead of "
                f"({n}, {n})"
            )
            logger.error(msg)
            raise ThundersValueError(msg)

        super().__init__(n1=n, n2=n, bus1=bus1, bus2=bus2, id_=id_, geometry=geometry)
        self.n = n
        self.line_characteristics = line_characteristics
        self.length = length

    @staticmethod
    def from_dict(
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        length: float,
        line_types: dict[str, LineCharacteristics],
        type_name: str,
        ground: Optional[Ground] = None,
        geometry: Optional[BaseGeometry] = None,
    ) -> "Line":
        """Line constructor from dict.

        Args:
            line_types:
                A dictionary of line characteristics by type name.

            type_name:
                The name of the line type

            id_:
                The id of the created line.

            bus1:
                Bus to connect to the line.

            bus2:
                Bus to connect to the line.

            length:
                Length of the line (km).

            ground:
                The ground (optional for SimplifiedLine models).

            geometry:
                The geometry of the line.

        Returns:
            The constructed line.
        """
        line_characteristics = line_types[type_name]
        n = line_characteristics.z_line.shape[0]
        if line_characteristics.y_shunt is None:
            return SimplifiedLine(
                id_=id_,
                n=n,
                bus1=bus1,
                bus2=bus2,
                line_characteristics=line_characteristics,
                length=length,
                geometry=geometry,
            )
        else:
            return ShuntLine(
                id_=id_,
                n=n,
                bus1=bus1,
                bus2=bus2,
                ground=ground,
                line_characteristics=line_characteristics,
                length=length,
                geometry=geometry,
            )

    def to_dict(self) -> dict[str, Any]:
        res = super().to_dict()
        res.update(
            {
                "length": self.length,
                "type_name": self.line_characteristics.type_name,
                "type": "line",
            }
        )
        return res


class SimplifiedLine(Line):
    def __init__(
        self,
        id_: Any,
        n: int,
        bus1: AbstractBus,
        bus2: AbstractBus,
        line_characteristics: LineCharacteristics,
        length: float,
        geometry: Optional[BaseGeometry] = None,
    ) -> None:
        """SimplifiedLine constructor.

        Args:
            id_:
                The id of the branch.

            n:
                Number of phases of the line.

            bus1:
                Bus to connect to the line.

            bus2:
                Bus to connect to the line.

            line_characteristics:
                The characteristics of the line.

            length:
                The length of the line in km.

            geometry:
                The geometry of the line.
        """
        super().__init__(
            n=n,
            bus1=bus1,
            bus2=bus2,
            id_=id_,
            length=length,
            line_characteristics=line_characteristics,
            geometry=geometry,
        )

        if line_characteristics.y_shunt is not None:
            logger.warning(
                f"The simplified line {self.id!r} has been given a line characteristic "
                f"{self.line_characteristics.type_name} with a shunt. The shunt part will be ignored."
            )


class ShuntLine(Line):
    def __init__(
        self,
        id_: Any,
        n: int,
        bus1: AbstractBus,
        bus2: AbstractBus,
        ground: Ground,
        line_characteristics: LineCharacteristics,
        length: float,
        geometry: Optional[BaseGeometry] = None,
    ) -> None:
        """ShuntLine constructor.

        Args:
            n:
                Number of phases of the line.

            bus1:
                Bus to connect to the line.

            bus2:
                Bus to connect to the line.

            ground:
                The ground.

            id_:
                The id of the branch.

            line_characteristics:
                The characteristics of the line.

            length:
                The length of the line in km.

            geometry:
                The geometry of the line.
        """
        super().__init__(
            n=n,
            bus1=bus1,
            bus2=bus2,
            id_=id_,
            line_characteristics=line_characteristics,
            length=length,
            geometry=geometry,
        )

        self.connected_elements.append(ground)
        ground.connected_elements.append(self)
