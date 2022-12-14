import logging
from typing import Any, Optional

from pint import Quantity
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import AbstractBranch, Ground, Phases
from roseau.load_flow.models.lines.line_characteristics import LineCharacteristics
from roseau.load_flow.models.voltage_sources import VoltageSource
from roseau.load_flow.utils.types import BranchType
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class Switch(AbstractBranch):
    """A general purpose switch branch."""

    branch_type = BranchType.SWITCH

    def __init__(
        self, id: Any, phases: Phases, bus1: Bus, bus2: Bus, geometry: Optional[Point] = None, **kwargs
    ) -> None:
        """Switch constructor.

        Args:
            id:
                The id of the branch.

            phases:
                The phases of the switch. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

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
        super().__init__(id=id, phases1=phases, phases2=phases, bus1=bus1, bus2=bus2, geometry=geometry, **kwargs)
        self._check_elements()
        self._check_loop()

    def _check_loop(self):
        """Check that there are no switch loop, raise an exception if it is the case"""
        visited_1 = set()
        elements = [self.connected_elements[0]]
        while elements:
            element = elements.pop(-1)
            visited_1.add(element)
            for e in element.connected_elements:
                if e not in visited_1 and (isinstance(e, Bus) or isinstance(e, Switch)) and e != self:
                    elements.append(e)
        visited_2 = set()
        elements = [self.connected_elements[1]]
        while elements:
            element = elements.pop(-1)
            visited_2.add(element)
            for e in element.connected_elements:
                if e not in visited_2 and (isinstance(e, Bus) or isinstance(e, Switch)) and e != self:
                    elements.append(e)
        if visited_1.intersection(visited_2):
            msg = f"There is a loop of switch involving the switch {self.id!r}. It is not allowed."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.SWITCHES_LOOP)

    def _check_elements(self):
        """Check that we can connect both elements."""
        element1 = self.connected_elements[0]
        element2 = self.connected_elements[1]
        if (
            isinstance(element1, Bus)
            and any(isinstance(e, VoltageSource) for e in element1.connected_elements)
            and isinstance(element2, Bus)
            and any(isinstance(e, VoltageSource) for e in element2.connected_elements)
        ):
            msg = (
                f"The voltage sources {element1.id!r} and {element2.id!r} are "
                f"connected with the switch {self.id!r}. It is not allowed."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION)


class Line(AbstractBranch):
    """An electrical line PI model with series impedance and optional shunt admittance.

    .. math::
        V_1 &= a \\cdot V_2 - b \\cdot I_2 + g \\cdot V_g \\\\
        I_1 &= c \\cdot V_2 - d \\cdot I_2 + h \\cdot V_g \\\\
        I_g &= f^t \\cdot \\left(V_1 + V_2 - 2\\cdot V_g\\right)

    where

    .. math::
        a &= \\mathcal{I}_5 + \\dfrac{1}{2} \\cdot Z \\cdot Y  \\\\
        b &= Z  \\\\
        c &= Y + \\dfrac{1}{4}\\cdot Y \\cdot Z \\cdot Y  \\\\
        d &= \\mathcal{I}_5 + \\dfrac{1}{2} \\cdot Y \\cdot Z  \\\\
        f &= -\\dfrac{1}{2} \\cdot \\begin{pmatrix} y_{ag} & y_{bg} & y_{cg} &y_{ng} \\end{pmatrix} ^t  \\\\
        g &= Z \\cdot f  \\\\
        h &= 2 \\cdot f + \\frac{1}{2}\\cdot Y \\cdot Z \\cdot f  \\\\

    If the line does not define a shunt admittance, the following simplified equations are used
    instead:

    .. math::
        \\left(V_1 - V_2\\right) &= Z \\cdot I_1 \\\\
        I_2 &= -I_1
    """

    branch_type = BranchType.LINE

    def __init__(
        self,
        id: Any,
        phases: Phases,
        bus1: Bus,
        bus2: Bus,
        line_characteristics: LineCharacteristics,
        length: float,
        ground: Optional[Ground] = None,
        geometry: Optional[LineString] = None,
        **kwargs,
    ):
        """Line constructor.

        Args:
            id:
                The id of the line.

            phases:
                The phases of the line. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

            bus1:
                The first bus (aka `"from_bus"`) to connect to the line.

            bus2:
                The second bus (aka `"to_bus"`) to connect to the line.

            line_characteristics:
                The characteristics of the line.

            length:
                The length of the line in km.

            ground:
                The ground element attached to the line if it has shunt admittance.

            geometry:
                The geometry of the line i.e. the linestring.
        """
        if geometry is not None and not isinstance(geometry, LineString):
            msg = f"The geometry for a {type(self).__name__} must be a linestring: {geometry.geom_type} provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)

        line_dimensions = (len(phases),) * 2
        if line_characteristics.z_line.shape != line_dimensions:
            msg = (
                f"Incorrect z_line dimensions for line {id!r}: {line_characteristics.z_line.shape} instead of "
                f"{line_dimensions}"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE)

        super().__init__(id=id, phases1=phases, phases2=phases, bus1=bus1, bus2=bus2, geometry=geometry, **kwargs)

        if line_characteristics.y_shunt is not None:
            if line_characteristics.y_shunt.shape != line_dimensions:
                msg = (
                    f"Incorrect y_shunt dimensions for line {id!r}: {line_characteristics.y_shunt.shape} instead of "
                    f"{line_dimensions}"
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE)

            if ground is None:
                msg = f"The ground element must be provided for line {id!r} with shunt admittance."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)
            self.connected_elements.append(ground)
            ground.connected_elements.append(self)

        self.phases = phases
        self.line_characteristics = line_characteristics
        self.ground = ground

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
        if self.line_characteristics.y_shunt is not None:
            if self.ground is not None and self.ground not in self.connected_elements:
                self.connected_elements.append(self.ground)
                self.ground.connected_elements.append(self)

    #
    # Json Mixin interface
    #
    @classmethod
    @ureg.wraps(None, (None, None, None, None, "km", None, None, None, None), strict=False)
    def from_dict(
        cls,
        id: Any,
        bus1: Bus,
        bus2: Bus,
        length: float,
        line_types: dict[str, LineCharacteristics],
        type_name: str,
        ground: Optional[Ground] = None,
        geometry: Optional[BaseGeometry] = None,
    ) -> "Line":
        """Line constructor from dict.

        Args:
            id:
                The id of the created line.

            bus1:
                Bus to connect to the line.

            bus2:
                Bus to connect to the line.

            length:
                Length of the line (km).

            line_types:
                A dictionary of line characteristics by type name.

            type_name:
                The name of the line type

            ground:
                The ground (optional for line models without a shunt admittance).

            geometry:
                The geometry of the line.

        Returns:
            The constructed line.
        """
        line_characteristics = line_types[type_name]
        n = line_characteristics.z_line.shape[0]
        # TODO: line phases should be provided in the branch dict. For now we assume 3-phase lines
        # so we can determine the number of phases from the z_line shape. This will not work for
        # single-phase lines.
        phases = "abc" if n == 3 else "abcn"
        return cls(
            id=id,
            phases=phases,
            bus1=bus1,
            bus2=bus2,
            ground=ground,
            line_characteristics=line_characteristics,
            length=length,
            geometry=geometry,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "length": self.length,
            "type_name": self.line_characteristics.type_name,
        }
