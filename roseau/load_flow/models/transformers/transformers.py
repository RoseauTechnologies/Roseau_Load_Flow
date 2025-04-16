import logging
import warnings
from functools import cached_property
from typing import Final

from shapely.geometry.base import BaseGeometry

from roseau.load_flow.converters import _calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.transformers.parameters import TransformerParameters
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import deprecate_renamed_parameters, find_stack_level
from roseau.load_flow_engine.cy_engine import CyTransformer

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch[CyTransformer]):
    """A generic transformer model.

    The model parameters are defined using the ``parameters`` argument.
    """

    element_type: Final = "transformer"
    allowed_phases: Final = Bus.allowed_phases
    """The allowed phases for a transformer are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"`` (three-phase transformer)
    - P-P or P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"an"``, ``"bn"``, ``"cn"`` (single-phase
      transformer or HV side of center-tapped transformer)
    - P-P-N: ``"abn"``, ``"bcn"``, ``"can"`` (LV side of center-tapped transformer)
    """
    _allowed_phases_three = frozenset({"abc", "abcn"})
    _allowed_phases_single = frozenset({"ab", "bc", "ca", "an", "bn", "cn"})
    _allowed_phases_center_lv_side = frozenset({"abn", "bcn", "can"})

    @deprecate_renamed_parameters(
        {"bus1": "bus_hv", "bus2": "bus_lv", "phases1": "phases_hv", "phases2": "phases_lv"},
        version="0.12.0",
        category=DeprecationWarning,
    )
    def __init__(
        self,
        id: Id,
        bus_hv: Bus,
        bus_lv: Bus,
        *,
        parameters: TransformerParameters,
        tap: float = 1.0,
        phases_hv: str | None = None,
        phases_lv: str | None = None,
        connect_neutral_hv: bool | None = None,
        connect_neutral_lv: bool | None = None,
        max_loading: float | Q_[float] = 1,
        geometry: BaseGeometry | None = None,
    ) -> None:
        """Transformer constructor.

        Args:
            id:
                A unique ID of the transformer in the network transformers.

            bus_hv:
                Bus to connect the HV side of the transformer.

            bus_lv:
                Bus to connect the LV side of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            parameters:
                Parameters defining the electrical model of the transformer. This is an instance of
                the :class:`TransformerParameters` class and can be used by multiple transformers.

            phases_hv:
                The phases of the HV side of the transformer. A string like ``"abc"`` or ``"abcn"``
                etc. The order of the phases is important. For a full list of supported phases, see
                the class attribute :attr:`allowed_phases`. All phases must be present in the
                connected bus. By default, determined from the transformer type.

            phases_lv:
                The phases of the LV side of the transformer. Similar to ``phases_hv``.

            connect_neutral_hv:
                Specifies whether the element's neutral on the HV side should be connected to the HV
                bus's neutral or left floating. By default, the elements's neutral is connected when
                the bus has a neutral. If the bus does not have a neutral, the element's neutral is
                left floating by default. To override the default behavior, pass an explicit ``True``
                or ``False``.

            connect_neutral_lv:
                Similar to ``connect_neutral_hv`` but for the LV side.

            max_loading:
                The maximum loading of the transformer (unitless). It is used with the `sn` of the
                :class:`TransformerParameters` to compute the :meth:`~roseau.load_flow.Transformer.max_power`,
                :meth:`~roseau.load_flow.Transformer.res_loading` and
                :meth:`~roseau.load_flow.Transformer.res_violated` of the transformer.

            geometry:
                The geometry of the transformer.
        """
        self._initialized = False
        if parameters.type == "single-phase":
            compute_phases = self._compute_phases_single
        elif parameters.type == "center-tapped":
            compute_phases = self._compute_phases_center
        else:
            compute_phases = self._compute_phases_three
        phases_hv, phases_lv, connect_neutral_hv, connect_neutral_lv = compute_phases(
            id=id,
            bus_hv=bus_hv,
            bus_lv=bus_lv,
            parameters=parameters,
            phases_hv=phases_hv,
            phases_lv=phases_lv,
            connect_neutral_hv=connect_neutral_hv,
            connect_neutral_lv=connect_neutral_lv,
        )

        super().__init__(id=id, bus1=bus_hv, bus2=bus_lv, phases1=phases_hv, phases2=phases_lv, geometry=geometry)
        self._connect_neutral_hv = connect_neutral_hv
        self._connect_neutral_lv = connect_neutral_lv
        self.tap = tap
        self.parameters = parameters
        self.max_loading = max_loading
        self._initialized = True

        if parameters.type == "three-phase":
            self._cy_element = parameters._create_cy_transformer(tap=tap)
        else:
            self._cy_element = parameters._create_cy_transformer(tap=parameters.orientation * tap)
        self._cy_connect()
        self._connect(bus_hv, bus_lv)

    def __repr__(self) -> str:
        return f"{super().__repr__()[:-1]}, tap={self.tap:f}, max_loading={self._max_loading:f}>"

    @property
    def bus_hv(self) -> Bus:
        """The bus on the high voltage side of the transformer."""
        return self._bus1

    @property
    def bus_lv(self) -> Bus:
        """The bus on the low voltage side of the transformer."""
        return self._bus2

    @property
    def phases_hv(self) -> str:
        """The phases of the high voltage side of the transformer."""
        return self._phases1

    @property
    def phases_lv(self) -> str:
        """The phases of the low voltage side of the transformer."""
        return self._phases2

    @cached_property
    def has_floating_neutral_hv(self) -> bool:
        """Does this transformer have a floating neutral on the HV side?"""
        return self.bus_hv._is_element_neutral_floating(self.phases_hv, self._connect_neutral_hv)

    @cached_property
    def has_floating_neutral_lv(self) -> bool:
        """Does this transformer have a floating neutral on the LV side?"""
        return self.bus_lv._is_element_neutral_floating(self.phases_lv, self._connect_neutral_lv)

    @property
    def tap(self) -> float:
        """The tap of the transformer, for example 1.02."""
        return self._tap

    @tap.setter
    def tap(self, value: float) -> None:
        if value > 1.1:
            logger.warning(f"The provided tap {value:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if value < 0.9:
            logger.warning(f"The provided tap {value:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")
        self._tap = value
        self._invalidate_network_results()
        if self._cy_element is not None:
            z2, ym, k = self.parameters._z2, self.parameters._ym, self.parameters._k
            self._cy_element.update_transformer_parameters(z2, ym, k * value)

    @property
    def parameters(self) -> TransformerParameters:
        """The parameters of the transformer."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: TransformerParameters) -> None:
        old_parameters = self._parameters if self._initialized else None
        if old_parameters is not None and old_parameters.vg != value.vg:
            msg = (
                f"Cannot update the parameters of transformer {self.id!r} to a different vector "
                f"group: old={old_parameters.vg!r}, new={value.vg!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE)
        self._update_network_parameters(old_parameters=old_parameters, new_parameters=value)
        self._invalidate_network_results()
        self._parameters = value
        if self._cy_element is not None:
            z2, ym, k = value._z2, value._ym, value._k
            if value.type in ("single-phase", "center-tapped"):
                k *= value.orientation
            self._cy_element.update_transformer_parameters(z2, ym, k * self.tap)

    @property
    @ureg_wraps("", (None,))
    def max_loading(self) -> Q_[float]:
        """The maximum loading of the transformer (unitless)"""
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

    def _compute_phases_three(
        self,
        id: Id,
        bus_hv: Bus,
        bus_lv: Bus,
        parameters: TransformerParameters,
        phases_hv: str | None,
        phases_lv: str | None,
        connect_neutral_hv: bool | None,
        connect_neutral_lv: bool | None,
    ) -> tuple[str, str, bool | None, bool | None]:
        whv = parameters.whv
        wlv = parameters.wlv
        clock = parameters.clock

        w1_has_neutral = whv.endswith("N")
        if phases_hv is None:
            phases_hv = "abcn" if w1_has_neutral else "abc"
            phases_hv = "".join(p for p in bus_hv.phases if p in phases_hv)
            self._check_phases(id=id, allowed_phases=self._allowed_phases_three, phases_hv=phases_hv)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_three, phases_hv=phases_hv)
            if "n" in phases_hv and not w1_has_neutral:
                if whv.startswith(("Y", "Z")):
                    correct_vg = f"{whv}N{wlv}{clock}"
                    warnings.warn(
                        f"Transformer {id!r} with vector group '{parameters.vg}' does not have a "
                        f"brought out neutral on the HV side. The neutral phase 'n' is ignored. If "
                        f"you meant to use a brought out neutral, use vector group '{correct_vg}'. "
                        f"This will raise an error in the future.",
                        FutureWarning,
                        stacklevel=find_stack_level(),
                    )
                    phases_hv = phases_hv.replace("n", "")
                else:
                    msg = f"HV phases {phases_hv!r} of transformer {id!r} are not compatible with its winding {whv!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
            connect_neutral_hv = bus_hv._check_element_phases(
                self, eid=id, phases=phases_hv, side="HV", connect_neutral=connect_neutral_hv
            )

        w2_has_neutral = wlv.endswith("n")
        if phases_lv is None:
            phases_lv = "abcn" if w2_has_neutral else "abc"
            phases_lv = "".join(p for p in bus_lv.phases if p in phases_lv)
            self._check_phases(id=id, allowed_phases=self._allowed_phases_three, phases_lv=phases_lv)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_three, phases_lv=phases_lv)
            if "n" in phases_lv and not w2_has_neutral:
                if wlv.startswith(("y", "z")):
                    correct_vg = f"{whv}{wlv}n{clock}"
                    warnings.warn(
                        f"Transformer {id!r} with vector group '{parameters.vg}' does not have a "
                        f"brought out neutral on the LV side. The neutral phase 'n' is ignored. If "
                        f"you meant to use a brought out neutral, use vector group '{correct_vg}'. "
                        f"This will raise an error in the future.",
                        FutureWarning,
                        stacklevel=find_stack_level(),
                    )
                    phases_lv = phases_lv.replace("n", "")
                else:
                    msg = f"LV phases {phases_lv!r} of transformer {id!r} are not compatible with its winding {wlv!r}."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
            connect_neutral_lv = bus_lv._check_element_phases(
                self, eid=id, phases=phases_lv, side="LV", connect_neutral=connect_neutral_lv
            )

        return phases_hv, phases_lv, connect_neutral_hv, connect_neutral_lv

    def _compute_phases_single(
        self,
        id: Id,
        bus_hv: Bus,
        bus_lv: Bus,
        parameters: TransformerParameters,
        phases_hv: str | None,
        phases_lv: str | None,
        connect_neutral_hv: bool | None,
        connect_neutral_lv: bool | None,
    ) -> tuple[str, str, bool | None, bool | None]:
        if phases_hv is None:
            phases_hv = "".join(
                p for p in bus_hv.phases if p in bus_lv.phases
            )  # can't use set because order is important
            phases_hv = phases_hv.replace("ac", "ca")
            if phases_hv not in self._allowed_phases_single:
                msg = f"HV phases of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_single, phases_hv=phases_hv)
            connect_neutral_hv = bus_hv._check_element_phases(
                self, eid=id, phases=phases_hv, side="HV", connect_neutral=connect_neutral_hv
            )
        if phases_lv is None:
            phases_lv = "".join(
                p for p in bus_hv.phases if p in bus_lv.phases
            )  # can't use set because order is important
            phases_lv = phases_lv.replace("ac", "ca")
            if phases_lv not in self._allowed_phases_single:
                msg = f"LV phases of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_single, phases_lv=phases_lv)
            connect_neutral_lv = bus_lv._check_element_phases(
                self, eid=id, phases=phases_lv, side="LV", connect_neutral=connect_neutral_lv
            )

        return phases_hv, phases_lv, connect_neutral_hv, connect_neutral_lv

    def _compute_phases_center(
        self,
        id: Id,
        bus_hv: Bus,
        bus_lv: Bus,
        parameters: TransformerParameters,
        phases_hv: str | None,
        phases_lv: str | None,
        connect_neutral_hv: bool | None,
        connect_neutral_lv: bool | None,
    ) -> tuple[str, str, bool | None, bool | None]:
        if phases_hv is None:
            phases_hv = "".join(p for p in bus_lv.phases if p in bus_hv.phases and p != "n")
            phases_hv = phases_hv.replace("ac", "ca")
            if phases_hv not in self._allowed_phases_single:
                msg = f"HV phases of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_single, phases_hv=phases_hv)
            connect_neutral_hv = bus_hv._check_element_phases(
                self, eid=id, phases=phases_hv, side="HV", connect_neutral=connect_neutral_hv
            )

        if phases_lv is None:
            phases_lv = "".join(p for p in bus_lv.phases if p in bus_hv.phases or p == "n")
            if phases_lv not in self._allowed_phases_center_lv_side:
                msg = f"LV phases of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_center_lv_side, phases_lv=phases_lv)
            connect_neutral_lv = bus_lv._check_element_phases(
                self, eid=id, phases=phases_lv, side="LV", connect_neutral=connect_neutral_lv
            )

        return phases_hv, phases_lv, connect_neutral_hv, connect_neutral_lv

    def _cy_connect(self) -> None:
        """Connect the Cython elements of the buses and the transformer."""
        connections = []
        bus_hv_phases = self.bus_hv.phases.removesuffix("n") if self.has_floating_neutral_hv else self.bus_hv.phases
        for i, phase in enumerate(self.phases1):
            if phase in bus_hv_phases:
                j = bus_hv_phases.index(phase)
                connections.append((i, j))
        self._cy_element.connect(self.bus_hv._cy_element, connections, True)

        connections = []
        bus_lv_phases = self.bus_lv.phases.removesuffix("n") if self.has_floating_neutral_lv else self.bus_lv.phases
        for i, phase in enumerate(self.phases2):
            if phase in bus_lv_phases:
                j = bus_lv_phases.index(phase)
                connections.append((i, j))
        self._cy_element.connect(self.bus_lv._cy_element, connections, False)

    #
    # Results
    #
    def _res_loading_getter(self, warning: bool) -> float:
        powers_hv, powers_lv = self._res_powers_getter(warning)
        return max(abs(powers_hv.sum()), abs(powers_lv.sum())) / self._parameters._sn

    @property
    @ureg_wraps("", (None,))
    def res_loading(self) -> Q_[float]:
        """Get the loading of the transformer (unitless)."""
        return self._res_loading_getter(warning=True)

    @property
    @ureg_wraps("VA", (None,))
    def res_power_losses(self) -> Q_[complex]:
        """Get the total power losses in the transformer (in VA)."""
        powers_hv, powers_lv = self._res_powers_getter(warning=True)
        return sum(powers_hv) + sum(powers_lv)

    @property
    def res_violated(self) -> bool:
        """Whether the transformer power loading exceeds its maximal loading."""
        # True if either the HV or LV side is overloaded
        loading = self._res_loading_getter(warning=True)
        return bool(loading > self._max_loading)

    @property
    @ureg_wraps("V", (None,))
    def res_voltages_hv(self) -> Q_[ComplexArray]:
        """The load flow result of the transformer voltages on the HV side (V)."""
        potentials_hv = self._res_potentials_getter(warning=True)[0]
        return _calculate_voltages(potentials=potentials_hv, phases=self.phases_hv)

    @property
    @ureg_wraps("V", (None,))
    def res_voltages_lv(self) -> Q_[ComplexArray]:
        """The load flow result of the transformer voltages on the LV side (V)."""
        potentials_lv = self._res_potentials_getter(warning=True)[1]
        return _calculate_voltages(potentials=potentials_lv, phases=self.phases_lv)

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results)
        data["connect_neutral_hv"] = self._connect_neutral_hv
        data["connect_neutral_lv"] = self._connect_neutral_lv
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
            powers_hv, powers_lv = self._res_powers_getter(warning=False)  # warn only once
            sum_powers_hv, sum_powers_lv = sum(powers_hv), sum(powers_lv)
            power_losses = sum_powers_hv + sum_powers_lv
            loading = max(abs(sum_powers_hv), abs(sum_powers_lv)) / self.parameters._sn
            results["power_losses"] = [power_losses.real, power_losses.imag]
            results["loading"] = loading
        return results
