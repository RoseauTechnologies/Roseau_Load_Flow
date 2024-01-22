import logging
from enum import auto

import pandas as pd

from roseau.load_flow._compat import StrEnum
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

# The local logger
logger = logging.getLogger(__name__)


# pandas dtypes used in the data frames
PhaseDtype = pd.CategoricalDtype(categories=["a", "b", "c", "n"], ordered=True)
"""Categorical data type used for the phase of potentials, currents, powers, etc."""
VoltagePhaseDtype = pd.CategoricalDtype(categories=["an", "bn", "cn", "ab", "bc", "ca"], ordered=True)
"""Categorical data type used for the phase of voltages and flexible powers only."""
BranchTypeDtype = pd.CategoricalDtype(categories=["line", "transformer", "switch"], ordered=True)
"""Categorical data type used for branch types."""
_DTYPES = {
    "bus_id": object,
    "branch_id": object,
    "transformer_id": object,
    "line_id": object,
    "switch_id": object,
    "load_id": object,
    "source_id": object,
    "ground_id": object,
    "potential_ref_id": object,
    "branch_type": BranchTypeDtype,
    "phase": PhaseDtype,
    "current": complex,
    "current1": complex,
    "current2": complex,
    "power": complex,
    "power1": complex,
    "power2": complex,
    "potential": complex,
    "potential1": complex,
    "potential2": complex,
    "voltage": complex,
    "voltage1": complex,
    "voltage2": complex,
    "max_power": float,
    "series_losses": complex,
    "shunt_losses": complex,
    "series_current": complex,
    "max_current": float,
    "min_voltage": float,
    "max_voltage": float,
    "violated": pd.BooleanDtype(),
}


class LineType(StrEnum):
    """The type of a line."""

    OVERHEAD = auto()
    """An overhead line that can be vertically or horizontally configured -- Fr = Aérien."""
    UNDERGROUND = auto()
    """An underground or a submarine cable -- Fr = Souterrain/Sous-Marin."""
    TWISTED = auto()
    """A twisted line commonly known as Aerial Cable or Aerial Bundled Conductor (ABC) -- Fr = Torsadé."""

    # aliases
    O = OVERHEAD  # noqa: E741
    U = UNDERGROUND
    T = TWISTED

    @classmethod
    def _missing_(cls, value: object) -> "LineType | None":
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        msg = f"{value!r} cannot be converted into a LineType."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)

    def code(self) -> str:
        """A code that can be used in line type names."""
        return self.name[0]


class ConductorType(StrEnum):
    """The type of the material of the conductor."""

    CU = auto()
    """Copper -- Fr = Cuivre."""
    AL = auto()
    """All Aluminum Conductor (AAC) -- Fr = Aluminium."""
    AM = auto()
    """All Aluminum Alloy Conductor (AAAC) -- Fr = Almélec."""
    AA = auto()
    """Aluminum Conductor Steel Reinforced (ACSR) -- Fr = Alu-Acier."""
    LA = auto()
    """Aluminum Alloy Conductor Steel Reinforced (AACSR) -- Fr = Almélec-Acier."""

    # aliases
    AAC = AL  # 1350-H19 (Standard Round of Compact Round)
    """All Aluminum Conductor (AAC) -- Fr = Aluminium."""
    # AAC/TW  # 1380-H19 (Trapezoidal Wire)

    AAAC = AM
    """All Aluminum Alloy Conductor (AAAC) -- Fr = Almélec."""
    # Aluminum alloy 6201-T81.
    # Concentric-lay-stranded
    # conforms to ASTM Specification B-399
    # Applications: Overhead

    ACSR = AA
    """Aluminum Conductor Steel Reinforced (ACSR) -- Fr = Alu-Acier."""
    # Aluminum alloy 1350-H-19
    # Applications: Bare overhead transmission cable and primary and secondary distribution cable

    AACSR = LA
    """Aluminum Alloy Conductor Steel Reinforced (AACSR) -- Fr = Almélec-Acier."""

    @classmethod
    def _missing_(cls, value: object) -> "ConductorType | None":
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        msg = f"{value!r} cannot be converted into a ConductorType."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE)

    def code(self) -> str:
        """A code that can be used in conductor type names."""
        return self.name


