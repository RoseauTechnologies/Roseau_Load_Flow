import logging
from typing import Final, Self

import numpy as np
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch, AbstractBranchSide
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.grounds import Ground
from roseau.load_flow.models.line_parameters import LineParameters
from roseau.load_flow.typing import BoolArray, ComplexArray, ComplexMatrix, FloatArray, Id, JsonDict, ResultState
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import warn_external
from roseau.load_flow_engine.cy_engine import CyShuntLine, CySimplifiedLine

logger = logging.getLogger(__name__)


class Line(AbstractBranch["LineSide", CyShuntLine | CySimplifiedLine]):
    """An electrical line PI model with series impedance and optional shunt admittance."""

    element_type: Final = "line"
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
                A unique ID of the line in the network lines.

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
        phases = self._check_phases_common(id, bus1=bus1, bus2=bus2, phases=phases)
        self._initialized = False
        super().__init__(id=id, bus1=bus1, bus2=bus2, phases1=phases, phases2=phases, geometry=geometry)
        self._side1 = LineSide(branch=self, side=1, bus=bus1, phases=phases, connect_neutral=None)
        self._side2 = LineSide(branch=self, side=2, bus=bus2, phases=phases, connect_neutral=None)
        self._n = self._side1._n + self._side2._n + (1 if parameters.with_shunt else 0)
        self.ground = ground
        self.length = length
        self.parameters = parameters
        self.max_loading = max_loading
        self._initialized = True
        self._check_same_voltage_level()

        # Handle the ground
        if self.ground is not None and not self.with_shunt:
            warn_external(
                message=(
                    f"The ground element must not be provided for line {self.id!r} as it does not have a shunt "
                    f"admittance."
                ),
                category=UserWarning,
            )
            self.ground = None
        elif self.with_shunt:
            # Connect the ground
            self._connect(self.ground)

        # Cache values used in results calculations
        self._z_line = parameters._z_line * self._length
        self._y_shunt = parameters._y_shunt * self._length
        self._z_line_inv = np.linalg.inv(self._z_line)
        self._yg = self._y_shunt.sum(axis=1)  # y_ig = Y_ia + Y_ib + Y_ic + Y_in for i in {a, b, c, n}

        if parameters.with_shunt:
            self._cy_element = CyShuntLine(n=self._side1._n, y_shunt=self._y_shunt.ravel(), z_line=self._z_line.ravel())
        else:
            self._cy_element = CySimplifiedLine(n=self._side1._n, z_line=self._z_line.ravel())
        self._cy_connect()
        self._connect(bus1, bus2)
        if parameters.with_shunt:
            ground._cy_element.connect(self._cy_element, [(0, self._n - 1)])

        # Results
        self._res_ground_potential: complex | None = None

    def __repr__(self) -> str:
        s = f"{super().__repr__()[:-1]}, length={self._length!r}"
        if self.ground is not None:
            s += f", ground={self.ground.id!r}"
        if self._max_loading is not None:
            s += f", max_loading={self._max_loading!r}"
        s += ">"
        return s

    @property
    def phases(self) -> str:
        """The phases of the line. This is an alias for :attr:`phases1` and :attr:`phases2`."""
        return self._side1.phases

    def _update_internal_parameters(self) -> None:
        """Update the internal parameters of the line."""
        self._z_line = self._parameters._z_line * self._length
        self._y_shunt = self._parameters._y_shunt * self._length
        self._z_line_inv = np.linalg.inv(self._z_line)
        self._yg = self._y_shunt.sum(axis=1)

        if self._cy_initialized:
            if self._parameters.with_shunt:
                self._cy_element.update_line_parameters(y_shunt=self._y_shunt.ravel(), z_line=self._z_line.ravel())
            else:
                self._cy_element.update_line_parameters(z_line=self._z_line.ravel())

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
        self._length = float(value)
        if self._initialized:
            self._update_internal_parameters()

    @property
    def parameters(self) -> LineParameters:
        """The parameters defining the impedance and shunt admittance matrices of line model."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: LineParameters) -> None:
        self._check_compatible_phase_tech(value)
        old_parameters = self._parameters if self._initialized else None
        shape = (self._side1._n, self._side2._n)
        if value._z_line.shape != shape:
            msg = f"Incorrect z_line dimensions for line {self.id!r}: {value._z_line.shape} instead of {shape}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE)

        if value.with_shunt:
            if self._initialized and not self.with_shunt:
                msg = "Cannot set line parameters with a shunt to a line that does not have shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            if value._y_shunt.shape != shape:
                msg = f"Incorrect y_shunt dimensions for line {self.id!r}: {value._y_shunt.shape} instead of {shape}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE)
            if self.ground is None:
                msg = f"The ground element must be provided for line {self.id!r} with shunt admittance."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)
        else:
            if self._initialized and self.with_shunt:
                msg = "Cannot set line parameters without a shunt to a line that has shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
        self._update_network_parameters(old_parameters=old_parameters, new_parameters=value)
        self._invalidate_network_results()
        self._parameters = value
        if self._initialized:
            self._update_internal_parameters()

    @property
    @ureg_wraps("ohm", (None,))
    def z_line(self) -> Q_[ComplexMatrix]:
        """Impedance of the line (in Ohm)."""
        return self._parameters._z_line * self._length

    @property
    @ureg_wraps("S", (None,))
    def y_shunt(self) -> Q_[ComplexMatrix]:
        """Shunt admittance of the line (in Siemens)."""
        return self._parameters._y_shunt * self._length

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
        self._max_loading = float(value)

    @property
    def ampacities(self) -> Q_[FloatArray] | None:
        """The ampacities of the line (in A)."""
        # Do not add a setter. The user must know that if they change the ampacities, it changes
        # for all lines that share the parameters. It is better to set it on the parameters.
        return self._parameters.ampacities

    @property
    def max_currents(self) -> Q_[FloatArray] | None:
        """The maximum current of the line defined as `max_loading * parameters.ampacities` (in A)."""
        # Do not add a setter. Only `max_loading` can be altered by the user
        amp = self._parameters._ampacities
        return None if amp is None else Q_(amp * self._max_loading, "A")

    @property
    def with_shunt(self) -> bool:
        return self._parameters.with_shunt

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            super()._refresh_results()
            if self.with_shunt:
                self._res_ground_potential = self._cy_element.get_port_potential(self._n - 1)

    def _res_ground_potential_getter(self, warning: bool) -> complex:
        if not self.with_shunt:
            msg = (
                f"Ground potential is only available for lines with shunt components. Line "
                f"{self.id!r} does not have shunt components."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)
        self._refresh_results()
        return self._res_getter(value=self._res_ground_potential, warning=warning)

    def _res_series_values_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        pot1 = self._side1._res_potentials_getter(warning)
        pot2 = self._side2._res_potentials_getter(warning=False)  # # warn only once
        du_line = pot1 - pot2
        i_line = self._z_line_inv @ du_line  # Zₗ x Iₗ = ΔU -> I = Zₗ⁻¹ x ΔU
        return du_line, i_line

    def _res_series_currents_getter(self, warning: bool) -> ComplexArray:
        _, i_line = self._res_series_values_getter(warning)
        return i_line

    def _res_series_power_losses_getter(self, warning: bool) -> ComplexArray:
        du_line, i_line = self._res_series_values_getter(warning)
        return du_line * i_line.conjugate()  # Sₗ = ΔU.Iₗ*

    def _res_power_losses_getter(self, warning: bool) -> ComplexArray:
        series_losses = self._res_series_power_losses_getter(warning)
        shunt_losses1 = self._side1._res_shunt_losses_getter(warning=False)  # warn only once
        shunt_losses2 = self._side2._res_shunt_losses_getter(warning=False)  # warn only once
        return series_losses + shunt_losses1 + shunt_losses2

    def _res_loading_getter(self, warning: bool) -> FloatArray | None:
        if (amp := self._parameters._ampacities) is None:
            return None
        currents1 = self._side1._res_currents_getter(warning)
        currents2 = self._side2._res_currents_getter(warning=False)  # warn only once
        return np.maximum(abs(currents1), abs(currents2)) / amp

    def _res_state_getter(self) -> ResultState:
        """Get the state of the line based on its loading."""
        loading_array = self._res_loading_getter(warning=False)
        if loading_array is None:
            return "unknown"
        max_loading = self._max_loading
        loading = max(loading_array.tolist())
        if loading > max_loading:
            return "very-high"
        elif loading > 0.75 * max_loading:
            return "high"
        else:
            return "normal"

    @property
    @ureg_wraps("V", (None,))
    def res_ground_potential(self) -> Q_[complex]:
        """Get the potential of the ground port of the shunt line (in V)."""
        return self._res_ground_potential_getter(warning=True)

    @property
    @ureg_wraps("A", (None,))
    def res_series_currents(self) -> Q_[ComplexArray]:
        """Get the current in the series elements of the line (in A)."""
        return self._res_series_currents_getter(warning=True)

    @property
    @ureg_wraps("VA", (None,))
    def res_series_power_losses(self) -> Q_[ComplexArray]:
        """Get the power losses in the series elements of the line (in VA)."""
        return self._res_series_power_losses_getter(warning=True)

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_shunt_currents(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """Get the currents in the shunt elements of the line (in A)."""
        return (
            self._side1._res_shunt_currents_getter(warning=True),
            self._side2._res_shunt_currents_getter(warning=False),  # warn only once
        )  # type: ignore

    @property
    @ureg_wraps("VA", (None,))
    def res_shunt_power_losses(self) -> Q_[ComplexArray]:
        """Get the power losses in the shunt elements of the line (in VA)."""
        return (
            self._side1._res_shunt_losses_getter(warning=True)
            + self._side2._res_shunt_losses_getter(warning=False)  # warn only once
        )  # type: ignore

    @property
    @ureg_wraps("VA", (None,))
    def res_power_losses(self) -> Q_[ComplexArray]:
        """Get the power losses in the line (in VA)."""
        return self._res_power_losses_getter(warning=True)

    @property
    def res_loading(self) -> Q_[FloatArray] | None:
        """The loading of the line (unitless) if ``self.parameters.ampacities`` is set, else ``None``."""
        loading = self._res_loading_getter(warning=True)
        return None if loading is None else Q_(loading, "")

    @property
    def res_violated(self) -> BoolArray | None:
        """Whether the line current loading exceeds its maximal loading.

        Returns ``None`` if the ``self.parameters.ampacities`` is not set.
        """
        loading = self._res_loading_getter(warning=True)
        return None if loading is None else (loading > self._max_loading)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        results = data.get("results", None)
        self = super().from_dict(data, include_results=include_results)
        if include_results and results and self.with_shunt:
            self._res_ground_potential = complex(*results["ground_potential"])
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        line_dict = super()._to_dict(include_results)
        line_dict["max_loading"] = self._max_loading
        line_dict["params_id"] = self._parameters.id
        line_dict["length"] = self._length
        if self.ground is not None:
            line_dict["ground"] = self.ground.id
        if include_results:
            if self.with_shunt:
                vg = self._res_ground_potential_getter(warning=False)
                line_dict["results"]["ground_potential"] = [vg.real, vg.imag]
            line_dict["results"] = line_dict.pop("results")  # move results to the end
        return line_dict

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning, full)
        if self.with_shunt:
            vg = self._res_ground_potential_getter(warning=False)
            results["ground_potential"] = [vg.real, vg.imag]
        if full:
            # Add line specific results
            power_losses = self._res_power_losses_getter(warning=False)  # warn only once
            series_power_losses = self._res_series_power_losses_getter(warning=False)
            shunt_power_losses = (
                # add the shunt losses from both sides
                self._side1._res_shunt_losses_getter(warning=False)
                + self._side2._res_shunt_losses_getter(warning=False)
            )
            series_currents = self._res_series_currents_getter(warning=False)
            shunt_currents1 = self._side1._res_shunt_currents_getter(warning=False)
            shunt_currents2 = self._side2._res_shunt_currents_getter(warning=False)
            loading = self._res_loading_getter(warning=False)
            results["power_losses"] = [[s.real, s.imag] for s in power_losses.tolist()]
            results["series_currents"] = [[i.real, i.imag] for i in series_currents.tolist()]
            results["series_power_losses"] = [[s.real, s.imag] for s in series_power_losses.tolist()]
            results["shunt_currents1"] = [[i.real, i.imag] for i in shunt_currents1.tolist()]
            results["shunt_currents2"] = [[i.real, i.imag] for i in shunt_currents2.tolist()]
            results["shunt_power_losses"] = [[s.real, s.imag] for s in shunt_power_losses.tolist()]
            results["loading"] = None if loading is None else loading.tolist()
        return results


class LineSide(AbstractBranchSide):
    element_type = "line"
    allowed_phases = Line.allowed_phases  # type: ignore
    _branch: Line

    def _res_shunt_values_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        assert self._branch.with_shunt, "This method only works when there is a shunt"
        potentials = self._res_potentials_getter(warning)
        vg = self._branch._res_ground_potential_getter(warning=False)
        ig = self._branch._yg * vg
        shunt_currents = (self._branch._y_shunt @ potentials - ig) / 2
        return potentials, shunt_currents

    def _res_shunt_currents_getter(self, warning: bool) -> ComplexArray:
        if not self._branch.with_shunt:
            return np.zeros(self._n, dtype=np.complex128)
        return self._res_shunt_values_getter(warning)[1]

    def _res_shunt_losses_getter(self, warning: bool) -> ComplexArray:
        if not self._branch.with_shunt:
            return np.zeros(self._n, dtype=np.complex128)
        potentials, currents = self._res_shunt_values_getter(warning)
        return potentials * currents.conjugate()

    @property
    @ureg_wraps("A", (None,))
    def res_shunt_currents(self) -> Q_[ComplexArray]:
        """Get the currents in the shunt elements of the line side (in A)."""
        return self._res_shunt_currents_getter(warning=True)  # type: ignore

    @property
    @ureg_wraps("VA", (None,))
    def res_shunt_losses(self) -> Q_[ComplexArray]:
        """Get the losses in the shunt elements of the line side (in VA)."""
        return self._res_shunt_losses_getter(warning=True)  # type: ignore
