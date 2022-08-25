import logging
from typing import Any

import numpy as np

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils import TransformerType, ureg

logger = logging.getLogger(__name__)


class TransformerCharacteristics:
    @ureg.wraps(None, (None, None, None, "V", "V", "VA", "W", None, "W", None), strict=False)
    def __init__(
        self,
        type_name: str,
        windings: str,
        uhv: float,
        ulv: float,
        sn: float,
        p0: float,
        i0: float,
        psc: float,
        vsc: float,
    ):
        """TransformerCharacteristics constructor.

        Args:
            type_name:
                The name of the transformer type

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
        self.type_name = type_name
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
                f"The transformer {type_name!r} has a high voltages lower or equal than the low voltages: uhv="
                f"{uhv:.2f} V and ulv={ulv:.2f} V"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES)

    @classmethod
    def from_dict(cls, characteristics: dict[str, Any]):
        """Dict constructor

        Args:
            characteristics:
                A dictionary of the characteristics of the transformer
        """
        type_name = characteristics["name"]
        sn = characteristics["sn"]
        uhv = characteristics["uhv"]  # Phase-to-phase nominal voltages of the high voltages side (V)
        ulv = characteristics["ulv"]  # Phase-to-phase nominal voltages of the low voltages side (V)
        i0 = characteristics["i0"]
        p0 = characteristics["p0"]  # Losses during off-load test (W)
        psc = characteristics["psc"]  # Losses during short circuit test (W)
        vsc = characteristics["vsc"]
        windings = characteristics["type"]  # Winding of the transformer

        return cls(type_name=type_name, windings=windings, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.type_name,
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
        """Compute the transformer characteristics z2, ym, k and orientation mandatory for some models

        Returns:
            * z2 The series impedance of the transformer (Ohms).
            * ym The magnetizing admittance of the transformer (Siemens).
            * k The transformation ratio
            * orientation 1 for direct winding, -1 for reverse winding
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