class InsulatorType(StrEnum):
    """The type of the insulator for a wire."""

    UNKNOWN = auto()
    """The material of the insulator is unknown."""

    # General insulators (IEC 60287)
    HDPE = auto()
    """High-Density PolyEthylene (HDPE) insulation."""
    MDPE = auto()
    """Medium-Density PolyEthylene (MDPE) insulation."""
    LDPE = auto()
    """Low-Density PolyEthylene (LDPE) insulation."""
    XLPE = auto()
    """Cross-linked polyethylene (XLPE) insulation."""
    EPR = auto()
    """Ethylene-Propylene Rubber (EPR) insulation."""
    PVC = auto()
    """PolyVinyl Chloride (PVC) insulation."""
    IP = auto()
    """Impregnated Paper (IP) insulation."""

    # Coiffier's insulators (French standards)
    SR = auto()  # IEC equivalent -> EPR
    """Synthétique HN-33S22 (Pr ou EP); équivalent à NF C 33-220. Diélectriques massifs extrudés."""
    SO = auto()  # IEC equivalent -> XLPE
    """SYNTHE. UTE C 33-223 (CABLE 2000). Polyéthylène réticulé."""
    SE = auto()  # IEC equivalent -> PVC
    """Synthétique HN-33S22 (Pe ou PVC); équivalent à NF C 33-220. Diélectriques massifs extrudés."""
    SC = auto()  # IEC equivalent -> XLPE
    """Synthétique NF C 33-223 SS Cablette. Polyéthylène réticulé."""
    S3 = auto()  # IEC equivalent -> XLPE
    """Synthétique HN-33S23 (PR); équivalent à NF C 33-223. Polyéthylène réticulé."""
    S6 = auto()  # IEC equivalent -> XLPE
    """Synthétique NF C 33-226. Polyethylène réticulé à gradient fixé."""
    PU = auto()  # IEC equivalent -> IP
    """Unipolar impregnated paper under lead -- Fr = Papier imprégné unipolaire sous plomb."""
    PP = auto()  # IEC equivalent -> IP
    """Tri-polar tri-lead metalized paper -- Fr = Papier métallisé tripolaire triplomb."""
    PM = auto()  # IEC equivalent -> IP
    """Tri-polar metallic paper radial field -- Fr = Papier métallisé tripolaire champ radial."""
    PC = auto()  # IEC equivalent -> IP
    """Tri-polar belt paper -- Fr = Papier ceinture tripolaire."""

    # Aliases
    PEX = XLPE
    """Alias -- Cross-linked polyethylene (XLPE) insulation."""
    PE = MDPE
    """Alias -- Medium-Density PolyEthylene (MDPE) insulation."""

    @classmethod
    def _missing_(cls, value: object) -> "InsulatorType | None":
        if isinstance(value, str):
            string = value.upper()
            if string in {"", "NAN"}:
                return cls.UNKNOWN
            try:
                return cls[string]
            except KeyError:
                pass
        msg = f"{value!r} cannot be converted into a InsulatorType."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_INSULATOR_TYPE)

    def code(self) -> str:
        """A code that can be used in insulator type names."""
        return self.name

    def is_compatible_with(self, model: str) -> bool:
        """A model that can be used in insulator type names."""
        if self == InsulatorType.UNKNOWN:
            return True
        elif self in {
            InsulatorType.HDPE,
            InsulatorType.MDPE,
            InsulatorType.LDPE,
            InsulatorType.XLPE,
            InsulatorType.EPR,
            InsulatorType.PVC,
            InsulatorType.IP,
        }:
            return model == "iec"
        elif self in {
            InsulatorType.SR,
            InsulatorType.SO,
            InsulatorType.SE,
            InsulatorType.SC,
            InsulatorType.S3,
            InsulatorType.S6,
            InsulatorType.PU,
            InsulatorType.PP,
            InsulatorType.PM,
            InsulatorType.PC,
        }:
            return model == "coiffier"
        else:
            raise NotImplementedError(f"InsulatorType {self} is not implemented.")
