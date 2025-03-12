import logging
from typing import Final

from shapely.geometry.base import BaseGeometry

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Float, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import deprecate_renamed_parameters
from roseau.load_flow_engine.cy_engine import CySingleTransformer
from roseau.load_flow_single.models.branches import AbstractBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.transformer_parameters import TransformerParameters

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch[CySingleTransformer]):
    """A generic transformer model.

    The model parameters are defined using the ``parameters`` argument.
    """

    element_type: Final = "transformer"

    @deprecate_renamed_parameters({"bus1": "bus_hv", "bus2": "bus_lv"}, version="0.12.0", category=DeprecationWarning)
    def __init__(
        self,
        id: Id,
        bus_hv: Bus,
        bus_lv: Bus,
        *,
        parameters: TransformerParameters,
        tap: Float = 1.0,
        max_loading: Float | Q_[Float] = 1.0,
        geometry: BaseGeometry | None = None,
    ) -> None:
        """Transformer constructor.

        Args:
            id:
                A unique ID of the transformer in the network transformers.

            bus_hv:
                Bus to connect the HV side of the transformer to.

            bus_lv:
                Bus to connect the LV side of the transformer to.

            parameters:
                Parameters defining the electrical model of the transformer. This is an instance of
                the :class:`TransformerParameters` class and can be used by multiple transformers.

            tap:
                The tap of the transformer. For example, `1.0` means the tap is at the neutral
                position, `1.025` means a `+2.5%` tap, and `0.975` means a `-2.5%` tap. The value
                must be between 0.9 and 1.1.

            max_loading:
                The maximum loading of the transformer (unitless). It is used with ``parameters.sn``
                to compute the maximum allowed power of the transformer and to determine if the
                transformer is overloaded.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(id=id, bus1=bus_hv, bus2=bus_lv, n=2, geometry=geometry)

        self.tap = tap
        self._parameters = parameters
        self.max_loading = max_loading

        # Equivalent direct-system (positive-sequence) parameters
        z2, ym, k = parameters.z2d, parameters.ymd, parameters.kd

        self._cy_element = CySingleTransformer(z2=z2, ym=ym, k=k * self._tap)
        self._cy_connect()
        self._connect(bus_hv, bus_lv)

    @property
    def bus_hv(self) -> Bus:
        """The bus on the high voltage side of the transformer."""
        return self._bus1

    @property
    def bus_lv(self) -> Bus:
        """The bus on the low voltage side of the transformer."""
        return self._bus2

    @property
    def tap(self) -> float:
        """The tap of the transformer, for example 1.02."""
        return self._tap

    @tap.setter
    def tap(self, value: Float) -> None:
        if value > 1.1:
            logger.warning(f"The provided tap {value:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if value < 0.9:
            logger.warning(f"The provided tap {value:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")
        self._tap = float(value)
        self._invalidate_network_results()
        if self._cy_element is not None:
            z2, ym, k = self.parameters.z2d, self.parameters.ymd, self.parameters.kd
            self._cy_element.update_transformer_parameters(z2, ym, k * self._tap)

    @property
    def parameters(self) -> TransformerParameters:
        """The parameters of the transformer."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: TransformerParameters) -> None:
        # Note here we allow changing the vector group as the model is the same
        if value.type != "three-phase":
            msg = f"{value.type.capitalize()} transformers are not allowed in a balanced three-phase load flow."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE)
        self._parameters = value
        self._invalidate_network_results()
        if self._cy_element is not None:
            z2, ym, k = value.z2d, value.ymd, value.kd
            self._cy_element.update_transformer_parameters(z2, ym, k * self.tap)

    @property
    @ureg_wraps("", (None,))
    def max_loading(self) -> Q_[float]:
        """The maximum loading of the transformer (unitless)"""
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
    def sn(self) -> Q_[float]:
        """The nominal power of the transformer (VA)."""
        # Do not add a setter. The user must know that if they change the nominal power, it changes
        # for all transformers that share the parameters. It is better to set it on the parameters.
        return self._parameters.sn

    @property
    @ureg_wraps("VA", (None,))
    def max_power(self) -> Q_[float]:
        """The maximum power loading of the transformer (in VA)."""
        return self.parameters._sn * self._max_loading  # type: ignore

    @property
    @ureg_wraps("VA", (None,))
    def res_power_losses(self) -> Q_[complex]:
        """Get the total power losses in the transformer (in VA)."""
        power1, power2 = self._res_powers_getter(warning=True)
        return power1 + power2

    def _res_loading_getter(self, warning: bool) -> float:
        sn = self._parameters._sn
        power1, power2 = self._res_powers_getter(warning=warning)
        return max(abs(power1), abs(power2)) / sn

    @property
    @ureg_wraps("", (None,))
    def res_loading(self) -> Q_[float]:
        """Get the loading of the transformer (unitless)."""
        return self._res_loading_getter(warning=True)

    @property
    def res_violated(self) -> bool:
        """Whether the transformer power loading exceeds its maximal loading."""
        # True if either the primary or secondary is overloaded
        loading = self._res_loading_getter(warning=True)
        return bool(loading > self._max_loading)

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results)
        data["max_loading"] = self._max_loading
        data["params_id"] = self.parameters.id
        data["tap"] = self.tap
        if include_results:
            data["results"] = data.pop("results")  # move results to the end
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning, full)
        if full:
            # Add transformer specific results
            power_hv, power_lv = self._res_powers_getter(warning=False)  # warn only once
            power_losses = power_hv + power_lv
            loading = max(abs(power_hv), abs(power_lv)) / self.parameters._sn
            results["power_losses"] = [power_losses.real, power_losses.imag]
            results["loading"] = loading
        return results
