import logging
from typing import NoReturn

import numpy as np
import regex
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import Identifiable, JsonMixin

logger = logging.getLogger(__name__)


class TransformerParameters(Identifiable, JsonMixin):
    """A class to store the parameters of the transformers.

    See Also:
        `Transformer parameters documentation <../../../models/Transformer/index.html#transformer-parameters>`_
    """

    _EXTRACT_WINDINGS_RE = regex.compile(
        "(?(DEFINE)(?P<y_winding>yn?)(?P<d_winding>d)(?P<z_winding>zn?)(?P<p_set_1>[06])"
        "(?P<p_set_2>5|11))"
        ""
        "(?|(?P<w1>(?&y_winding))(?P<w2>(?&y_winding))(?P<p>(?&p_set_1))"  # yy
        "|(?P<w1>(?&y_winding))(?P<w2>(?&d_winding))(?P<p>(?&p_set_2))"  # yd
        "|(?P<w1>(?&y_winding))(?P<w2>(?&z_winding))(?P<p>(?&p_set_2))"  # yz
        "|(?P<w1>(?&d_winding))(?P<w2>(?&z_winding))(?P<p>(?&p_set_1))"  # dz
        "|(?P<w1>(?&d_winding))(?P<w2>(?&y_winding))(?P<p>(?&p_set_2))"  # dy
        "|(?P<w1>(?&d_winding))(?P<w2>(?&d_winding))(?P<p>(?&p_set_1)))",  # dd
        regex.IGNORECASE,
    )
    """The pattern to extract the winding of the primary and of the secondary of the transformer."""

    @ureg_wraps(None, (None, None, None, "V", "V", "VA", "W", "", "W", ""), strict=False)
    def __init__(
        self,
        id: Id,
        type: str,
        uhv: float,
        ulv: float,
        sn: float,
        p0: float,
        i0: float,
        psc: float,
        vsc: float,
    ) -> None:
        """TransformerParameters constructor.

        Args:
            id:
                A unique ID of the transformer parameters, typically its canonical name.

            type:
                The type of transformer parameters. It can be "single" for single-phase transformers, "split" for
                split-phase transformers, or the name of the windings such as "Dyn11" for three-phase transformers.
                Allowed windings are "D" for delta, "Y" for wye (star), and "Z" for zigzag.

            uhv:
                Phase-to-phase nominal voltages of the high voltages side (V)

            ulv:
                Phase-to-phase nominal voltages of the low voltages side (V)

            sn:
                The nominal power of the transformer (VA)

            p0:
                Losses during off-load test (W)

            i0:
                Current during off-load test (%)

            psc:
                Losses during short circuit test (W)

            vsc:
                Voltages on LV side during short circuit test (%)
        """
        super().__init__(id)
        self._sn = sn
        self._uhv = uhv
        self._ulv = ulv
        self._i0 = i0
        self._p0 = p0
        self._psc = psc
        self._vsc = vsc
        self.type = type
        if type in ("single", "split"):
            self.winding1 = None
            self.winding2 = None
            self.phase_displacement = None
        else:
            self.winding1, self.winding2, self.phase_displacement = self.extract_windings(string=type)

        # Check
        if uhv <= ulv:
            msg = (
                f"Transformer type {id!r} has the low voltages higher than the high voltages: "
                f"uhv={uhv:.2f} V and ulv={ulv:.2f} V."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES)
        if i0 > 1.0 or i0 < 0.0:
            msg = (
                f"Transformer type {id!r} has the 'current during off-load test' i0={i0}. It is a "
                f"percentage that should be between 0 and 1."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if vsc > 1.0 or vsc < 0.0:
            msg = (
                f"Transformer type {id!r} has the 'voltages on LV side during short circuit test' "
                f"vsc={vsc}. It is a percentage that should be between 0 and 1."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if psc / sn > vsc:
            msg = (
                f"Transformer type {id!r} has parameters that can't be modeled. The following inequality should be "
                f"respected: psc/sn <= vsc"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if i0 * sn < p0:
            logger.warning(
                f"Transformer type {id!r} doesn't respect the inequality: i0 * sn > p0. The magnetizing admittance "
                f"imaginary part will be null."
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransformerParameters):
            return NotImplemented
        else:
            return (
                self.id == other.id
                and self.type == other.type
                and np.isclose(self._sn, other._sn)
                and np.isclose(self._p0, other._p0)
                and np.isclose(self._i0, other._i0)
                and np.isclose(self._uhv, other._uhv)
                and np.isclose(self._ulv, other._ulv)
                and np.isclose(self._psc, other._psc)
                and np.isclose(self._vsc, other._vsc)
            )

    @property
    @ureg_wraps("V", (None,), strict=False)
    def uhv(self) -> Q_[float]:
        """Phase-to-phase nominal voltages of the high voltages side (V)"""
        return self._uhv

    @property
    @ureg_wraps("V", (None,), strict=False)
    def ulv(self) -> Q_[float]:
        """Phase-to-phase nominal voltages of the low voltages side (V)"""
        return self._ulv

    @property
    @ureg_wraps("VA", (None,), strict=False)
    def sn(self) -> Q_[float]:
        """The nominal power of the transformer (VA)"""
        return self._sn

    @property
    @ureg_wraps("W", (None,), strict=False)
    def p0(self) -> Q_[float]:
        """Losses during off-load test (W)"""
        return self._p0

    @property
    @ureg_wraps("", (None,), strict=False)
    def i0(self) -> Q_[float]:
        """Current during off-load test (%)"""
        return self._i0

    @property
    @ureg_wraps("W", (None,), strict=False)
    def psc(self) -> Q_[float]:
        """Losses during short circuit test (W)"""
        return self._psc

    @property
    @ureg_wraps("", (None,), strict=False)
    def vsc(self) -> Q_[float]:
        """Voltages on LV side during short circuit test (%)"""
        return self._vsc

    @classmethod
    def from_name(cls, name: str, type: str) -> Self:
        """Construct TransformerParameters from name and types.

        Args:
            name:
                The name of the transformer parameters, such as `"160kVA"` or `"H61_50kVA"`.

            type:
                The type of transformer parameters such as "Dyn11", "single", "split".

        Returns:
            The constructed transformer parameters.
        """
        if name == "H61_50kVA":
            return cls(id=name, type=type, uhv=20000, ulv=400, sn=50 * 1e3, p0=145, i0=1.8 / 100, psc=1350, vsc=4 / 100)
        elif name[-3:] == "kVA":
            try:
                sn = float(name[:-3])
            except ValueError:
                msg = f"The transformer type name does not follow the syntax rule. {name!r} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX) from None
            else:
                return cls(name, type, 20000, 400, sn * 1e3, 460, 2.3 / 100, 2350, 4 / 100)
        else:
            msg = f"The transformer type name does not follow the syntax rule. {name!r} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX)

    @ureg_wraps(("ohm", "S", "", None), (None,), strict=False)
    def to_zyk(self) -> tuple[Q_[complex], Q_[complex], Q_[float], float]:
        """Compute the transformer parameters ``z2``, ``ym``, ``k`` and ``orientation`` mandatory
        for some models.

        Where:
            * ``z2``: The series impedance of the transformer (Ohms).
            * ``ym``: The magnetizing admittance of the transformer (Siemens).
            * ``k``: The transformation ratio.
            * ``orientation``: 1 for direct winding, -1 for reverse winding.

        Returns:
            The parameters (``z2``, ``ym``, ``k``, ``orientation``).
        """
        # Off-load test
        # Iron losses resistance (Ohm)
        r_iron = self._uhv**2 / self._p0
        # Magnetizing inductance (Henry) * omega (rad/s)
        if self._i0 * self._sn > self._p0:
            lm_omega = self._uhv**2 / (np.sqrt((self._i0 * self._sn) ** 2 - self._p0**2))
            ym = 1 / r_iron + 1 / (1j * lm_omega)
        else:
            ym = 1 / r_iron

        # Short circuit test
        r2 = self._psc * (self._ulv / self._sn) ** 2
        l2_omega = np.sqrt((self._vsc * self._ulv**2 / self._sn) ** 2 - r2**2)
        z2 = r2 + 1j * l2_omega

        # Change the voltages if the reference voltages is phase to neutral
        uhv = self._uhv
        ulv = self._ulv
        if self.type == "single" or self.type == "split":
            orientation = 1.0
        else:
            # Extract the windings of the primary and the secondary of the transformer
            if self.winding1[0] in ("y", "Y"):
                uhv /= np.sqrt(3.0)
            if self.winding2[0] in ("y", "Y"):
                ulv /= np.sqrt(3.0)
            if self.winding1[0] in ("z", "Z"):
                uhv /= 3.0
            if self.winding2[0] in ("z", "Z"):
                ulv /= 3.0
            if self.phase_displacement in (0, 11):  # Normal winding
                orientation = 1.0
            else:  # Reverse winding
                assert self.phase_displacement in (5, 6)
                orientation = -1.0

        return z2, ym, ulv / uhv, orientation

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        return cls(
            id=data["id"],
            type=data["type"],  # Type of the transformer
            uhv=data["uhv"],  # Phase-to-phase nominal voltages of the high voltages side (V)
            ulv=data["ulv"],  # Phase-to-phase nominal voltages of the low voltages side (V)
            sn=data["sn"],
            p0=data["p0"],  # Losses during off-load test (W)
            i0=data["i0"],
            psc=data["psc"],  # Losses during short circuit test (W)
            vsc=data["vsc"],
        )

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "sn": self._sn,
            "uhv": self._uhv,
            "ulv": self._ulv,
            "i0": self._i0,
            "p0": self._p0,
            "psc": self._psc,
            "vsc": self._vsc,
            "type": self.type,
        }

    def _results_to_dict(self, warning: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    def results_from_dict(self, data: JsonDict) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to import."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    @classmethod
    def extract_windings(cls, string: str) -> tuple[str, str, int]:
        """Extract the windings and phase displacement from a given string

        Args:
            string:
                The string to parse.

        Returns:
            The first winding, the second winding, and the phase displacement
        """
        match = cls._EXTRACT_WINDINGS_RE.fullmatch(string=string)
        if match:
            groups = match.groupdict()
            winding1, winding2, phase_displacement = groups["w1"], groups["w2"], groups["p"]
            return winding1.upper(), winding2.lower(), int(phase_displacement)
        else:
            msg = f"Transformer windings cannot be extracted from the string {string!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
