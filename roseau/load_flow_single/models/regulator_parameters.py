import logging
from typing import Final, NoReturn, Self

from roseau.load_flow import SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.regulator_parameters import _RegulatorParametersMixin
from roseau.load_flow.typing import Complex, Float, Id, JsonDict, QtyOrMag
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import Identifiable, JsonMixin, pretty_unit
from roseau.load_flow_engine.cy_engine import CySingleVoltageRegulator

logger = logging.getLogger(__name__)


class RegulatorParameters(_RegulatorParametersMixin, Identifiable, JsonMixin):
    """Parameters that define the electrical model of a single-phase voltage regulator.

    A voltage regulator is modelled as an autotransformer whose tap ratio ``a`` keeps the load-side
    voltage at ``u_ref`` while ``a`` stays within ``[1 - u_range, 1 + u_range]``, and stays at its bound
    otherwise. The control law is the fixed point:

        a = softclamp(a · u_ref / |U_sec|, 1 - u_range, 1 + u_range)

    where ``softclamp`` is a clamp smoothed with softplus functions of steepness ``alpha``.

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
        alpha: Float = 1000.0,
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
                Steepness of the softplus functions smoothing the tap bounds: the corners of the
                characteristic are rounded over about ``1 / alpha`` in tap ratio. Must be positive.
                Defaults to 1000.
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
        """Steepness of the softplus functions smoothing the tap bounds."""
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

    def _create_cy_tap_calculator(self, u_ref: float) -> CySingleVoltageRegulator:
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
