import logging
from typing import Any, Optional

from pint import Quantity
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import AbstractBranch, Ground
from roseau.load_flow.models.lines.line_characteristics import LineCharacteristics
from roseau.load_flow.models.voltage_sources import VoltageSource
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import BranchType, ureg

logger = logging.getLogger(__name__)


class Switch(AbstractBranch):
    """A general purpose switch branch."""

    branch_type = BranchType.SWITCH

    allowed_phases = frozenset(Bus.allowed_phases | {"a", "b", "c", "n"})

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        phases: Optional[str] = None,
        geometry: Optional[Point] = None,
        **kwargs: Any,
    ) -> None:
        """Switch constructor.

        Args:
            id:
                A unique ID of the switch in the network branches.

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
        if phases is None:
            phases = "".join(p for p in bus1.phases if p in bus2.phases)  # can't use set because order is important
        else:
            # Also check they are in the intersection of buses phases
            self._check_phases(id, phases=phases)
            buses_phases = set(bus1.phases) & set(bus2.phases)
            phases_not_in_buses = set(phases) - buses_phases
            if phases_not_in_buses:
                msg = (
                    f"Phases {sorted(phases_not_in_buses)} of switch {id!r} are not in the common phases "
                    f"{sorted(buses_phases)} of buses {bus1.id!r} and {bus2.id!r}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        if geometry is not None and not isinstance(geometry, Point):
            msg = f"The geometry for a {type(self)} must be a point: {geometry.geom_type} provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)
        super().__init__(id=id, phases1=phases, phases2=phases, bus1=bus1, bus2=bus2, geometry=geometry, **kwargs)
        self.phases = phases
        self._check_elements()
        self._check_loop()

    def _check_loop(self) -> None:
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

    def _check_elements(self) -> None:
        """Check that we can connect both elements."""
        e1 = self.connected_elements[0]
        e2 = self.connected_elements[1]
        if (
            isinstance(e1, Bus)
            and any(isinstance(e, VoltageSource) for e in e1.connected_elements)
            and isinstance(e2, Bus)
            and any(isinstance(e, VoltageSource) for e in e2.connected_elements)
        ):
            msg = (
                f"The buses {e1.id!r} and {e2.id!r} both have a voltage source and are "
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

    allowed_phases = frozenset(Bus.allowed_phases | {"a", "b", "c", "n"})

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        line_characteristics: LineCharacteristics,
        length: float,
        phases: Optional[str] = None,
        ground: Optional[Ground] = None,
        geometry: Optional[LineString] = None,
        **kwargs: Any,
    ) -> None:
        """Line constructor.

        Args:
            id:
                A unique ID of the line in the network branches.

            bus1:
                The first bus (aka `"from_bus"`) to connect to the line.

            bus2:
                The second bus (aka `"to_bus"`) to connect to the line.

            line_characteristics:
                The characteristics of the line.

            length:
                The length of the line in km.

            phases:
                The phases of the line. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the line must be present in the phases of
                both connected buses. By default, the phases common to both buses are used.

            ground:
                The ground element attached to the line if it has shunt admittance.

            geometry:
                The geometry of the line i.e. the linestring.
        """
        if phases is None:
            phases = "".join(p for p in bus1.phases if p in bus2.phases)  # can't use set because order is important
        else:
            # Also check they are in the intersection of buses phases
            self._check_phases(id, phases=phases)
            buses_phases = set(bus1.phases) & set(bus2.phases)
            phases_not_in_buses = set(phases) - buses_phases
            if phases_not_in_buses:
                msg = (
                    f"Phases {sorted(phases_not_in_buses)} of line {id!r} are not in the common phases "
                    f"{sorted(buses_phases)} of buses {bus1.id!r} and {bus2.id!r}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
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

        super().__init__(id, bus1, bus2, phases1=phases, phases2=phases, geometry=geometry, **kwargs)

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
            self._connect(ground)

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
        if self.line_characteristics.y_shunt is not None and self.ground is not None:
            self._connect(self.ground)  # handles already connected case

    #
    # Json Mixin interface
    #
    @classmethod
    @ureg.wraps(None, (None, None, None, None, "km", None, None, None, None), strict=False)
    def from_dict(
        cls,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        length: float,
        line_type: LineCharacteristics,
        phases: Optional[str] = None,
        ground: Optional[Ground] = None,
        geometry: Optional[BaseGeometry] = None,
    ) -> "Line":
        """Line constructor from dict.

        Args:
            id:
                A unique ID of the line in the network branches.

            bus1:
                The first bus to connect to the line.

            bus2:
                The second bus to connect to the line.

            length:
                Length of the line (km).

            line_type:
                The line characteristics.

            ground:
                The ground (optional for line models without a shunt admittance).

            geometry:
                The geometry of the line.

        Returns:
            The constructed line.
        """
        return cls(
            id=id,
            bus1=bus1,
            bus2=bus2,
            line_characteristics=line_type,
            length=length,
            phases=phases,
            ground=ground,
            geometry=geometry,
        )

    def to_dict(self) -> JsonDict:
        res = {**super().to_dict(), "length": self.length, "type_id": self.line_characteristics.id}
        if self.ground is not None:
            res["ground"] = self.ground.id
        return res
