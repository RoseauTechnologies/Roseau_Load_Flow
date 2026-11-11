import logging
from typing import TYPE_CHECKING, Final, Literal, NoReturn, Self, get_args

import numpy as np

from roseau.load_flow.constants import SQRT3
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Complex, Float, Id, JsonDict, QtyOrMag, RegulatorConnection
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import Identifiable, JsonMixin, pretty_unit, warn_external
from roseau.load_flow_engine.cy_engine import CySingleVoltageRegulator, CyVoltageRegulator

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

type PowerFactoryRegulatorType = Literal["Type A", "Type B"]
"""The type of a DIgSILENT PowerFactory step-voltage regulator (``TypVoltreg.type``)."""
type PowerFactoryRegulatorConfiguration = Literal[
    "Star, 3-phase", "Star, 3 x 1-phase", "Closed delta, 3 x 1-phase", "Open delta, 2 x 1-phase"
]
"""The configuration of a DIgSILENT PowerFactory step-voltage regulator (``TypVoltreg.config``)."""
type PowerFactoryClosedDeltaConnection = Literal["Lagging", "Leading"]
"""The connection of a DIgSILENT PowerFactory closed-delta step-voltage regulator
(``TypVoltreg.cldeltacn``)."""


class _RegulatorParametersMixin:
    """Common methods of the multi-phase and single-phase voltage regulator parameters."""

    _un: float
    _u_range: float

    def _create_cy_tap_calculator(self, u_ref: float) -> CyVoltageRegulator | CySingleVoltageRegulator:
        """Create a C++ regulator unit used to compute the no-load tap ratios."""
        raise NotImplementedError

    def _compute_tap(self, u_in: Float, cy_element: CyVoltageRegulator | CySingleVoltageRegulator) -> float:
        return cy_element.compute_tap(float(u_in) / SQRT3)

    def compute_tap(self, u_ref: Float, u_in: Float) -> float:
        """Compute the no-load tap ratio for the given source-side voltage magnitude (V).

        This is the steady-state tap of an ideal regulator unit (no series impedance, no load).

        Args:
            u_ref:
                Target voltage on the load side (p.u.).

            u_in:
                Source-side (line-to-line) voltage magnitude (V).

        Returns:
            The tap ratio (a) as a fraction, e.g. 1.05 means +5 % boost, 0.95 means -5 % buck.
            Bounded to (1 - u_range, 1 + u_range).
        """
        cy_element = self._create_cy_tap_calculator(u_ref=float(u_ref))
        return self._compute_tap(u_in=u_in, cy_element=cy_element)

    def plot_tap(self, u_ref: Float, voltages: np.ndarray, *, ax: "Axes | None" = None) -> "Axes":
        """Plot the no-load tap position (%) as a function of source-side voltage.

        Args:
            u_ref:
                Target voltage on the load side (p.u.).

            voltages:
                Array of source-side (line-to-line) voltage magnitudes to evaluate (V).

            ax:
                Axes to draw on. Uses the current axes if not provided.

        Returns:
            The axes with the plot.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            ax = plt.gca()

        u_ref = float(u_ref)
        scale, unit = (1e-3, "kV") if self._un > 1000 else (1.0, "V")
        u_ref_v = u_ref * self._un * scale  # convert p.u. → V for the voltage axis

        voltages = np.asarray(voltages, dtype=float)
        cy_element = self._create_cy_tap_calculator(u_ref=u_ref)
        taps = np.array([self._compute_tap(u_in=u, cy_element=cy_element) for u in voltages])
        taps_pct = (taps - 1.0) * 100.0

        ax.scatter(voltages * scale, taps_pct, color="steelblue", marker=".", s=20, label="Tap (%)")
        ax.axvline(
            x=u_ref_v,
            color="green",
            linestyle="--",
            linewidth=1,
            label=f"$u_{{ref}}$ = {u_ref_v:.3g} {unit}",
        )
        ax.axhline(y=0.0, color="gray", linestyle=":", linewidth=1, label="Neutral (0 %)")
        ax.axhline(
            y=self._u_range * 100.0,
            color="red",
            linestyle=":",
            linewidth=1,
            label=f"Max boost (+{self._u_range * 100:.0f} %)",
        )
        ax.axhline(
            y=-self._u_range * 100.0,
            color="orange",
            linestyle=":",
            linewidth=1,
            label=f"Max buck ({-self._u_range * 100:.0f} %)",
        )
        ax.grid(visible=True)
        ax.set_xlabel(f"Source-side voltage ({unit})")
        ax.set_ylabel("Tap position (%)")
        ax.legend()

        return ax

    def plot_voltage(self, u_ref: Float, voltages: np.ndarray, *, ax: "Axes | None" = None) -> "Axes":
        """Plot the regulated load-side voltage as a function of source-side voltage.

        For each source-side voltage ``u_in``, the no-load tap ``a`` is computed and the output
        voltage is ``u_out = a · u_in``. This gives the exact no-load regulation curve of a
        regulator unit.

        Args:
            u_ref:
                Target voltage on the load side (p.u.).

            voltages:
                Array of source-side (line-to-line) voltage magnitudes to evaluate (V). Should span
                the range of interest around ``u_ref * un``, e.g. ``np.linspace(0.8, 1.2, 100) * un``.

            ax:
                Axes to draw on. Uses the current axes if not provided.

        Returns:
            The axes with the plot.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            ax = plt.gca()

        u_ref = float(u_ref)
        scale, unit = (1e-3, "kV") if self._un > 1000 else (1.0, "V")
        u_ref_v = u_ref * self._un * scale  # convert p.u. → V for the voltage axis

        u_in = np.asarray(voltages, dtype=float)
        cy_element = self._create_cy_tap_calculator(u_ref=u_ref)
        taps = np.array([self._compute_tap(u_in=u, cy_element=cy_element) for u in u_in])
        u_in = u_in * scale
        u_out = taps * u_in  # output voltage produced by this source voltage (exact at no-load)

        ax.plot(u_in, u_out, color="steelblue", marker=".", label="Output voltage")
        ax.plot(u_in, u_in, color="gray", marker=".", label="No regulation ($a = 1$)")
        ax.axhline(y=u_ref_v, color="green", linestyle="--", linewidth=1, label=f"$u_{{ref}}$ = {u_ref_v:.3g} {unit}")
        ax.grid(visible=True)
        ax.set_xlabel(f"Source-side voltage ({unit})")
        ax.set_ylabel(f"Load-side voltage ({unit})")
        ax.legend()

        return ax


