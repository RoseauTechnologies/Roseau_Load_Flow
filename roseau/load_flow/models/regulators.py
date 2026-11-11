import logging
from typing import Final, final

import numpy as np
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.constants import SQRT3
from roseau.load_flow.converters import calculate_voltage_phases
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch, AbstractBranchSide
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.regulator_parameters import RegulatorParameters
from roseau.load_flow.typing import Float, FloatArray, Id, JsonDict, QtyOrMag, ResultState
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import warn_external
from roseau.load_flow_engine.cy_engine import CyVoltageRegulator  # noqa: F401

logger = logging.getLogger(__name__)


# The Cy* types are stringified so that autoapi/astroid can resolve inheritance for the documentation.
@final
class VoltageRegulator(AbstractBranch["RegulatorSide", "CyVoltageRegulator"]):
    """A multi-phase voltage regulator with continuous smooth tap control.

    A voltage regulator is a bank of single-phase units, each an autotransformer with an on-load
    tap changer, whose tap keeps its regulated voltage on the load side (``bus2``) at ``u_ref``.
    Every unit has its own tap, controlled independently. How the units are connected is defined by
    the :attr:`~RegulatorParameters.connection` of the ``parameters``.

    See Also:
        :doc:`Voltage regulator model documentation </models/VoltageRegulator>`
    """

    element_type: Final = "regulator"
    allowed_phases: Final = frozenset({"an", "bn", "cn", "abn", "bcn", "can", "abcn", "abc"})
    """The allowed phases for a voltage regulator are:

    - P-N, P-P-N or P-P-P-N: ``"an"``, ``"bn"``, ``"cn"``, ``"abn"``, ``"bcn"``, ``"can"``,
      ``"abcn"`` for the ``"wye"`` connection (one unit per phase);
    - P-P-P: ``"abc"`` for the closed-delta connections (three units).
    """

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        parameters: RegulatorParameters,
        u_ref: QtyOrMag[Float] = 1.0,
        phases: str | None = None,
        max_loading: QtyOrMag[Float] = 1.0,
        geometry: BaseGeometry | None = None,
    ) -> None:
        """VoltageRegulator constructor.

        Args:
            id:
                A unique ID of the regulator in the network regulators.

            bus1:
                Bus to connect to the source side.

            bus2:
                Bus to connect to the load side. The regulator drives the voltages of this bus
                toward ``u_ref``.

            parameters:
                Parameters defining the electrical model of the regulator. Can be shared across
                multiple regulator instances. Its :attr:`~RegulatorParameters.connection` must be
                compatible with the phases of the regulator.

            u_ref:
                Target voltage magnitude on the load side (p.u. of the nominal voltage ``un`` of
                the parameters). Each unit drives its regulated voltage toward this value: the
                phase-to-neutral voltage (in p.u. of ``un / √3``) for a ``"wye"`` connection, the
                line-to-line voltage (in p.u. of ``un``) for a closed delta. Defaults to 1.0.

            phases:
                The phases of the regulator, common to both sides. A string like ``"abcn"`` or
                ``"abc"``. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases must be present in both connected buses. By
                default, ``"abc"`` for a closed delta and the phases common to both buses for a
                ``"wye"`` connection.

            max_loading:
                The maximum loading of the regulator (unitless). It is used with the ``sn`` of the
                parameters to compute the :attr:`max_power`, :attr:`res_loading` and
                :attr:`res_violated` of the regulator. Defaults to 1.0.

            geometry:
                The geometry of the regulator.
        """
        self._initialized = False
        self._res_taps: FloatArray | None = None
        self._check_compatible_phase_tech(parameters, id=id)
        if phases is None and parameters.is_delta:
            phases = "abc"
        phases = self._check_phases_common(id, bus1=bus1, bus2=bus2, phases=phases)
        self._check_connection(id=id, phases=phases, parameters=parameters)
        super().__init__(id=id, bus1=bus1, bus2=bus2, phases1=phases, phases2=phases, geometry=geometry)
        self._side1 = RegulatorSide(branch=self, side=1, bus=bus1, phases=phases, connect_neutral=None)
        self._side2 = RegulatorSide(branch=self, side=2, bus=bus2, phases=phases, connect_neutral=None)
        self.u_ref = u_ref
        self.parameters = parameters
        self.max_loading = max_loading
        self._initialized = True

        self._cy_element = parameters._create_cy_element(n=self._side1._n, u_ref=self._u_ref)
        self._cy_connect()
        self._connect(bus1, bus2)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}: id={self.id!r}, bus1={self.bus1.id!r}, bus2={self.bus2.id!r}, "
            f"phases={self.phases!r}, u_ref={self._u_ref:f}, max_loading={self._max_loading:f}>"
        )

    @classmethod
    def _check_connection(cls, id: Id, phases: str, parameters: RegulatorParameters) -> None:
        """Check that the phases of the regulator are compatible with the connection of its parameters."""
        if parameters.is_delta:
            ok = phases == "abc"
            expected = "'abc'"
        else:
            ok = "n" in phases
            expected = "phases with a neutral ('an', 'abn', 'abcn', etc.)"
        if not ok:
            msg = (
                f"Phases {phases!r} of voltage regulator {id!r} are not compatible with the "
                f"connection {parameters.connection!r} of its parameters {parameters.id!r}: "
                f"expected {expected}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

    @property
    def phases(self) -> str:
        """The phases of the regulator. This is an alias for :attr:`phases1` and :attr:`phases2`."""
        return self._side1._phases

    @property
    def tap_phases(self) -> list[str]:
        """The pairs of terminals each unit of the regulator is connected between, in the order of
        :attr:`res_taps`: ``"an"``, ``"bn"``, ``"cn"`` for a ``"wye"`` connection, ``"ab"``,
        ``"bc"``, ``"ca"`` for a closed delta."""
        return calculate_voltage_phases(self.phases)

    def _no_load_potentials(self, potentials: dict[str, complex]) -> dict[str, complex]:
        """Estimate the load-side potentials from the source-side ones with the no-load taps.

        This is only used to initialize the potentials of the buses before the load flow.
        """
        params = self._parameters
        u_ref = self._u_ref * params._un / SQRT3
        v_n = potentials.get("n", 0j)
        new_potentials = dict(potentials)
        for phase in self.phases:
            if phase == "n" or phase not in potentials:
                continue
            u = abs(potentials[phase] - v_n)
            if u > 0:
                tap = min(max(u_ref / u, 1 - params._u_range), 1 + params._u_range)
                new_potentials[phase] = v_n + tap * (potentials[phase] - v_n)
        return new_potentials

    def _update_cy_parameters(self) -> None:
        """Update the C++ model parameters after a change in u_ref, z2, or ym."""
        if self._cy_initialized:
            self._cy_element.update_parameters(
                self._parameters._z2, self._parameters._ym, self._u_ref * self._parameters._un / SQRT3
            )

    @property
    def parameters(self) -> RegulatorParameters:
        """The parameters of the voltage regulator."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: RegulatorParameters) -> None:
        self._check_compatible_phase_tech(value)
        old_parameters = self._parameters if self._initialized else None
        if old_parameters is not None:
            self._check_connection(id=self.id, phases=self.phases, parameters=value)
        self._update_network_parameters(old_parameters=old_parameters, new_parameters=value)
        self._invalidate_network_results()
        self._parameters = value
        if self._cy_initialized:
            assert old_parameters is not None
            if (
                old_parameters._connection != value._connection
                or old_parameters._u_range != value._u_range
                or old_parameters._alpha != value._alpha
            ):
                # These parameters are baked in the C++ model, rebuild it
                if self._network is not None:
                    self._network._valid = False
                self._cy_element.disconnect()
                self._cy_element = value._create_cy_element(n=self._side1._n, u_ref=self._u_ref)
                self._cy_connect()
            else:
                self._update_cy_parameters()

    @property
    def u_ref(self) -> Q_[float]:
        """Target voltage on the load side (p.u. of the nominal voltage ``un`` of the parameters)."""
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
        self._update_cy_parameters()

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
        if self._fetch_results:
            super()._refresh_results()
            taps = self._cy_element.get_taps()
            if self._parameters._connection == "delta_negative_rotation":
                # The unit of phase "a" is connected between "c" and "a": reorder as "ab", "bc", "ca"
                taps = np.roll(taps, -1)
            self._res_taps = taps

    def _res_taps_getter(self, warning: bool) -> FloatArray:
        self._refresh_results()
        return self._res_getter(self._res_taps, warning)

    def _res_loading_getter(self, warning: bool) -> float:
        powers1 = self._side1._res_powers_getter(warning)
        powers2 = self._side2._res_powers_getter(warning=False)  # warn only once
        return max(abs(powers1.sum()), abs(powers2.sum())) / self._parameters._sn

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
    def res_taps(self) -> FloatArray:
        """The tap ratios applied by the units of the regulator, in the order of :attr:`tap_phases`.

        A value of 1.05 means that the unit boosted its output voltage by 5%; 0.95 means a 5% buck.
        Each tap is bounded to `(1 - u_range, 1 + u_range)`.
        """
        return self._res_taps_getter(warning=True)

    @property
    def res_power_losses(self) -> Q_[complex]:
        """Get the total power losses in the regulator (in VA)."""
        powers1 = self._side1._res_powers_getter(warning=True)
        powers2 = self._side2._res_powers_getter(warning=False)  # warn only once
        return Q_(sum(powers1) + sum(powers2), "VA")

    @property
    def res_loading(self) -> Q_[float]:
        """Get the loading of the regulator (unitless)."""
        return Q_(self._res_loading_getter(warning=True), "")

    @property
    def res_violated(self) -> bool:
        """Whether the regulator power loading exceeds its maximal loading."""
        # True if either the source side or load side is overloaded
        loading = self._res_loading_getter(warning=True)
        return bool(loading > self._max_loading)

    #
    # Json Mixin interface
    #
    @classmethod
    def _from_dict(cls, data: JsonDict, *, include_results: bool = True) -> "VoltageRegulator":
        results = data.get("results")  # peek before super() pops it
        taps = results.pop("taps", None) if results else None
        self = super()._from_dict(data, include_results=include_results)
        if include_results and taps is not None:
            self._res_taps = np.array(taps, dtype=np.float64)
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results)
        data["params_id"] = self.parameters.id
        data["u_ref"] = self._u_ref
        data["max_loading"] = self._max_loading
        if include_results:
            data["results"]["taps"] = self._res_taps_getter(warning=False).tolist()  # warn only once
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning, full)
        results["taps"] = self._res_taps_getter(warning=False).tolist()  # warn only once
        if full:
            # Add regulator specific results
            powers1 = self._side1._res_powers_getter(warning=False)
            powers2 = self._side2._res_powers_getter(warning=False)
            sum_powers1, sum_powers2 = sum(powers1), sum(powers2)
            power_losses = sum_powers1 + sum_powers2
            loading = max(abs(sum_powers1), abs(sum_powers2)) / self.parameters._sn
            results["power_losses"] = [power_losses.real, power_losses.imag]
            results["loading"] = loading
        return results


@final
class RegulatorSide(AbstractBranchSide):
    element_type = "regulator"
    allowed_phases = VoltageRegulator.allowed_phases  # type: ignore
    _branch: VoltageRegulator
