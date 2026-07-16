import logging
from typing import TYPE_CHECKING, Final, NoReturn, Self

import numpy as np

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Complex, Float, FloatArray, Id, JsonDict, QtyOrMag
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import Identifiable, JsonMixin, pretty_unit
from roseau.load_flow_engine.cy_engine import CySingleVoltageRegulator

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)


class RegulatorParameters(Identifiable, JsonMixin):
    """Parameters that define the electrical model of a single-phase voltage regulator.

    A voltage regulator is modelled as an autotransformer with a continuous tanh tap control law:

        a = 1 + u_range · tanh(alpha · (u_ref - |U_sec|) / u_ref)

    The parameters here define the physical and control characteristics shared across all
    regulator instances that use the same parameter set. The per-instance target voltage ``u_ref``
    is set on the :class:`VoltageRegulator` element itself.
    """

    is_multi_phase: Final = False

    @ureg_wraps(None, (None, None, "VA", "V", "ohm", "S", None, None))
    def __init__(
        self,
        id: Id,
        *,
        sn: QtyOrMag[Float],
        un: QtyOrMag[Float],
        z2: QtyOrMag[Complex],
        ym: QtyOrMag[Complex],
        u_range: Float = 0.1,
        alpha: Float = 100.0,
    ) -> None:
        """RegulatorParameters constructor.

        Args:
            id:
                A unique ID of the regulator parameters.

            sn:
                Rated apparent power of the regulator (VA).

            un:
                Nominal voltage of the regulator (V).

            z2:
                Series impedance of the series winding (Ω). Must be non-zero.

            ym:
                Magnetising admittance of the shunt winding (S).

            u_range:
                Voltage regulation range as a fraction, e.g. ``0.1`` means ±10 %. Defaults to 0.1.

            alpha:
                Steepness of the tanh droop. Larger values give tighter voltage regulation.
                Must be positive. Defaults to 100.
        """
        super().__init__(id)
        if u_range <= 0 or u_range >= 1:
            msg = f"u_range must be between 0 and 1, got {u_range!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        if alpha <= 0:
            msg = f"alpha must be positive, got {alpha!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)
        self._sn = float(sn)
        self._un = float(un)
        self._z2 = complex(z2)
        self._ym = complex(ym)
        self._u_range = float(u_range)
        self._alpha = float(alpha)
        self._elements: set = set()

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}: id={self.id!r}, sn={self._sn}, un={self._un}, z2={self._z2}, "
            f"ym={self._ym}, u_range={self._u_range}, alpha={self._alpha}>"
        )

    @property
    def sn(self) -> Q_[float]:
        """Rated apparent power of the regulator (VA)."""
        return Q_(self._sn, "VA")

    @property
    def un(self) -> Q_[float]:
        """Nominal voltage of the regulator (V)."""
        return Q_(self._un, "V")

    @property
    def z2(self) -> Q_[complex]:
        """Series impedance of the series winding (Ω)."""
        return Q_(self._z2, "ohm")

    @property
    def ym(self) -> Q_[complex]:
        """Magnetising admittance of the shunt winding (S)."""
        return Q_(self._ym, "S")

    @property
    def u_range(self) -> float:
        """Voltage regulation range as a fraction (e.g. 0.1 means ±10 %)."""
        return self._u_range

    @property
    def alpha(self) -> float:
        """Steepness of the tanh droop."""
        return self._alpha

    def _create_cy_element(self, u_ref: float) -> "CySingleVoltageRegulator":
        """Create the C++ model of the regulator parameters."""
        return CySingleVoltageRegulator(
            z2=self._z2,
            ym=self._ym,
            u_ref=self._un * u_ref / SQRT3,
            u_range=self._u_range,
            alpha=self._alpha,
            phi=0.0,  # phase shift: hardcoded until connection type is exposed on the Python API
        )

    def _rating_pretty(self) -> str:
        """Return a pretty string representation of the regulator rating."""
        return f"{pretty_unit(self._sn, 'VA')} - {pretty_unit(self._un, 'V')}"

    def _compute_tap(self, u_out: Float, cy_element: "CySingleVoltageRegulator") -> float:
        return cy_element.compute_tap(float(u_out) / SQRT3)

    def _compute_voltage(self, u_in: Complex, i_out: Complex, cy_element: "CySingleVoltageRegulator") -> complex:
        return cy_element.compute_voltage(complex(u_in) / SQRT3, complex(i_out)) * SQRT3

    def compute_tap(self, u_ref: Float, u_out: Float) -> float:
        """Compute the tap ratio for the given load-side voltage magnitude (V).

        Args:
            u_ref:
                Target voltage on the load side (p.u.).

            u_out:
                Load-side voltage magnitude (V).

        Returns:
            The tap ratio (a) as a fraction, e.g. 1.05 means +5 % boost, 0.95 means -5 % buck.
            Bounded to (1 - u_range, 1 + u_range).
        """
        cy_element = self._create_cy_element(u_ref=float(u_ref))
        return self._compute_tap(u_out=u_out, cy_element=cy_element)

    def compute_voltage(self, u_ref: Float, u_in: Complex, i_out: Complex = 0j) -> complex:
        """Compute the load-side voltage for a given source-side voltage and load-side current.

        Uses Newton's method internally to solve the implicit tap-control equation.

        Args:
            u_ref:
                Target voltage on the load side (p.u.).

            u_in:
                Source-side voltage (V).

            i_out:
                Load-side complex current (A). Default: zero (no-load).

        Returns:
            The load-side voltage (V).
        """
        cy_element = self._create_cy_element(u_ref=float(u_ref))
        return self._compute_voltage(u_in=u_in, i_out=i_out, cy_element=cy_element)

    def plot_tap(self, u_ref: Float, voltages: np.ndarray, *, ax: "Axes | None" = None) -> tuple["Axes", FloatArray]:
        """Plot the tap position (%) as a function of load-side voltage.

        Args:
            u_ref:
                Target voltage on the load side (p.u.).

            voltages:
                Array of load-side voltage magnitudes to evaluate (V).

            ax:
                Axes to draw on. Uses the current axes if not provided.

        Returns:
            The axes and the array of tap ratios.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            ax = plt.gca()

        u_ref = float(u_ref)
        u_ref_v = u_ref * self._un  # convert p.u. → V for the voltage axis
        scale, unit = (1e-3, "kV") if u_ref_v > 1000 else (1.0, "V")

        voltages = np.asarray(voltages, dtype=float)
        cy_element = self._create_cy_element(u_ref=u_ref)
        taps = np.array([self._compute_tap(u_out=u, cy_element=cy_element) for u in voltages])
        taps_pct = (taps - 1.0) * 100.0

        ax.scatter(voltages * scale, taps_pct, color="steelblue", marker=".", s=20, label="Tap (%)")
        ax.axvline(
            x=u_ref_v * scale,
            color="green",
            linestyle="--",
            linewidth=1,
            label=f"$u_{{ref}}$ = {u_ref_v * scale:.3g} {unit}",
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
        ax.set_xlabel(f"Load-side voltage ({unit})")
        ax.set_ylabel("Tap position (%)")
        ax.legend()

        return ax, taps

    def plot_voltage(
        self, u_ref: Float, voltages: np.ndarray, i_out: complex = 0j, *, ax: "Axes | None" = None
    ) -> tuple["Axes", FloatArray]:
        """Plot the load-side voltage as a function of source-side voltage.

        Args:
            u_ref:
                Target voltage on the load side (p.u.).

            voltages:
                Array of load-side voltage magnitudes to evaluate (V).

            i_out:
                Output complex current (A). Default: zero (no-load).

            ax:
                Axes to draw on. Uses the current axes if not provided.

        Returns:
            The axes and the array of load-side voltage magnitudes (V).
        """
        import matplotlib.pyplot as plt

        if ax is None:
            ax = plt.gca()

        u_ref = float(u_ref)
        u_ref_v = u_ref * self._un  # convert p.u. → V for the voltage axis
        scale, unit = (1e-3, "kV") if u_ref_v > 1000 else (1.0, "V")

        voltages = np.asarray(voltages, dtype=float)
        cy_element = self._create_cy_element(u_ref=u_ref)
        u_out = np.array([abs(self._compute_voltage(u_in=u, i_out=i_out, cy_element=cy_element)) for u in voltages])

        ax.scatter(voltages * scale, u_out * scale, color="steelblue", marker=".", s=20, label="Output voltage")
        ax.scatter(voltages * scale, voltages * scale, color="gray", marker=".", s=5, label="No regulation ($a = 1$)")
        ax.axhline(
            y=u_ref_v * scale,
            color="green",
            linestyle="--",
            linewidth=1,
            label=f"$u_{{ref}}$ = {u_ref_v * scale:.3g} {unit}",
        )
        ax.grid(visible=True)
        ax.set_xlabel(f"Source-side voltage ({unit})")
        ax.set_ylabel(f"Load-side voltage ({unit})")
        ax.legend()

        return ax, u_out

    def _to_dict(self, include_results: bool) -> JsonDict:
        return {
            "id": self.id,
            "sn": self._sn,
            "un": self._un,
            "z2": [self._z2.real, self._z2.imag],
            "ym": [self._ym.real, self._ym.imag],
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
            u_range=data["u_range"],
            alpha=data["alpha"],
        )
