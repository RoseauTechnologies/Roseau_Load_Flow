import logging
from enum import auto

from roseau.load_flow._compat import StrEnum
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

# The local logger
logger = logging.getLogger(__name__)


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


class Material(StrEnum):
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

    # Aliases
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
    def _missing_(cls, value: object) -> "Material":
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        msg = f"{value!r} cannot be converted into a Material."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_MATERIAL)

    def code(self) -> str:
        """A code that can be used in conductor type names."""
        return self.name


class Insulator(StrEnum):
    """The type of the insulator for a wire."""

    NONE = auto()
    """No insulation."""

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

    # Aliases
    PEX = XLPE
    """Alias -- Cross-linked polyethylene (XLPE) insulation."""
    PE = MDPE
    """Alias -- Medium-Density PolyEthylene (MDPE) insulation."""

    @classmethod
    def _missing_(cls, value: object) -> "Insulator":
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        msg = f"{value!r} cannot be converted into a Insulator."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_INSULATOR)

    def code(self) -> str:
        """A code that can be used in insulator type names."""
        return self.name
