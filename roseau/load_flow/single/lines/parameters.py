import logging

from roseau.load_flow.models.lines.parameters import LineParameters as TriLineParameters
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import (
    ConductorType,
    InsulatorType,
    LineType,
)

logger = logging.getLogger(__name__)


class LineParameters(TriLineParameters):
    """Parameters that define electrical models of lines."""

    @ureg_wraps(None, (None, None, "ohm/km", "S/km", "A", None, None, None, "mm²"))
    def __init__(
        self,
        id: Id,
        z_line: complex,
        y_shunt: complex | None = None,
        max_current: float | None = None,
        line_type: LineType | None = None,
        conductor_type: ConductorType | None = None,
        insulator_type: InsulatorType | None = None,
        section: float | Q_[float] | None = None,
    ) -> None:
        """LineParameters constructor.

        Args:
            id:
                A unique ID of the line parameters, typically its canonical name.

            z_line:
                 The Z matrix of the line (Ohm/km).

            y_shunt:
                The Y matrix of the line (Siemens/km). This field is optional if the line has no shunt part.

            max_current:
                The maximum current loading of the line (A). The maximum current is optional, it is
                not used in the load flow but can be used to check for overloading.
                See also :meth:`Line.res_violated <roseau.load_flow.Line.res_violated>`.

            line_type:
                The type of the line (overhead, underground, twisted). The line type is optional,
                it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            conductor_type:
                The type of the conductor material (Aluminum, Copper, ...). The conductor type is
                optional, it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            insulator_type:
                The type of the cable insulator (PVC, XLPE, ...). The insulator type is optional,
                it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.
        """
        y_shunt_tri = [[y_shunt]] if y_shunt is not None else None
        super().__init__(
            id,
            z_line=[[z_line]],
            y_shunt=y_shunt_tri,
            max_current=max_current,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
        )
