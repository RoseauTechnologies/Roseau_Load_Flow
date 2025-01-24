import logging
import warnings
from typing import Final

from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.transformers.parameters import TransformerParameters
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import deprecate_renamed_parameters, find_stack_level
from roseau.load_flow_engine.cy_engine import (
    CyCenterTransformer,
    CySingleTransformer,
    CyThreePhaseTransformer,
    CyTransformer,
)

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch):
    """A generic transformer model.

    The model parameters are defined using the ``parameters`` argument.
    """

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
        max_loading: float | Q_[float] = 1,
        geometry: BaseGeometry | None = None,
    ) -> None:
        """Transformer constructor.

        Args:
            id:
                A unique ID of the transformer in the network branches.

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

            max_loading:
                The maximum loading of the transformer (unitless). It is used with the `sn` of the
                :class:`TransformerParameters` to compute the :meth:`~roseau.load_flow.Transformer.max_power`,
                :meth:`~roseau.load_flow.Transformer.res_loading` and
                :meth:`~roseau.load_flow.Transformer.res_violated` of the transformer.

            geometry:
                The geometry of the transformer.
        """
        if parameters.type == "single-phase":
            phases_hv, phases_lv = self._compute_phases_single(
                id=id, bus_hv=bus_hv, bus_lv=bus_lv, phases_hv=phases_hv, phases_lv=phases_lv
            )
        elif parameters.type == "center-tapped":
            phases_hv, phases_lv = self._compute_phases_center(
                id=id, bus_hv=bus_hv, bus_lv=bus_lv, phases_hv=phases_hv, phases_lv=phases_lv
            )
        else:
            phases_hv, phases_lv = self._compute_phases_three(
                id=id, bus_hv=bus_hv, bus_lv=bus_lv, parameters=parameters, phases_hv=phases_hv, phases_lv=phases_lv
            )

        super().__init__(id=id, bus1=bus_hv, bus2=bus_lv, phases1=phases_hv, phases2=phases_lv, geometry=geometry)
        self.tap = tap
        self._parameters = parameters
        self.max_loading = max_loading

        z2, ym, k = parameters._z2, parameters._ym, parameters._k
        clock, orientation = parameters.clock, parameters.orientation
        self._cy_element: CyTransformer
        if parameters.type == "single-phase":
            self._cy_element = CySingleTransformer(z2=z2, ym=ym, k=k * orientation * tap)
        elif parameters.type == "center-tapped":
            self._cy_element = CyCenterTransformer(z2=z2, ym=ym, k=k * orientation * tap)
        else:
            self._cy_element = CyThreePhaseTransformer(
                n1=parameters._n1,
                n2=parameters._n2,
                whv=parameters.whv[0],
                wlv=parameters.wlv[0],
                z2=z2,
                ym=ym,
                k=k * tap,
                clock=clock,
            )
        self._cy_connect()

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}: id={self.id!r}, bus1={self.bus1.id!r}, bus2={self.bus2.id!r}, "
            f"phases_hv={self.phases_hv!r}, phases_lv={self.phases_lv!r}, tap={self.tap:f}, "
            f"max_loading={self._max_loading:f}>"
        )

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
        vg1 = self._parameters.vg
        vg2 = value.vg
        if vg1 != vg2:
            msg = (
                f"Cannot update the parameters of transformer {self.id!r} to a different vector "
                f"group: old={vg1!r}, new={vg2!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE)
        self._parameters = value
        self._invalidate_network_results()
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
        self._max_loading: float = value

    @property
    def sn(self) -> Q_[float]:
        """The nominal power of the transformer (VA)."""
        # Do not add a setter. The user must know that if they change the nominal power, it changes
        # for all transformers that share the parameters. It is better to set it on the parameters.
        return self._parameters.sn

    @property
    def max_power(self) -> Q_[float] | None:
        """The maximum power loading of the transformer (in VA)."""
        sn = self.parameters._sn
        return None if sn is None else Q_(sn * self._max_loading, "VA")

    def _compute_phases_three(
        self,
        id: Id,
        bus_hv: Bus,
        bus_lv: Bus,
        parameters: TransformerParameters,
        phases_hv: str | None,
        phases_lv: str | None,
    ) -> tuple[str, str]:
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
            self._check_bus_phases(id=id, bus=bus_hv, phases_hv=phases_hv)
            transformer_phases = "abcn" if w1_has_neutral else "abc"
            phases_not_in_transformer = set(phases_hv) - set(transformer_phases)
            if phases_not_in_transformer:
                if phases_not_in_transformer == {"n"} and whv.startswith(("Y", "Z")):
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

        w2_has_neutral = wlv.endswith("n")
        if phases_lv is None:
            phases_lv = "abcn" if w2_has_neutral else "abc"
            phases_lv = "".join(p for p in bus_lv.phases if p in phases_lv)
            self._check_phases(id=id, allowed_phases=self._allowed_phases_three, phases_lv=phases_lv)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_three, phases_lv=phases_lv)
            self._check_bus_phases(id=id, bus=bus_lv, phases_lv=phases_lv)
            transformer_phases = "abcn" if w2_has_neutral else "abc"
            phases_not_in_transformer = set(phases_lv) - set(transformer_phases)
            if phases_not_in_transformer:
                if phases_not_in_transformer == {"n"} and wlv.startswith(("y", "z")):
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

        return phases_hv, phases_lv

    def _compute_phases_single(
        self, id: Id, bus_hv: Bus, bus_lv: Bus, phases_hv: str | None, phases_lv: str | None
    ) -> tuple[str, str]:
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
            self._check_bus_phases(id=id, bus=bus_hv, phases_hv=phases_hv)

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
            self._check_bus_phases(id=id, bus=bus_lv, phases_lv=phases_lv)

        return phases_hv, phases_lv

    def _compute_phases_center(
        self, id: Id, bus_hv: Bus, bus_lv: Bus, phases_hv: str | None, phases_lv: str | None
    ) -> tuple[str, str]:
        if phases_hv is None:
            phases_hv = "".join(p for p in bus_lv.phases if p in bus_hv.phases and p != "n")
            phases_hv = phases_hv.replace("ac", "ca")
            if phases_hv not in self._allowed_phases_single:
                msg = f"HV phases of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_single, phases_hv=phases_hv)
            self._check_bus_phases(id=id, bus=bus_hv, phases_hv=phases_hv)

        if phases_lv is None:
            phases_lv = "".join(p for p in bus_lv.phases if p in bus_hv.phases or p == "n")
            if phases_lv not in self._allowed_phases_center_lv_side:
                msg = f"LV phases of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id=id, allowed_phases=self._allowed_phases_center_lv_side, phases_lv=phases_lv)
            self._check_bus_phases(id=id, bus=bus_lv, phases_lv=phases_lv)

        return phases_hv, phases_lv

    @staticmethod
    def _check_bus_phases(id: Id, bus: Bus, **kwargs: str) -> None:
        name, phases = kwargs.popitem()  # phases_hv or phases_lv
        side = "HV" if name == "phases_hv" else "LV"
        phases_not_in_bus = set(phases) - set(bus.phases)
        if phases_not_in_bus:
            if len(phases_not_in_bus) == 1:
                ph = f"phase {next(iter(phases_not_in_bus))!r}"
                be = "is"
            else:
                ph = f"phases {sorted(phases_not_in_bus)}"
                be = "are"
            msg = f"{side} {ph} of transformer {id!r} {be} not in phases {bus.phases!r} of its {side} bus {bus.id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

    @property
    @ureg_wraps("VA", (None,))
    def res_power_losses(self) -> Q_[complex]:
        """Get the total power losses in the transformer (in VA)."""
        powers1, powers2 = self._res_powers_getter(warning=True)
        return sum(powers1) + sum(powers2)

    def _res_loading_getter(self, warning: bool) -> float:
        powers1, powers2 = self._res_powers_getter(warning)
        return max(abs(powers1.sum()), abs(powers2.sum())) / self._parameters._sn

    @property
    @ureg_wraps("", (None,))
    def res_loading(self) -> Q_[float]:
        """Get the loading of the transformer (unitless)."""
        return self._res_loading_getter(warning=True)

    @property
    def res_violated(self) -> bool:
        """Whether the transformer power loading exceeds its maximal loading."""
        # True if either the HV or LV side is overloaded
        loading = self._res_loading_getter(warning=True)
        return bool(loading > self._max_loading)

    #
    # Json Mixin interface
    #
    def _to_dict(self, include_results: bool) -> JsonDict:
        res = super()._to_dict(include_results=include_results)
        res["tap"] = self.tap
        res["params_id"] = self.parameters.id
        res["max_loading"] = self._max_loading

        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents1, currents2 = self._res_currents_getter(warning)
        results = {
            "id": self.id,
            "phases1": self.phases_hv,
            "phases2": self.phases_lv,
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

            sum_powers1 = sum(powers1)
            sum_powers2 = sum(powers2)
            power_losses = sum_powers1 + sum_powers2
            results["power_losses"] = [power_losses.real, power_losses.imag]
            loading = max(abs(sum_powers1), abs(sum_powers2)) / self.parameters._sn
            results["loading"] = loading

        return results
