import logging
from typing import Final

import numpy as np
import shapely

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Float, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyShuntLine, CySimplifiedLine
from roseau.load_flow_single.models.branches import AbstractBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.line_parameters import LineParameters

logger = logging.getLogger(__name__)


class Line(AbstractBranch[CyShuntLine | CySimplifiedLine]):
    """An electrical line PI model with series impedance and optional shunt admittance."""

    element_type: Final = "line"

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        parameters: LineParameters,
        length: Float | Q_[Float],
        max_loading: Float | Q_[Float] = 1.0,
        geometry: shapely.Geometry | None = None,
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

            max_loading:
                The maximum loading of the line (unitless). It is not used in the load flow. It is
                used with ``parameters.ampacity`` to compute the maximum allowed current of the line
                and to determine if the line is overloaded.

            geometry:
                The geometry of the line i.e. the linestring.
        """
        self._initialized = False
        self._with_shunt = parameters.with_shunt
        super().__init__(id=id, bus1=bus1, bus2=bus2, n=1, geometry=geometry)
        self.length = length
        self.parameters = parameters
        self.max_loading = max_loading
        self._initialized = True
        self._check_same_voltage_level()

        # Cache values used in results calculations
        self._z_line = parameters._z_line * self._length
        self._y_shunt = parameters._y_shunt * self._length
        self._z_line_inv = 1.0 / self._z_line

        if parameters.with_shunt:
            self._cy_element = CyShuntLine(
                n=1,
                y_shunt=np.array([self._y_shunt], dtype=np.complex128),
                z_line=np.array([self._z_line], dtype=np.complex128),
            )
        else:
            self._cy_element = CySimplifiedLine(n=1, z_line=np.array([self._z_line], dtype=np.complex128))
        self._cy_connect()

    def _update_internal_parameters(self) -> None:
        """Update the internal parameters of the line."""
        self._z_line = self._parameters._z_line * self._length
        self._y_shunt = self._parameters._y_shunt * self._length
        self._z_line_inv = 1.0 / self._z_line
        if self._cy_element is not None:
            if self._parameters.with_shunt:
                assert isinstance(self._cy_element, CyShuntLine)
                self._cy_element.update_line_parameters(
                    y_shunt=np.array([self._y_shunt], dtype=np.complex128),
                    z_line=np.array([self._z_line], dtype=np.complex128),
                )
            else:
                assert isinstance(self._cy_element, CySimplifiedLine)
                self._cy_element.update_line_parameters(z_line=np.array([self._z_line], dtype=np.complex128))

    @property
    @ureg_wraps("km", (None,))
    def length(self) -> Q_[float]:
        """The length of the line (in km)."""
        return self._length

    @length.setter
    @ureg_wraps(None, (None, "km"))
    def length(self, value: Float | Q_[Float]) -> None:
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
        if value.with_shunt:
            if self._initialized and not self.with_shunt:
                msg = "Cannot set line parameters with a shunt to a line that does not have shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
        else:
            if self._initialized and self.with_shunt:
                msg = "Cannot set line parameters without a shunt to a line that has shunt components."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
        self._invalidate_network_results()
        self._parameters = value
        if self._initialized:
            self._update_internal_parameters()

    @property
    @ureg_wraps("ohm", (None,))
    def z_line(self) -> Q_[complex]:
        """Impedance of the line (in Ohm)."""
        return self._z_line

    @property
    @ureg_wraps("S", (None,))
    def y_shunt(self) -> Q_[complex]:
        """Shunt admittance of the line (in Siemens)."""
        return self._y_shunt

    @property
    @ureg_wraps("", (None,))
    def max_loading(self) -> Q_[float]:
        """The maximum loading of the line (unitless)"""
        return self._max_loading

    @max_loading.setter
    @ureg_wraps(None, (None, ""))
    def max_loading(self, value: Float | Q_[Float]) -> None:
        if value <= 0:
            msg = f"Maximum loading must be positive: {value} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE)
        self._max_loading = float(value)

    @property
    def ampacity(self) -> Q_[float] | None:
        """The ampacity of the line (in A)."""
        # Do not add a setter. The user must know that if they change the ampacity, it changes
        # for all lines that share the parameters. It is better to set it on the parameters.
        return self._parameters.ampacity

    @property
    def max_current(self) -> Q_[float] | None:
        """The maximum current of the line (in A). It takes into account the `max_loading` of the line and the
        `ampacity` of the parameters."""
        # Do not add a setter. Only `max_loading` can be altered by the user
        amp = self._parameters._ampacity
        return None if amp is None else Q_(amp * self._max_loading, "A")

    @property
    def with_shunt(self) -> bool:
        return self._with_shunt

    def _res_series_values_getter(self, warning: bool) -> tuple[complex, complex]:
        volt1, volt2 = self._res_voltages_getter(warning)  # V
        du_line = volt1 - volt2
        i_line = self._z_line_inv * du_line / SQRT3  # Zₗ x Iₗ = ΔU -> I = Zₗ⁻¹ x ΔU
        return du_line, i_line

    def _res_series_current_getter(self, warning: bool) -> complex:
        _, i_line = self._res_series_values_getter(warning)
        return i_line

    def _res_series_power_losses_getter(self, warning: bool) -> complex:
        du_line, i_line = self._res_series_values_getter(warning)
        return du_line * i_line.conjugate() * SQRT3  # Sₗ = √3.ΔU.Iₗ*

    def _res_shunt_values_getter(self, warning: bool) -> tuple[complex, complex, complex, complex]:
        assert self.with_shunt, "This method only works when there is a shunt"
        volt1, volt2 = self._res_voltages_getter(warning)
        i1_shunt = self._y_shunt * volt1 / SQRT3 / 2
        i2_shunt = self._y_shunt * volt2 / SQRT3 / 2
        return volt1, volt2, i1_shunt, i2_shunt

    def _res_shunt_currents_getter(self, warning: bool) -> tuple[complex, complex]:
        if not self.with_shunt:
            return 0j, 0j
        _, _, cur1, cur2 = self._res_shunt_values_getter(warning)
        return cur1, cur2

    def _res_shunt_power_losses_getter(self, warning: bool) -> complex:
        if not self.with_shunt:
            return 0j
        volt1, volt2, cur1, cur2 = self._res_shunt_values_getter(warning)
        return (volt1 * cur1.conjugate() + volt2 * cur2.conjugate()) * SQRT3

    def _res_power_losses_getter(self, warning: bool) -> complex:
        series_losses = self._res_series_power_losses_getter(warning)
        shunt_losses = self._res_shunt_power_losses_getter(warning=False)  # we warn on the previous line
        return series_losses + shunt_losses

    def _res_loading_getter(self, warning: bool) -> float | None:
        if (amp := self._parameters._ampacity) is None:
            return None
        current1, current2 = self._res_currents_getter(warning=warning)
        return max(abs(current1), abs(current2)) / amp

    @property
    @ureg_wraps("A", (None,))
    def res_series_current(self) -> Q_[complex]:
        """Get the current in the series elements of the line (in A)."""
        return self._res_series_current_getter(warning=True)

    @property
    @ureg_wraps("VA", (None,))
    def res_series_power_losses(self) -> Q_[complex]:
        """Get the power losses in the series elements of the line (in VA)."""
        return self._res_series_power_losses_getter(warning=True)

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_shunt_currents(self) -> tuple[Q_[complex], Q_[complex]]:
        """Get the currents in the shunt elements of the line (in A)."""
        cur1, cur2 = self._res_shunt_currents_getter(warning=True)
        return cur1, cur2

    @property
    @ureg_wraps("VA", (None,))
    def res_shunt_power_losses(self) -> Q_[complex]:
        """Get the power losses in the shunt elements of the line (in VA)."""
        return self._res_shunt_power_losses_getter(warning=True)

    @property
    @ureg_wraps("VA", (None,))
    def res_power_losses(self) -> Q_[complex]:
        """Get the power losses in the line (in VA)."""
        return self._res_power_losses_getter(warning=True)

    @property
    def res_loading(self) -> Q_[float] | None:
        """The loading of the line (unitless) if ``self.parameters.ampacity`` is set, else ``None``."""
        if (loading := self._res_loading_getter(warning=True)) is None:
            return None
        return Q_(loading, "")

    @property
    def res_violated(self) -> bool | None:
        """Whether the line current loading exceeds its maximal loading.

        Returns ``None`` if the ``self.parameters.ampacity`` is not set.
        """
        if (loading := self._res_loading_getter(warning=True)) is None:
            return None
        return bool(loading > self._max_loading)

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results)
        data["max_loading"] = self._max_loading
        data["params_id"] = self._parameters.id
        data["length"] = self._length
        if include_results:
            data["results"] = data.pop("results")  # move results to the end
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning, full)
        if full:
            # Add line specific results
            power_losses = self._res_power_losses_getter(warning=False)  # warn only once
            series_power_losses = self._res_series_power_losses_getter(warning=False)
            shunt_power_losses = self._res_shunt_power_losses_getter(warning=False)
            series_current = self._res_series_current_getter(warning=False)
            shunt_current1, shunt_current2 = self._res_shunt_currents_getter(warning=False)
            loading = self._res_loading_getter(warning=False)
            results["power_losses"] = [power_losses.real, power_losses.imag]
            results["series_power_losses"] = [series_power_losses.real, series_power_losses.imag]
            results["shunt_power_losses"] = [shunt_power_losses.real, shunt_power_losses.imag]
            results["series_current"] = [series_current.real, series_current.imag]
            results["shunt_current1"] = [shunt_current1.real, shunt_current1.imag]
            results["shunt_current2"] = [shunt_current2.real, shunt_current2.imag]
            results["loading"] = loading
        return results
