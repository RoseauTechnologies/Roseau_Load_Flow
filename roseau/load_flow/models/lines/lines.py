import logging
from typing import Any, Optional

from pint import Quantity
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import AbstractBus, VoltageSource
from roseau.load_flow.models.core import AbstractBranch, Ground
from roseau.load_flow.models.lines.line_characteristics import LineCharacteristics
from roseau.load_flow.utils.types import BranchType
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class Switch(AbstractBranch):
    """A general purpose switch branch."""

    branch_type = BranchType.SWITCH

    def __init__(
        self, id: Any, n: int, bus1: AbstractBus, bus2: AbstractBus, geometry: Optional[Point] = None, **kwargs
    ) -> None:
        """Switch constructor.

        Args:
            id:
                The id of the branch.

            n:
                The number of ports of the extremity buses.

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
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)
        super().__init__(id=id, n1=n, n2=n, bus1=bus1, bus2=bus2, geometry=geometry, **kwargs)
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
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.SWITCHES_LOOP)

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
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION)


class AbstractLine(AbstractBranch):
    """An abstract class for all lines of this package."""

    branch_type = BranchType.LINE
    _simplified_line_class: Optional[type["SimplifiedLine"]] = None
    _shunt_line_class: Optional[type["ShuntLine"]] = None

    def __init__(
        self,
        id: Any,
        n: int,
        bus1: AbstractBus,
        bus2: AbstractBus,
        line_characteristics: LineCharacteristics,
        length: float,
        geometry: Optional[LineString] = None,
        **kwargs,
    ):
        """Line constructor.

        Args:
            id:
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
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)

        if line_characteristics.z_line.shape != (n, n):
            msg = (
                f"Incorrect z_line dimensions for line {id!r}: {line_characteristics.z_line.shape} instead of "
                f"({n}, {n})"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE)
        if line_characteristics.y_shunt is not None and line_characteristics.y_shunt.shape != (n, n):
            msg = (
                f"Incorrect y_shunt dimensions for line {id!r}: {line_characteristics.y_shunt.shape} instead of "
                f"({n}, {n})"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE)

        super().__init__(n1=n, n2=n, bus1=bus1, bus2=bus2, id=id, geometry=geometry, **kwargs)
        self.n = n
        self.line_characteristics = line_characteristics

        if isinstance(length, Quantity):
            length = length.m_as("km")
        self.length = length

    def update_characteristics(self, line_characteristics: LineCharacteristics) -> None:
        """Change the line parameters.

        Args:
            line_characteristics:
                The line characteristics of the new line parameters.
        """
        self.line_characteristics = line_characteristics

    #
    # Json Mixin interface
    #
    @classmethod
    @ureg.wraps(None, (None, None, None, None, "km", None, None, None, None), strict=False)
    def from_dict(
        cls,
        id: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        length: float,
        line_types: dict[str, LineCharacteristics],
        type_name: str,
        ground: Optional[Ground] = None,
        geometry: Optional[BaseGeometry] = None,
    ) -> "AbstractLine":
        """Line constructor from dict.

        Args:
            line_types:
                A dictionary of line characteristics by type name.

            type_name:
                The name of the line type

            id:
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
            return cls._simplified_line_class(
                id=id,
                n=n,
                bus1=bus1,
                bus2=bus2,
                line_characteristics=line_characteristics,
                length=length,
                geometry=geometry,
            )
        else:
            return cls._shunt_line_class(
                id=id,
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


class SimplifiedLine(AbstractLine):
    """A line without shunt elements.

    .. math::
        \\left(V_1 - V_2\\right) &= Z \\cdot I_1 \\\\
        I_2 &= -I_1
    """

    def __init__(
        self,
        id: Any,
        n: int,
        bus1: AbstractBus,
        bus2: AbstractBus,
        line_characteristics: LineCharacteristics,
        length: float,
        geometry: Optional[BaseGeometry] = None,
        **kwargs,
    ) -> None:
        """SimplifiedLine constructor.

        Args:
            id:
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
            id=id,
            length=length,
            line_characteristics=line_characteristics,
            geometry=geometry,
            **kwargs,
        )

        if line_characteristics.y_shunt is not None:
            logger.warning(
                f"The simplified line {self.id!r} has been given a line characteristic "
                f"{self.line_characteristics.type_name} with a shunt. The shunt part will be ignored."
            )

    def update_characteristics(self, line_characteristics: LineCharacteristics) -> None:
        """Change the line parameters.

        Args:
            line_characteristics:
                The line characteristics of the new line parameters.
        """
        if line_characteristics.y_shunt is not None:
            logger.warning(
                f"The simplified line {self.id!r} has been given a line characteristic "
                f"{self.line_characteristics.type_name} with a shunt. The shunt part will be ignored."
            )

        super().update_characteristics(line_characteristics=line_characteristics)


class ShuntLine(AbstractLine):
    """A PI line model

    .. math::
        V_1 &= a \\cdot V_2 - b \\cdot I_2 + g \\cdot V_g \\\\
        I_1 &= c \\cdot V_2 - d \\cdot I_2 + h \\cdot V_g \\\\
        I_g &= f^t \\cdot \\left(V_1 + V_2 - 2\\cdot V_g\\right)

    with

    .. math::
        a &= \\mathcal{I}_5 + \\dfrac{1}{2} \\cdot Z \\cdot Y  \\\\
        b &= Z  \\\\
        c &= Y + \\dfrac{1}{4}\\cdot Y \\cdot Z \\cdot Y  \\\\
        d &= \\mathcal{I}_5 + \\dfrac{1}{2} \\cdot Y \\cdot Z  \\\\
        f &= -\\dfrac{1}{2} \\cdot \\begin{pmatrix} y_{ag} & y_{bg} & y_{cg} &y_{ng} \\end{pmatrix} ^t  \\\\
        g &= Z \\cdot f  \\\\
        h &= 2 \\cdot f + \\frac{1}{2}\\cdot Y \\cdot Z \\cdot f  \\\\

    """

    def __init__(
        self,
        id: Any,
        n: int,
        bus1: AbstractBus,
        bus2: AbstractBus,
        ground: Ground,
        line_characteristics: LineCharacteristics,
        length: float,
        geometry: Optional[BaseGeometry] = None,
        **kwargs,
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

            id:
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
            id=id,
            line_characteristics=line_characteristics,
            length=length,
            geometry=geometry,
            **kwargs,
        )

        self.connected_elements.append(ground)
        ground.connected_elements.append(self)


AbstractLine._simplified_line_class = SimplifiedLine
AbstractLine._shunt_line_class = ShuntLine
