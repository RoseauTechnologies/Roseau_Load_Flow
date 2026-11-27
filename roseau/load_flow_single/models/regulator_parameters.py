import logging
from typing import Final, NoReturn, Self

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.regulator_parameters import (
    PowerFactoryRegulatorConfiguration,
    PowerFactoryRegulatorType,
    _RegulatorParametersMixin,
)
from roseau.load_flow.typing import Complex, Float, Id, JsonDict, QtyOrMag, RegulatorConfig
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import Identifiable, JsonMixin, pretty_unit
from roseau.load_flow_engine.cy_engine import (
    CySingleDeltaVoltageRegulator,
    CySingleVoltageRegulator,
    CySingleVoltageRegulatorBase,
)

logger = logging.getLogger(__name__)


class RegulatorParameters(_RegulatorParametersMixin, Identifiable, JsonMixin):
    """Parameters that define the electrical model of a three-phase voltage regulator.

    A voltage regulator is modelled as an autotransformer whose tap ratio ``a`` keeps the load-side
    voltage at ``u_ref`` while ``a`` stays within ``[1 - u_range, 1 + u_range]``, and stays at its bound
    otherwise. The control law is the fixed point:

        a = softclamp(a · u_ref / |U_sec|, 1 - u_range, 1 + u_range)

    where ``softclamp`` is a clamp smoothed with softplus functions of steepness ``alpha``.

    The regulator is the single-line equivalent of a balanced bank of three single-phase units,
    whose ``config`` gives how they are connected:

    - ``"wye"``: a star, each unit being connected between a phase and the neutral. The output
      voltage is ``a`` times the input voltage at no load, in phase with it.
    - ``"closed-delta"``: a closed delta with a positive rotation (ANSI/PowerFactory "lagging"
      connection), the common terminal of each unit being the output of the next phase. The units
      act on each other's outputs: at no load, the output voltage is ``a / (1 - (1 - a)·α²)`` times
      the input voltage, which regulates over about 1.5 times the tap range, with a phase shift
      that depends on the tap (the output leads the input when boosting).

    The parameters here define the physical and control characteristics shared across all
    regulator instances that use the same parameter set. The per-instance target voltage ``u_ref``
    is set on the :class:`VoltageRegulator` element itself.
    """

    is_multi_phase: Final = False
    allowed_configs: Final[frozenset[RegulatorConfig]] = frozenset({"wye", "closed-delta"})
    """The allowed configurations of the regulator units: ``"wye"`` and ``"closed-delta"``."""

    @ureg_wraps(None, (None, None, "VA", "V", "ohm", "S", None, None, None))
    def __init__(
        self,
        id: Id,
        *,
        sn: QtyOrMag[Float],
        un: QtyOrMag[Float],
        z2: QtyOrMag[Complex],
        ym: QtyOrMag[Complex],
        config: RegulatorConfig,
        u_range: Float = 0.1,
        alpha: Float = 1000.0,
    ) -> None:
        """RegulatorParameters constructor.

        Args:
            id:
                A unique ID of the regulator parameters.

            sn:
                Rated (total, throughput) apparent power of the regulator (VA): the power flowing
                through the regulator at its rated current (``√3·un·In``).

            un:
                Nominal voltage of the regulator (V).

            z2:
                Series impedance of the series winding of each unit (Ω). Must be non-zero.

            ym:
                Magnetising admittance of the shunt winding of each unit (S).

            config:
                How the units of the regulator are connected: ``"wye"`` or ``"closed-delta"``.

            u_range:
                Voltage regulation range as a fraction, e.g. ``0.1`` means ±10 %. Defaults to 0.1.

            alpha:
                Steepness of the softplus functions smoothing the tap bounds: the corners of the
                characteristic are rounded over about ``1 / alpha`` in tap ratio. Must be positive.
                Defaults to 1000.
        """
        super().__init__(id)
        if sn <= 0:
            msg = f"sn must be positive, got {sn!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS)
        if un <= 0:
            msg = f"un must be positive, got {un!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS)
        if z2 == 0:
            msg = f"z2 must be non-zero, got {z2!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS)
        if u_range <= 0 or u_range >= 1:
            msg = f"u_range must be between 0 and 1, got {u_range!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS)
        if alpha <= 0:
            msg = f"alpha must be positive, got {alpha!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS)
        if config not in self.allowed_configs:
            msg = (
                f"Invalid config {config!r} for regulator parameters {id!r}. Allowed "
                f"configs are: {sorted(self.allowed_configs)}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONFIG)
        self._sn = float(sn)
        self._un = float(un)
        self._z2 = complex(z2)
        self._ym = complex(ym)
        self._u_range = float(u_range)
        self._config: RegulatorConfig = config
        self._alpha = float(alpha)
        self._elements: set = set()

    @classmethod
    @ureg_wraps(None, (None, None, "kV", "A", "percent", "percent", "W", None, None))
    def from_power_factory(
        cls,
        id: Id,
        *,
        un: QtyOrMag[Float],
        in_: QtyOrMag[Float],
        pc_reg: QtyOrMag[Float],
        uk: QtyOrMag[Float],
        pcu: QtyOrMag[Float],
        kind: PowerFactoryRegulatorType = "Type A",
        config: PowerFactoryRegulatorConfiguration = "Star, 3-phase",
    ) -> Self:
        """Create regulator parameters from the data of a DIgSILENT PowerFactory step-voltage
        regulator type (``TypVoltreg``).

        PowerFactory's step-voltage regulator is an autotransformer with a tap changer covering
        ``±pc_reg`` % and a series impedance (``uk``, ``pcu``) given in per-unit of its circuit base
        power ``Sb``: ``Sb = √3·Un·In`` for the "Star, 3-phase" configuration, the base power
        ``Un·In`` of a single-phase unit for the others. Its tap ratio is ``1 + n·dutap`` for a
        Type A regulator, exactly the law of this model, and ``1 / (1 - n·dutap)`` for a Type B
        regulator, approximated by the Type A law (identical at the neutral tap, 1.1 instead of
        1.111 at the end of a ±10 % range). The magnetising admittance is zero.

        Args:
            id:
                A unique ID of the regulator parameters.

            un:
                The rated voltage (kV, ``Un``): line-to-neutral for the "Star, 3 x 1-phase"
                configuration, line-to-line otherwise.

            in_:
                The rated current (A, ``In``). It gives the rated (throughput) power of the
                parameters ``sn = √3·Un·In`` (``Un`` line-to-line).

            pc_reg:
                The voltage regulation range (+/-, %, ``pcReg``).

            uk:
                The short-circuit voltage (%, ``uk``).

            pcu:
                The copper losses (W, ``pcu``), per single-phase unit except for the "Star,
                3-phase" configuration.

            kind:
                The type of the regulator (``type``): ``"Type A"`` (default) or ``"Type B"``.

            config:
                The configuration of the regulator (``config``): ``"Star, 3-phase"`` (default) and
                ``"Star, 3 x 1-phase"`` give ``"wye"`` parameters, ``"Closed delta, 3 x 1-phase"``
                gives ``"closed-delta"`` parameters, those of a "lagging" closed delta. The open
                delta is not supported.

        Returns:
            The created regulator parameters.
        """
        sn, un_ll, z2, u_range, rp_config = cls._parse_power_factory_params(
            id, un=un, in_=in_, pc_reg=pc_reg, uk=uk, pcu=pcu, kind=kind, config=config
        )
        return cls(id, sn=sn, un=un_ll, z2=z2, ym=0.0, u_range=u_range, config=rp_config)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}: id={self.id!r}, sn={self._sn}, un={self._un}, z2={self._z2}, "
            f"ym={self._ym}, config={self._config!r}, u_range={self._u_range}, alpha={self._alpha}>"
        )

    @property
    def sn(self) -> Q_[float]:
        """Rated (total, throughput) apparent power of the regulator (VA)."""
        return Q_(self._sn, "VA")

    @property
    def un(self) -> Q_[float]:
        """Nominal voltage of the regulator (V)."""
        return Q_(self._un, "V")

    @property
    def z2(self) -> Q_[complex]:
        """Series impedance of the series winding of each unit (Ω)."""
        return Q_(self._z2, "ohm")

    @property
    def ym(self) -> Q_[complex]:
        """Magnetising admittance of the shunt winding of each unit (S)."""
        return Q_(self._ym, "S")

    @property
    def u_range(self) -> float:
        """Voltage regulation range as a fraction (e.g. 0.1 means ±10 %)."""
        return self._u_range

    @property
    def config(self) -> RegulatorConfig:
        """How the units of the regulator are connected."""
        return self._config

    @property
    def alpha(self) -> float:
        """Steepness of the softplus functions smoothing the tap bounds."""
        return self._alpha

    def _create_cy_element(self, u_ref: float) -> CySingleVoltageRegulatorBase:
        """Create the C++ model of the regulator parameters."""
        cls = CySingleDeltaVoltageRegulator if self._config == "closed-delta" else CySingleVoltageRegulator
        return cls(z2=self._z2, ym=self._ym, u_ref=self._un * u_ref / SQRT3, u_range=self._u_range, alpha=self._alpha)

    def _create_cy_tap_calculator(self, u_ref: float) -> CySingleVoltageRegulatorBase:
        return self._create_cy_element(u_ref=u_ref)

    def _rating_pretty(self) -> str:
        """Return a pretty string representation of the regulator rating."""
        return f"{pretty_unit(self._sn, 'VA')} - {pretty_unit(self._un, 'V')}"

    def _to_dict(self, include_results: bool) -> JsonDict:
        return {
            "id": self.id,
            "sn": self._sn,
            "un": self._un,
            "z2": [self._z2.real, self._z2.imag],
            "ym": [self._ym.real, self._ym.imag],
            "config": self._config,
            "u_range": self._u_range,
            "alpha": self._alpha,
        }

    def _results_to_dict(self, warning: bool, full: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    @classmethod
    def _from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        return cls(
            id=data["id"],
            sn=data["sn"],
            un=data["un"],
            z2=complex(*data["z2"]),
            ym=complex(*data["ym"]),
            config=data["config"],
            u_range=data["u_range"],
            alpha=data["alpha"],
        )
