import logging
from enum import auto

from roseau.load_flow.utils import CaseInsensitiveStrEnum

# The local logger
logger = logging.getLogger(__name__)


class LineType(CaseInsensitiveStrEnum):
    """The type of a line."""

    OVERHEAD = auto()
    """An overhead line that can be vertically or horizontally configured -- Fr = Aérien."""
    UNDERGROUND = auto()
    """An underground or a submarine cable -- Fr = Souterrain/Sous-Marin."""
    TWISTED = auto()
    """A twisted line commonly known as Aerial Cable or Aerial Bundled Conductor (ABC) -- Fr = Torsadé."""

    # Short aliases
    O = OVERHEAD  # noqa: E741
    U = UNDERGROUND
    T = TWISTED

    # French aliases
    AERIEN = OVERHEAD  # Aérien
    A = OVERHEAD  # Aérien
    SOUTERRAIN = UNDERGROUND  # Souterrain
    S = UNDERGROUND  # Souterrain
    TORSADE = TWISTED  # Torsadé


class Material(CaseInsensitiveStrEnum):
    """The type of the material of the conductor."""

    # AAC:    1350-H19 (Standard Round of Compact Round)
    # AAC/TW: 1380-H19 (Trapezoidal Wire)
    # AAAC:   Aluminum alloy 6201-T81.
    # AAAC:   Concentric-lay-stranded
    # AAAC:   conforms to ASTM Specification B-399
    # AAAC:   Applications: Overhead
    # ACSR:   Aluminum alloy 1350-H-19
    # ACSR:   Applications: Bare overhead transmission cable and primary and secondary distribution cable

    CU = auto()
    """Copper -- Fr = Cuivre."""
    AAC = auto()
    """All Aluminum Conductor (AAC) -- Fr = Aluminium (AL)."""
    AAAC = auto()
    """All Aluminum Alloy Conductor (AAAC) -- Fr = Almélec (AM, AMC)."""
    ACSR = auto()
    """Aluminum Conductor Steel Reinforced (ACSR) -- Fr = Alu-Acier (AA)."""
    AACSR = auto()
    """Aluminum Alloy Conductor Steel Reinforced (AACSR) -- Fr = Almélec-Acier (LA)."""

    # French aliases
    CUC = CU  # Cuivre Câble
    CUF = CU  # Cuivre Fil
    AL = AAC  # Aluminium
    AM = AAAC  # Almélec
    AMC = AAAC  # Almélec
    AA = ACSR  # Aluminium Acier
    AR = ACSR  # Aluminium Acier Renforcé
    LA = AACSR  # Almélec Acier
    LR = AACSR  # Almélec Acier Renforcé


class Insulator(CaseInsensitiveStrEnum):
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

    # French aliases
    PEX = XLPE
    PE = MDPE


class TransformerCooling(CaseInsensitiveStrEnum):
    """IEC Designations and Descriptions of the Cooling Classes Used in Power Transformers."""

    # TODO add to the catalogue

    ONAN = auto()
    """Oil Natural/Air Natural.

    Oil-air (self-cooled).

    Previous designation (1993): OA or ONS
    """
    ONAF = auto()
    """Oil Natural/Air Forced, Forced-air

    Previous designation (1993): FA or ONF
    """
    ONAN_ONAF_ONAF = auto()
    """Oil Natural Air Natural/Oil Natural Air Forced/Oil Natural Air Forced.

    Oil-air (self-cooled), followed by two stages of forced-air cooling (fans).

    Previous designation (1993): OA/FA/FA
    """
    ONAN_ONAF_OFAF = auto()
    """Oil Natural Air Natural/Oil Natural Air Forced/Oil Forced Air Forced.

    Oil-air (self-cooled), followed by one stage of forced-air cooling (fans), followed by 1 stage
    of forced oil (oil pumps).

    Previous designation (1993): OA/FA/FOA
    """
    ONAF_ODAF = auto()
    """Oil Natural Air Forced/Oil Direct Air Forced.

    Oil-air (self-cooled), followed by one stage of directed oil flow pumps (with fans).

    Previous designation (1993): OA/FOA
    """
    ONAF_ODAF_ODAF = auto()
    """Oil Natural Air Forced/Oil Direct Air Forced/Oil Direct Air Forced.

    Oil-air (self-cooled), followed by two stages of directed oil flow pumps (with fans).

    Previous designation (1993): OA/FOA/FOA
    """
    OFAF = auto()
    """Oil Forced Air Forced.

    Forced oil/air (with fans) rating only -- no self-cooled rating.

    Previous designation (1993): FOA
    """
    OFWF = auto()
    """Oil Forced Water Forced.

    Forced oil/water cooled rating only (oil/water heat exchanger with oil and water pumps) -- no
    self-cooled rating.

    Previous designation (1993): FOW
    """
    ODAF = auto()
    """Oil Direct Air Forced

    Forced oil/air cooled rating only with directed oil flow pumps and fans -- no self-cooled rating.

    Previous designation (1993): FOA
    """
    ODWF = auto()
    """Oil Direct Water Forced

    Forced oil/water cooled rating only (oil/water heat exchanger with directed oil flow pumps and
    water pumps) --  no self-cooled rating.

    Previous designation (1993): FOW
    """
