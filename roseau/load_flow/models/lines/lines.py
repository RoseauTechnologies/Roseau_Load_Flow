import logging
from typing import Any, Optional

import numpy as np
from pint import Quantity
from shapely import LineString, Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.grounds import Ground
from roseau.load_flow.models.lines.parameters import LineParameters
from roseau.load_flow.models.sources import VoltageSource
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import BranchType

logger = logging.getLogger(__name__)


class Switch(AbstractBranch):
    """A general purpose switch branch."""

    branch_type = BranchType.SWITCH

    allowed_phases = frozenset(Bus.allowed_phases | {"a", "b", "c", "n"})
    """The allowed phases for a switch are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"``
    - P-P or P-P-N: ``"ab"``, ``"bc"``, ``"ca"``, "abn"``, ``"bcn"``, ``"can"``
    - P or P-N: ``"a"``, ``"b"``, ``"c"``, ``"an"``, ``"bn"``, ``"cn"``
    - N: ``"n"``
    """

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
            phases = phases.replace("ac", "ca")
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
        visited_1: set[Element] = set()
        elements: list[Element] = [self.bus1]
        while elements:
            element = elements.pop(-1)
            visited_1.add(element)
            for e in element._connected_elements:
                if e not in visited_1 and (isinstance(e, Bus) or isinstance(e, Switch)) and e != self:
                    elements.append(e)
        visited_2: set[Element] = set()
        elements = [self.bus2]
        while elements:
            element = elements.pop(-1)
            visited_2.add(element)
            for e in element._connected_elements:
                if e not in visited_2 and (isinstance(e, Bus) or isinstance(e, Switch)) and e != self:
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


class Line(AbstractBranch):
    """An electrical line PI model with series impedance and optional shunt admittance.

    .. math::
        V_1 &= a \\cdot V_2 - b \\cdot I_2 + g \\cdot V_{\\mathrm{g}} \\\\
        I_1 &= c \\cdot V_2 - d \\cdot I_2 + h \\cdot V_{\\mathrm{g}} \\\\
        I_{\\mathrm{g}} &= f^t \\cdot \\left(V_1 + V_2 - 2\\cdot V_{\\mathrm{g}}\\right)

    where

    .. math::
        a &= \\mathcal{I}_4 + \\dfrac{1}{2} \\cdot Z \\cdot Y  \\\\
        b &= Z  \\\\
        c &= Y + \\dfrac{1}{4}\\cdot Y \\cdot Z \\cdot Y  \\\\
        d &= \\mathcal{I}_4 + \\dfrac{1}{2} \\cdot Y \\cdot Z  \\\\
        f &= -\\dfrac{1}{2} \\cdot \\begin{pmatrix} y_{\\mathrm{ag}} & y_{\\mathrm{bg}} & y_{\\mathrm{cg}} &
        y_{\\mathrm{ng}} \\end{pmatrix} ^t  \\\\
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
    """The allowed phases for a line are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"``
    - P-P or P-P-N: ``"ab"``, ``"bc"``, ``"ca"``, "abn"``, ``"bcn"``, ``"can"``
    - P or P-N: ``"a"``, ``"b"``, ``"c"``, ``"an"``, ``"bn"``, ``"cn"``
    - N: ``"n"``
    """

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        parameters: LineParameters,
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

            parameters:
                The parameters of the line, an instance of :class:`LineParameters`.

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
            phases = phases.replace("ac", "ca")
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

        if isinstance(length, Quantity):
            length = length.m_as("km")

        self._initialized = False
        super().__init__(id, bus1, bus2, phases1=phases, phases2=phases, geometry=geometry, **kwargs)
        self.phases = phases
        self.ground = ground
        self.length = length
        self.parameters = parameters
        self._initialized = True

    @property
    def parameters(self) -> LineParameters:
        """The parameters of the line."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: LineParameters) -> None:
        shape = (len(self.phases),) * 2
        if value.z_line.shape != shape:
            msg = f"Incorrect z_line dimensions for line {self.id!r}: {value.z_line.shape} instead of {shape}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE)

        if value.y_shunt is not None:
            if self._initialized and self.parameters.y_shunt is None:
                msg = "Cannot set line parameters with a shunt to a line that does not have shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            if value.y_shunt.shape != shape:
                msg = f"Incorrect y_shunt dimensions for line {self.id!r}: {value.y_shunt.shape} instead of {shape}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE)
            if self.ground is None:
                msg = f"The ground element must be provided for line {self.id!r} with shunt admittance."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)
            self._connect(self.ground)
        else:
            if self._initialized and self.parameters.y_shunt is not None:
                msg = "Cannot set line parameters without a shunt to a line that has shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
        self._parameters = value
        self._invalidate_network_results()

    def _res_series_power_losses_getter(self, warning: bool) -> np.ndarray:
        pot1, pot2 = self._res_potentials_getter(warning)
        du_line = pot1 - pot2
        z_line = self.parameters.z_line * self.length
        i_line = np.linalg.inv(z_line) @ du_line  # Zₗ x Iₗ = ΔU -> I = Zₗ⁻¹ x ΔU
        return du_line * i_line.conj()  # Sₗ = ΔU.Iₗ*

    @property
    def res_series_power_losses(self) -> np.ndarray:
        """Get the power losses in the series elements of the line (VA)."""
        return self._res_series_power_losses_getter(warning=True)

    def _res_shunt_power_losses_getter(self, warning: bool) -> np.ndarray:
        y_shunt = self.parameters.y_shunt
        if y_shunt is None:
            return np.zeros(len(self.phases), dtype=np.complex_)
        assert self.ground is not None
        pot1, pot2 = self._res_potentials_getter(warning)
        vg = self.ground.res_potential
        y_shunt = y_shunt * self.length
        yg = y_shunt.sum(axis=1)  # y_ig = Y_ia + Y_ib + Y_ic + Y_in for i in {a, b, c, n}
        i1_shunt = (y_shunt @ pot1 - yg * vg) / 2
        i2_shunt = (y_shunt @ pot2 - yg * vg) / 2
        return pot1 * i1_shunt.conj() + pot2 * i2_shunt.conj()

    @property
    def res_shunt_power_losses(self) -> np.ndarray:
        """Get the power losses in the shunt elements of the line (VA)."""
        return self._res_shunt_power_losses_getter(warning=True)

    def _res_power_losses_getter(self, warning: bool) -> np.ndarray:
        series_losses = self._res_series_power_losses_getter(warning)
        shunt_losses = self._res_shunt_power_losses_getter(warning=False)  # we warn on the previous line
        return series_losses + shunt_losses

    @property
    def res_power_losses(self) -> np.ndarray:
        """Get the power losses in the line (VA)."""
        return self._res_power_losses_getter(warning=True)

    #
    # Json Mixin interface
    #
    def to_dict(self) -> JsonDict:
        res = {**super().to_dict(), "length": self.length, "params_id": self.parameters.id}
        if self.ground is not None:
            res["ground"] = self.ground.id
        return res
