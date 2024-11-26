import logging
import warnings
from typing import Final

import numpy as np
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.grounds import Ground
from roseau.load_flow.models.lines.parameters import InsulatorArray, LineParameters, MaterialArray
from roseau.load_flow.typing import ComplexArray, FloatArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils.types import LineType
from roseau.load_flow_engine.cy_engine import CyShuntLine, CySimplifiedLine

logger = logging.getLogger(__name__)


class Line(AbstractBranch):
    """An electrical line PI model with series impedance and optional shunt admittance."""

    allowed_phases: Final = frozenset(Bus.allowed_phases | {"a", "b", "c", "n"})
    """The allowed phases for a line are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"``
    - P-P or P-P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"abn"``, ``"bcn"``, ``"can"``
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
        length: float | Q_[float],
        phases: str | None = None,
        ground: Ground | None = None,
        max_loading: float | Q_[float] = 1,
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

            phases:
                The phases of the line. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the line must be present in the phases of
                both connected buses. By default, the phases common to both buses are used.

            ground:
                The ground element attached to the line if it has shunt admittance.

            max_loading:
                The maximum loading of the line (unitless).  It is not used in the load flow. It is used with the
                `ampacities` of the :class:`LineParameters` to compute the
                :meth:`~roseau.load_flow.Line.max_currents` of the line.

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

        self._initialized = False
        super().__init__(id=id, bus1=bus1, bus2=bus2, phases1=phases, phases2=phases, geometry=geometry)
        self.ground = ground
        self.length = length
        self.parameters = parameters
        self.max_loading = max_loading
        self._initialized = True
        with_shunt = parameters.with_shunt(phases=phases)

        # Handle the ground
        if self.ground is not None and not with_shunt:
            warnings.warn(
                message=(
                    f"The ground element must not be provided for line {self.id!r} as it does not have a shunt "
                    f"admittance."
                ),
                category=UserWarning,
                stacklevel=2,
            )
            self.ground = None
        elif with_shunt:
            # Connect the ground
            self._connect(self.ground)

        z_line = parameters._z_line_without_unit(phases=phases)
        if with_shunt:
            y_shunt = self.parameters._y_shunt_without_unit(phases=phases)
            self._cy_element = CyShuntLine(
                n=self._n1,
                y_shunt=y_shunt.reshape(self._n1 * self._n2) * self._length,
                z_line=z_line.reshape(self._n1 * self._n2) * self._length,
            )
        else:
            y_shunt = np.zeros_like(z_line, dtype=np.complex128)
            self._cy_element = CySimplifiedLine(n=self._n1, z_line=z_line.reshape(self._n1 * self._n2) * self._length)
        self._cy_connect()
        if with_shunt:
            ground._cy_element.connect(self._cy_element, [(0, self._n1 + self._n1)])

        # Cache values related to the line parameters
        self._z_line = z_line * self._length
        self._y_shunt = y_shunt * self._length
        self._with_shunt = with_shunt
        self._z_line_inv = np.linalg.inv(self._z_line)
        self._yg = self._y_shunt.sum(axis=1)  # y_ig = Y_ia + Y_ib + Y_ic + Y_in for i in {a, b, c, n}
        self._materials = parameters.materials(phases=phases)
        self._sections = parameters.sections(phases=phases)
        self._insulators = parameters.insulators(phases=phases)
        self._ampacities = parameters.ampacities(phases=phases)

    def __repr__(self) -> str:
        s = (
            f"<{type(self).__name__}: id={self.id!r}, bus1={self.bus1.id!r}, bus2={self.bus2.id!r}, "
            f"phases1={self.phases1!r}, phases2={self.phases2!r}"
        )
        for attr, val, tp in (("length", self._length, float), ("max_loading", self._max_loading, float)):
            if val is not None:
                s += f", {attr}={tp(val)!r}"
        s += ">"
        return s

    @property
    def phases(self) -> str:
        """The phases of the line. This is an alias for :attr:`phases1` and :attr:`phases2`."""
        return self._phases1

    def _update_internal_parameters(self, parameters: LineParameters, length: float) -> None:
        """Update the internal parameters of the line."""
        self._parameters = parameters
        self._length = length

        # Update the cache values
        self._with_shunt = parameters.with_shunt(phases=self._phases1)
        self._z_line = parameters._z_line_without_unit(phases=self._phases1) * self._length
        if self._with_shunt:
            self._y_shunt = parameters._y_shunt_without_unit(phases=self._phases1) * self._length
        else:
            self._y_shunt = np.zeros_like(self._z_line, dtype=np.complex128)
        self._z_line_inv = np.linalg.inv(self._z_line)
        self._yg = self._y_shunt.sum(axis=1)
        self._materials = parameters.materials(phases=self._phases1)
        self._sections = parameters.sections(phases=self._phases1)
        self._insulators = parameters.insulators(phases=self._phases1)
        self._ampacities = parameters.ampacities(phases=self._phases1)

        # Update the cy_element
        if self._cy_element is not None:
            if self._with_shunt:
                self._cy_element.update_line_parameters(
                    y_shunt=self._y_shunt.reshape(self._n1 * self._n2), z_line=self._z_line.reshape(self._n1 * self._n2)
                )
            else:
                self._cy_element.update_line_parameters(z_line=self._z_line.reshape(self._n1 * self._n2))

    @property
    @ureg_wraps("km", (None,))
    def length(self) -> Q_[float]:
        """The length of the line (in km)."""
        return self._length

    @length.setter
    @ureg_wraps(None, (None, "km"))
    def length(self, value: float | Q_[float]) -> None:
        if value <= 0:
            msg = f"A line length must be greater than 0. {value:.2f} km provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE)
        self._invalidate_network_results()
        self._length = value
        if self._initialized:
            self._update_internal_parameters(self._parameters, value)

    @property
    def parameters(self) -> LineParameters:
        """The parameters defining the impedance and shunt admittance matrices of line model."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: LineParameters) -> None:
        value_with_shunt = value.with_shunt(phases=self._phases1)
        if value_with_shunt:
            if self._initialized and not self._with_shunt:
                msg = "Cannot set line parameters with a shunt to a line that does not have shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            if self.ground is None:
                msg = f"The ground element must be provided for line {self.id!r} with shunt admittance."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)
        else:
            if self._initialized and self._with_shunt:
                msg = "Cannot set line parameters without a shunt to a line that has shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
        self._invalidate_network_results()
        self._parameters = value
        if self._initialized:
            self._update_internal_parameters(value, self._length)

    @property
    @ureg_wraps("", (None,))
    def max_loading(self) -> Q_[float]:
        """The maximum loading of the line (unitless)"""
        return self._max_loading

    @max_loading.setter
    @ureg_wraps(None, (None, ""))
    def max_loading(self, value: float | Q_[float]) -> None:
        if value <= 0:
            msg = f"Maximum loading must be positive: {value} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE)
        self._max_loading = value

    #
    # Properties related to the parameters
    #
    @property
    @ureg_wraps("ohm", (None,))
    def z_line(self) -> Q_[ComplexArray]:
        """Impedance of the line (in Ohm)."""
        return self._z_line

    @property
    @ureg_wraps("S", (None,))
    def y_shunt(self) -> Q_[ComplexArray]:
        """Shunt admittance of the line (in Siemens)."""
        return self._y_shunt

    @property
    def with_shunt(self) -> bool:
        return self._with_shunt

    @property
    def line_type(self) -> LineType | None:
        """The type of the line. Informative only, it has no impact on the load flow."""
        return self._parameters.line_type

    @property
    def materials(self) -> MaterialArray | None:
        """The materials of the conductors. Informative only, it has no impact on the load flow."""
        return self._materials

    @property
    def insulators(self) -> InsulatorArray | None:
        """The insulators of the conductors. Informative only, it has no impact on the load flow."""
        return self._insulators

    @property
    def sections(self) -> Q_[FloatArray] | None:
        """The cross-section areas of the cable (in mm²). Informative only, it has no impact on the load flow."""
        return self._sections

    @property
    def ampacities(self) -> Q_[FloatArray] | None:
        """The ampacities of the line (A) if it is set. Informative only, it has no impact on the load flow."""
        return self._ampacities

    @property
    def max_currents(self) -> Q_[FloatArray] | None:
        """The maximum current of the line (in A). It takes into account the `max_loading` of the line and the
        `ampacities` of the parameters."""
        # Do not add a setter. Only `max_loading` can be altered by the user.
        return None if self._ampacities is None else Q_(self._ampacities * self._max_loading, "A")

    #
    # Load flow results
    #
    def _res_series_values_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        pot1, pot2 = self._res_potentials_getter(warning)  # V
        du_line = pot1 - pot2
        i_line = self._z_line_inv @ du_line  # Zₗ x Iₗ = ΔU -> I = Zₗ⁻¹ x ΔU
        return du_line, i_line

    def _res_series_currents_getter(self, warning: bool) -> ComplexArray:
        _, i_line = self._res_series_values_getter(warning)
        return i_line

    @property
    @ureg_wraps("A", (None,))
    def res_series_currents(self) -> Q_[ComplexArray]:
        """Get the current in the series elements of the line (in A)."""
        return self._res_series_currents_getter(warning=True)

    def _res_series_power_losses_getter(self, warning: bool) -> ComplexArray:
        du_line, i_line = self._res_series_values_getter(warning)
        return du_line * i_line.conj()  # Sₗ = ΔU.Iₗ*

    @property
    @ureg_wraps("VA", (None,))
    def res_series_power_losses(self) -> Q_[ComplexArray]:
        """Get the power losses in the series elements of the line (in VA)."""
        return self._res_series_power_losses_getter(warning=True)

    def _res_shunt_values_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray]:
        assert self._with_shunt, "This method only works when there is a shunt"
        assert self.ground is not None
        pot1, pot2 = self._res_potentials_getter(warning)
        vg = self.ground._res_potential_getter(warning=False)
        ig = self._yg * vg
        i1_shunt = (self._y_shunt @ pot1 - ig) / 2
        i2_shunt = (self._y_shunt @ pot2 - ig) / 2
        return pot1, pot2, i1_shunt, i2_shunt

    def _res_shunt_currents_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        if not self._with_shunt:
            zeros = np.zeros(self._n1, dtype=np.complex128)
            return zeros[:], zeros[:]
        _, _, cur1, cur2 = self._res_shunt_values_getter(warning)
        return cur1, cur2

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_shunt_currents(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """Get the currents in the shunt elements of the line (in A)."""
        return self._res_shunt_currents_getter(warning=True)

    def _res_shunt_power_losses_getter(self, warning: bool) -> ComplexArray:
        if not self._with_shunt:
            return np.zeros(self._n1, dtype=np.complex128)
        pot1, pot2, cur1, cur2 = self._res_shunt_values_getter(warning)
        return pot1 * cur1.conj() + pot2 * cur2.conj()

    @property
    @ureg_wraps("VA", (None,))
    def res_shunt_power_losses(self) -> Q_[ComplexArray]:
        """Get the power losses in the shunt elements of the line (in VA)."""
        return self._res_shunt_power_losses_getter(warning=True)

    def _res_power_losses_getter(self, warning: bool) -> ComplexArray:
        series_losses = self._res_series_power_losses_getter(warning)
        shunt_losses = self._res_shunt_power_losses_getter(warning=False)  # we warn on the previous line
        return series_losses + shunt_losses

    @property
    @ureg_wraps("VA", (None,))
    def res_power_losses(self) -> Q_[ComplexArray]:
        """Get the power losses in the line (in VA)."""
        return self._res_power_losses_getter(warning=True)

    @property
    def res_loading(self) -> Q_[FloatArray] | None:
        """Get the loading of the line (unitless)."""
        if self._ampacities is None:
            return None
        currents1, currents2 = self._res_currents_getter(warning=True)
        i_max = self._ampacities.m * self._max_loading
        return Q_(np.maximum(abs(currents1), abs(currents2)) / i_max, "")

    @property
    def res_violated(self) -> bool | None:
        """Whether the line current exceeds the maximal current of the line (computed with the parameters' ampacities
        and the maximal loading of the line itself).

        Returns ``None`` if the ampacities or the `max_loading` is not set are not set.
        """
        if self._ampacities is None:
            return None
        currents1, currents2 = self._res_currents_getter(warning=True)
        i_max = self._ampacities.m * self._max_loading
        # True if any phase is overloaded
        return bool((np.maximum(abs(currents1), abs(currents2)) > i_max).any())

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {
            "id": self.id,
            "phases": self.phases,
            "bus1": self.bus1.id,
            "bus2": self.bus2.id,
            "length": self._length,
            "params_id": self._parameters.id,
            "max_loading": self._max_loading,
        }
        if self.ground is not None:
            res["ground"] = self.ground.id
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        if include_results:
            currents1, currents2 = self._res_currents_getter(warning=True)
            res["results"] = {
                "currents1": [[i.real, i.imag] for i in currents1],
                "currents2": [[i.real, i.imag] for i in currents2],
            }
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents1, currents2 = self._res_currents_getter(warning)
        results = {
            "id": self.id,
            "phases": self.phases,
            "currents1": [[i.real, i.imag] for i in currents1],
            "currents2": [[i.real, i.imag] for i in currents2],
        }
        if full:
            potentials1, potentials2 = self._res_potentials_getter(warning=False)
            results["potentials1"] = [[v.real, v.imag] for v in potentials1]
            results["potentials2"] = [[v.real, v.imag] for v in potentials2]
            powers1, powers2 = self._res_powers_getter(
                warning=False,
                potentials1=potentials1,
                potentials2=potentials2,
                currents1=currents1,
                currents2=currents2,
            )
            results["powers1"] = [[s.real, s.imag] for s in powers1]
            results["powers2"] = [[s.real, s.imag] for s in powers2]
            voltages1, voltages2 = self._res_voltages_getter(
                warning=False, potentials1=potentials1, potentials2=potentials2
            )
            results["voltages1"] = [[v.real, v.imag] for v in voltages1]
            results["voltages2"] = [[v.real, v.imag] for v in voltages2]
            results["power_losses"] = [[s.real, s.imag] for s in self._res_power_losses_getter(warning=False)]
            results["series_currents"] = [[i.real, i.imag] for i in self._res_series_currents_getter(warning=False)]
            results["series_power_losses"] = [
                [s.real, s.imag] for s in self._res_series_power_losses_getter(warning=False)
            ]
            shunt_currents1, shunt_currents2 = self._res_shunt_currents_getter(warning=False)
            results["shunt_currents1"] = [[i.real, i.imag] for i in shunt_currents1]
            results["shunt_currents2"] = [[i.real, i.imag] for i in shunt_currents2]
            results["shunt_power_losses"] = [
                [s.real, s.imag] for s in self._res_shunt_power_losses_getter(warning=False)
            ]
        return results
