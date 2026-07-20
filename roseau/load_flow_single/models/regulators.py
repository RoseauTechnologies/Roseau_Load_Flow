import logging
from typing import Final, final

from shapely.geometry.base import BaseGeometry

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Float, Id, JsonDict, QtyOrMag, ResultState
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import warn_external
from roseau.load_flow_engine.cy_engine import CySingleVoltageRegulator  # noqa: F401
from roseau.load_flow_single.models.branches import AbstractBranch, AbstractBranchSide
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.regulator_parameters import RegulatorParameters

logger = logging.getLogger(__name__)


@final
class VoltageRegulator(AbstractBranch["RegulatorSide", "CySingleVoltageRegulator"]):
    """Voltage regulator with continuous smooth tap control.

    The model parameters are defined using the ``parameters`` argument.
    """

    element_type: Final = "regulator"

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        parameters: RegulatorParameters,
        u_ref: Float = 1.0,
        max_loading: Float = 1.0,
        geometry: BaseGeometry | None = None,
    ) -> None:
        """VoltageRegulator constructor.

        Args:
            id:
                A unique ID of the regulator in the network.

            bus1:
                Bus to connect to the source side.

            bus2:
                Bus to connect to the load side. The regulator will drive the voltage of this bus
                toward ``u_ref``.

            parameters:
                Parameters defining the electrical model of the regulator. Can be shared
                across multiple regulator instances.

            u_ref:
                Target voltage magnitude on the load side (p.u.). The regulator drives the load-side
                bus voltage toward this value. Defaults to 1.0.

            max_loading:
                Maximum loading of the regulator (p.u.). Defaults to 1.0.

            geometry:
                Geometry of the regulator element.
        """
        self._initialized = False
        self._res_tap: float | None = None
        super().__init__(id=id, bus1=bus1, bus2=bus2, n=2, geometry=geometry)
        self._side1 = RegulatorSide(branch=self, side=1, bus=bus1)
        self._side2 = RegulatorSide(branch=self, side=2, bus=bus2)
        self.u_ref = u_ref
        self.parameters = parameters
        self.max_loading = max_loading
        self._initialized = True

        self._cy_element = parameters._create_cy_element(u_ref=self._u_ref)
        self._cy_connect()
        self._connect(bus1, bus2)

    def _update_parameters(self) -> None:
        """Update the C++ model parameters after a change in u_ref, z2, or ym."""
        if self._cy_initialized:
            self._cy_element.update_parameters(
                self._parameters._z2,
                self._parameters._ym,
                self._u_ref * self._parameters._un / SQRT3,
            )

    @property
    def parameters(self) -> RegulatorParameters:
        """The parameters of the voltage regulator."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: RegulatorParameters) -> None:
        self._check_compatible_phase_tech(value)
        old_parameters = self._parameters if self._initialized else None
        self._update_network_parameters(old_parameters=old_parameters, new_parameters=value)
        self._invalidate_network_results()
        self._parameters = value
        self._update_parameters()

    @property
    def u_ref(self) -> Q_[float]:
        """Target voltage on the load side (p.u. of the nominal voltage ``un``)."""
        return Q_(self._u_ref, "")

    @u_ref.setter
    @ureg_wraps(None, (None, ""))
    def u_ref(self, value: QtyOrMag[Float]) -> None:
        if value <= 0:
            msg = f"u_ref must be positive: {value!r} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
        if value > 20:
            warn_external(
                f"Voltage regulator {self.id!r} got very high u_ref {value:.2f} p.u ({value:.2%}). "
                f"Did you mean {value / 100:.2f} p.u ({value:.2f}%) instead?",
            )
        self._u_ref = float(value)
        self._invalidate_network_results()
        self._update_parameters()

    @property
    def max_loading(self) -> Q_[float]:
        """Maximum loading of the regulator (unitless)."""
        return Q_(self._max_loading, "")

    @max_loading.setter
    @ureg_wraps(None, (None, ""))
    def max_loading(self, value: QtyOrMag[Float]) -> None:
        if value <= 0:
            msg = f"Maximum loading must be positive: {value} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE)
        if value > 20:
            warn_external(
                f"Voltage regulator {self.id!r} got very high max_loading {value:.2f} p.u "
                f"({value:.2%}). Did you mean {value / 100:.2f} p.u ({value:.2f}%) instead?",
            )
        self._max_loading = float(value)

    @property
    def sn(self) -> Q_[float]:
        """The nominal power of the regulator (in VA)."""
        # Do not add a setter. The user must know that if they change the nominal power, it changes
        # for all regulators that share the parameters. It is better to set it on the parameters.
        return self._parameters.sn

    @property
    def un(self) -> Q_[float]:
        """The nominal voltage of the regulator (in V)."""
        # Do not add a setter. The user must know that if they change the nominal voltage, it changes
        # for all regulators that share the parameters. It is better to set it on the parameters.
        return self._parameters.un

    @property
    def max_power(self) -> Q_[float]:
        """The maximum power loading of the regulator (in VA)."""
        return Q_(self._parameters._sn * self._max_loading, "VA")

    #
    # Results
    #
    def _refresh_results(self) -> None:
        super()._refresh_results()
        if self._fetch_results:
            self._res_tap = self._cy_element.get_tap()

    def _res_tap_getter(self, warning: bool) -> float:
        self._refresh_results()
        return self._res_getter(self._res_tap, warning)

    def _res_loading_getter(self, warning: bool) -> float:
        sn = self._parameters._sn
        power1 = self._side1._res_power_getter(warning)
        power2 = self._side2._res_power_getter(warning=False)  # warn only once
        return max(abs(power1), abs(power2)) / sn

    def _res_state_getter(self) -> ResultState:
        """Get the state of the regulator based on its loading."""
        loading = self._res_loading_getter(warning=False)
        max_loading = self._max_loading
        if loading > max_loading:
            return "very-high"
        elif loading > 0.75 * max_loading:
            return "high"
        else:
            return "normal"

    @property
    def res_tap(self) -> float:
        """The tap ratio applied by the regulator.

        A value of 1.05 means the regulator boosted the load-side voltage by 5%; 0.95 means a 5%
        buck. The tap is bounded to `(1 - u_range, 1 + u_range)`.
        """
        return self._res_tap_getter(warning=True)

    @property
    def res_losses(self) -> Q_[complex]:
        """Get the total complex losses in the regulator (in VA)."""
        power1 = self._side1._res_power_getter(warning=True)
        power2 = self._side2._res_power_getter(warning=False)  # warn only once
        return Q_(power1 + power2, "VA")

    @property
    def res_loading(self) -> Q_[float]:
        """Get the loading of the regulator (unitless)."""
        return Q_(self._res_loading_getter(warning=True), "")

    @property
    def res_violated(self) -> bool:
        """Whether the regulator power loading exceeds its maximal loading."""
        # True if either the source side or load side is overloaded
        loading = self._res_loading_getter(warning=True)
        return loading > self._max_loading

    #
    # Json Mixin interface
    #
    @classmethod
    def _from_dict(cls, data: JsonDict, *, include_results: bool = True) -> "VoltageRegulator":
        results = data.get("results")  # peek before super() pops it
        self = super()._from_dict(data, include_results=include_results)
        if include_results and results and "tap" in results:
            self._res_tap = results["tap"]
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results)
        data["params_id"] = self.parameters.id
        data["max_loading"] = self._max_loading
        data["u_ref"] = self._u_ref
        if include_results:
            data["results"]["tap"] = self._res_tap_getter(warning=False)  # warn only once
            data["results"] = data.pop("results")  # move results to the end
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning, full)
        results["tap"] = self._res_tap_getter(warning=False)  # warn only once
        if full:
            # Add transformer specific results
            power1 = self._side1._res_power_getter(warning=False)
            power2 = self._side2._res_power_getter(warning=False)
            losses = power1 + power2
            loading = max(abs(power1), abs(power2)) / self.parameters._sn
            results["power_losses"] = [losses.real, losses.imag]
            results["loading"] = loading
        return results


@final
class RegulatorSide(AbstractBranchSide):
    element_type = "regulator"
    _branch: VoltageRegulator