class RegulatorParameters(_RegulatorParametersMixin, Identifiable, JsonMixin):
    """Parameters that define the electrical model of a multi-phase voltage regulator.

    A voltage regulator is a bank of single-phase *units*, each an autotransformer with an on-load
    tap changer in its series winding. Each unit has its own tap ratio ``a``, which keeps its
    regulated (load-side) voltage at ``u_ref`` while ``a`` stays within
    ``[1 - u_range, 1 + u_range]``, and stays at its bound otherwise. The control law is the fixed
    point:

        a = softclamp(a · u_ref / |U_out|, 1 - u_range, 1 + u_range)

    where ``softclamp`` is a clamp smoothed with softplus functions of steepness ``alpha``.

    The ``connection`` gives how the units are connected (the regulators' counterpart of a
    transformer's vector group):

    - ``"wye"``: a star, each unit is connected between a phase and the neutral, which is carried
      through the regulator. The phases of the regulator must contain the neutral (``"an"``,
      ``"abn"``, ``"abcn"``, etc.). Each unit regulates its phase-to-neutral voltage.
    - ``"delta_positive_rotation"``: a closed delta (ANSI/PowerFactory "lagging" connection), the
      common terminal of each unit is the output of the next phase (A → B → C → A). The phases of
      the regulator must be ``"abc"``. Each unit regulates a line-to-line voltage.
    - ``"delta_negative_rotation"``: a closed delta (ANSI/PowerFactory "leading" connection), the
      common terminal of each unit is the output of the previous phase (A → C → B → A).

    The parameters here define the physical and control characteristics shared across all
    regulator instances that use the same parameter set. The per-instance target voltage ``u_ref``
    is set on the :class:`VoltageRegulator` element itself.
    """

    is_multi_phase: Final = True
    allowed_connections: Final[frozenset[RegulatorConnection]] = frozenset(get_args(RegulatorConnection.__value__))
    """The allowed connections of the regulator units: ``"wye"``, ``"delta_positive_rotation"``
    and ``"delta_negative_rotation"``."""

    @ureg_wraps(None, (None, None, "VA", "V", "ohm", "S", None, None, None))
    def __init__(
        self,
        id: Id,
        *,
        sn: QtyOrMag[Float],
        un: QtyOrMag[Float],
        z2: QtyOrMag[Complex],
        ym: QtyOrMag[Complex],
        u_range: Float = 0.1,
        connection: RegulatorConnection = "wye",
        alpha: Float = 1000.0,
    ) -> None:
        """RegulatorParameters constructor.

        Args:
            id:
                A unique ID of the regulator parameters.

            sn:
                Rated (total, throughput) apparent power of the regulator (VA): the power flowing
                through the regulator at its rated current (``√3·un·In`` for a three-phase
                regulator). This is not the regulator's own catalogue rating, which only covers the
                boosted or bucked part of that power: ``sn · u_range``.

            un:
                Nominal (line-to-line) voltage of the regulator (V).

            z2:
                Series impedance of the series winding of each unit (Ω). Must be non-zero.

            ym:
                Magnetising admittance of the shunt winding of each unit (S).

            u_range:
                Voltage regulation range as a fraction, e.g. ``0.1`` means ±10 %. Defaults to 0.1.

            connection:
                How the units of the regulator are connected: ``"wye"`` (default),
                ``"delta_positive_rotation"`` or ``"delta_negative_rotation"``.

            alpha:
                Steepness of the softplus functions smoothing the tap bounds: the corners of the
                characteristic are rounded over about ``1 / alpha`` in tap ratio. Must be positive.
                Defaults to 1000.
        """
        super().__init__(id)
        if sn <= 0:
            msg = f"sn must be positive, got {sn!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        if un <= 0:
            msg = f"un must be positive, got {un!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        if z2 == 0:
            msg = f"z2 must be non-zero, got {z2!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        if u_range <= 0 or u_range >= 1:
            msg = f"u_range must be between 0 and 1, got {u_range!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        if alpha <= 0:
            msg = f"alpha must be positive, got {alpha!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        if connection not in self.allowed_connections:
            msg = (
                f"Invalid connection {connection!r} for regulator parameters {id!r}. Allowed "
                f"connections are: {sorted(self.allowed_connections)}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONNECTION)
        self._sn = float(sn)
        self._un = float(un)
        self._z2 = complex(z2)
        self._ym = complex(ym)
        self._u_range = float(u_range)
        self._connection: RegulatorConnection = connection
        self._alpha = float(alpha)
        self._elements: set = set()

    @classmethod
    @ureg_wraps(None, (None, None, "kV", "A", "percent", "percent", "W", None, None, None))
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
        configuration: PowerFactoryRegulatorConfiguration = "Star, 3-phase",
        closed_delta_connection: PowerFactoryClosedDeltaConnection | None = None,
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

            configuration:
                The configuration of the regulator (``config``): ``"Star, 3-phase"`` (default) and
                ``"Star, 3 x 1-phase"`` give ``"wye"`` parameters, ``"Closed delta, 3 x 1-phase"``
                gives closed-delta parameters. The open delta is not supported.

            closed_delta_connection:
                The connection of a closed delta (``cldeltacn``): ``"Lagging"`` (default) gives the
                ``"delta_positive_rotation"`` connection, ``"Leading"`` the
                ``"delta_negative_rotation"`` one. Ignored by the star configurations.

        Returns:
            The created regulator parameters.
        """
        un = float(un) * 1e3  # V
        in_ = float(in_)
        if configuration == "Star, 3-phase":
            un_ll, sb, connection = un, SQRT3 * un * in_, "wye"
        elif configuration == "Star, 3 x 1-phase":
            un_ll, sb, connection = un * SQRT3, un * in_, "wye"
        elif configuration == "Closed delta, 3 x 1-phase":
            if closed_delta_connection is None or closed_delta_connection == "Lagging":
                connection = "delta_positive_rotation"
            elif closed_delta_connection == "Leading":
                connection = "delta_negative_rotation"
            else:
                msg = (
                    f"Invalid closed delta connection {closed_delta_connection!r} for regulator "
                    f"parameters {id!r}: expected 'Lagging' or 'Leading'."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONNECTION)
            un_ll, sb = un, un * in_
        else:
            msg = (
                f"The PowerFactory step-voltage regulator configuration {configuration!r} of the "
                f"regulator parameters {id!r} is not supported."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONNECTION)
        if kind == "Type B":
            warn_external(
                f"The Type B step-voltage regulator {id!r} has a tap ratio 1/(1 - n·dutap), "
                f"approximated by the Type A ratio 1 + n·dutap."
            )
        elif kind != "Type A":
            msg = f"Invalid regulator type {kind!r} for regulator parameters {id!r}: expected 'Type A' or 'Type B'."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        sn = SQRT3 * un_ll * in_  # VA, the throughput rating
        zb = un * un / sb  # The base impedance of each unit (Ω)
        r = float(pcu) / sb  # p.u.
        z = float(uk) / 100.0  # p.u.
        if r > z:
            msg = (
                f"The copper losses pcu={pcu} W of the regulator parameters {id!r} exceed what their "
                f"short-circuit voltage uk={uk} % allows."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        z2 = complex(r, np.sqrt(z * z - r * r)) * zb
        return cls(id, sn=sn, un=un_ll, z2=z2, ym=0.0, u_range=float(pc_reg) / 100.0, connection=connection)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}: id={self.id!r}, sn={self._sn}, un={self._un}, z2={self._z2}, "
            f"ym={self._ym}, u_range={self._u_range}, connection={self._connection!r}, alpha={self._alpha}>"
        )

    @property
    def sn(self) -> Q_[float]:
        """Rated (total, throughput) apparent power of the regulator (VA)."""
        return Q_(self._sn, "VA")

    @property
    def un(self) -> Q_[float]:
        """Nominal (line-to-line) voltage of the regulator (V)."""
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
    def connection(self) -> RegulatorConnection:
        """How the units of the regulator are connected."""
        return self._connection

    @property
    def is_delta(self) -> bool:
        """Whether the units of the regulator are connected in a closed delta."""
        return self._connection != "wye"

    @property
    def alpha(self) -> float:
        """Steepness of the softplus functions smoothing the tap bounds."""
        return self._alpha

    def _create_cy_element(self, n: int, u_ref: float) -> CyVoltageRegulator:
        """Create the C++ model of a regulator with `n` ports per side using these parameters."""
        return CyVoltageRegulator(
            n=n,
            connection=self._connection,
            z2=self._z2,
            ym=self._ym,
            u_ref=self._un * u_ref / SQRT3,
            u_range=self._u_range,
            alpha=self._alpha,
        )

    def _create_cy_tap_calculator(self, u_ref: float) -> CyVoltageRegulator:
        # A single wye unit: the no-load characteristic of every unit
        return CyVoltageRegulator(
            n=2,
            connection="wye",
            z2=self._z2,
            ym=self._ym,
            u_ref=self._un * u_ref / SQRT3,
            u_range=self._u_range,
            alpha=self._alpha,
        )

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
            "u_range": self._u_range,
            "connection": self._connection,
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
            u_range=data["u_range"],
            connection=data.get("connection", "wye"),
            alpha=data["alpha"],
        )
