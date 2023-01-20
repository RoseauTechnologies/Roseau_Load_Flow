import logging

import numpy as np

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict, Self
from roseau.load_flow.units import ureg
from roseau.load_flow.utils import Identifiable, JsonMixin, TransformerType

logger = logging.getLogger(__name__)


class TransformerParameters(Identifiable, JsonMixin):
    """A class to store the parameters of the transformers."""

    @ureg.wraps(None, (None, None, None, "V", "V", "VA", "W", None, "W", None), strict=False)
    def __init__(
        self,
        id: Id,
        windings: str,
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

            windings:
                The type of windings such as "Dyn11"

            uhv:
                Phase-to-phase nominal voltages of the high voltages side (V)

            ulv:
                Phase-to-phase nominal voltages of the low voltages side (V)

            sn:
                The nominal voltages of the transformer (VA)

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
        self.sn = sn
        self.uhv = uhv
        self.ulv = ulv
        self.i0 = i0
        self.p0 = p0
        self.psc = psc
        self.vsc = vsc
        self.windings = windings
        self.winding1, self.winding2, self.phase_displacement = TransformerType.extract_windings(string=windings)

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransformerParameters):
            return NotImplemented
        else:
            return (
                self.id == other.id
                and self.windings == other.windings
                and np.isclose(self.sn, other.sn)
                and np.isclose(self.p0, other.p0)
                and np.isclose(self.i0, other.i0)
                and np.isclose(self.uhv, other.uhv)
                and np.isclose(self.ulv, other.ulv)
                and np.isclose(self.psc, self.psc)
                and np.isclose(self.vsc, other.vsc)
            )

    @classmethod
    def from_name(cls, name: str, windings: str) -> Self:
        """Construct TransformerParameters from name and windings.

        Args:
            name:
                The name of the transformer parameters, such as `"160kVA"` or `"H61_50kVA"`.

            windings:
                The type of windings such as `"Dyn11"`.

        Returns:
            The constructed transformer parameters.
        """
        if name == "H61_50kVA":
            return cls(name, windings, 20000, 400, 50 * 1e3, 145, 1.8 / 100, 1350, 4 / 100)
        elif name[-3:] == "kVA":
            try:
                sn = float(name[:-3])
            except ValueError:
                msg = f"The transformer type name does not follow the syntax rule. {name!r} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX)
            else:
                return cls(name, windings, 20000, 400, sn * 1e3, 460, 2.3 / 100, 2350, 4 / 100)
        else:
            msg = f"The transformer type name does not follow the syntax rule. {name!r} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX)

    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        return cls(
            id=data["id"],
            windings=data["type"],  # Windings of the transformer
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
            "sn": self.sn,
            "uhv": self.uhv,
            "ulv": self.ulv,
            "i0": self.i0,
            "p0": self.p0,
            "psc": self.psc,
            "vsc": self.vsc,
            "type": self.windings,
        }

    def to_zyk(self) -> tuple[complex, complex, float, float]:
        """Compute the transformer parameters z2, ym, k and orientation mandatory for some models

        Returns:
            * ``z2``: The series impedance of the transformer (Ohms).
            * ``ym``: The magnetizing admittance of the transformer (Siemens).
            * ``k``: The transformation ratio.
            * orientation: 1 for direct winding, -1 for reverse winding.
        """
        # Extract the windings of the primary and the secondary of the transformer
        winding1, winding2, phase_displacement = TransformerType.extract_windings(self.windings)

        # Off-load test
        # Iron losses resistance (Ohm)
        r_iron = self.uhv**2 / self.p0
        # Magnetizing inductance (Henry) * omega (rad/s)
        if self.i0 * self.sn > self.p0:
            lm_omega = self.uhv**2 / (np.sqrt((self.i0 * self.sn) ** 2 - self.p0**2))
            ym = 1 / r_iron + 1 / (1j * lm_omega)
        else:
            ym = 1 / r_iron

        # Short circuit test
        r2 = self.psc * (self.ulv / self.sn) ** 2
        l2_omega = np.sqrt((self.vsc * self.ulv**2 / self.sn) ** 2 - r2**2)
        z2 = r2 + 1j * l2_omega

        # Change the voltages if the reference voltages is phase to neutral
        uhv = self.uhv
        ulv = self.ulv
        if winding1[0] in ("y", "Y"):
            uhv /= np.sqrt(3.0)
        if winding2[0] in ("y", "Y"):
            ulv /= np.sqrt(3.0)
        if winding1[0] in ("z", "Z"):
            uhv /= 3.0
        if winding2[0] in ("z", "Z"):
            ulv /= 3.0

        if phase_displacement in (5, 6):
            # Reverse winding
            return z2, ym, ulv / uhv, -1.0
        else:
            # Normal winding
            assert phase_displacement in (0, 11)
            return z2, ym, ulv / uhv, 1.0
