"""Common types and enumerations."""

import logging
from enum import auto

from roseau.load_flow.utils.helpers import CaseInsensitiveStrEnum

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


class TransformerInsulation(CaseInsensitiveStrEnum):
    """The insulation technology of power transformers."""

    DRY_TYPE = "dry-type"
    """Dry-type transformer."""
    LIQUID_IMMERSED = "liquid-immersed"
    """Liquid-immersed transformer."""
    GAS_FILLED = "gas-filled"
    """Gas-filled transformer."""


class TransformerCooling(CaseInsensitiveStrEnum):
    """IEC designations and descriptions of the cooling classes used in power transformers.


    - Cooling class designations for liquid-immersed power transformers (IEC 60076-2):

      +----------+---------------------+--------+--------------------------------------------------+
      |          |                     | Letter | Description                                      |
      +==========+=====================+========+==================================================+
      | Internal | First Letter        | O      | Liquid with flash point ≤ 300°C                  |
      +          + (Cooling medium)    +--------+--------------------------------------------------+
      |          |                     | K      | Liquid with flash point > 300°C                  |
      +          +                     +--------+--------------------------------------------------+
      |          |                     | L      | Liquid with no measurable flash point            |
      +          +                     +--------+--------------------------------------------------+
      |          |                     | G      | Insulating gas (IEC 60076-15)                    |
      +          +---------------------+--------+--------------------------------------------------+
      |          | Second Letter       | N      | Natural convection through cooling equipment and |
      |          | (Cooling mechanism) |        | windings                                         |
      +          +                     +--------+--------------------------------------------------+
      |          |                     | F      | Forced circulation through cooling equipment,    |
      |          |                     |        | natural convection in windings                   |
      +          +                     +--------+--------------------------------------------------+
      |          |                     | D      | Forced circulation through cooling equipment,    |
      |          |                     |        | directed from the cooling equipment into at      |
      |          |                     |        | least the main windings                          |
      +----------+---------------------+--------+--------------------------------------------------+
      | External | Third letter        | A      | Air                                              |
      +          + (Cooling medium)    +--------+--------------------------------------------------+
      |          |                     | W      | Water                                            |
      +          +---------------------+--------+--------------------------------------------------+
      |          | Fourth Letter       | N      | Natural convection                               |
      +          + (Cooling mechanism) +--------+--------------------------------------------------+
      |          |                     | F      | Forced circulation (fans, air blowers, water     |
      |          |                     |        | pumps)                                           |
      +----------+---------------------+--------+--------------------------------------------------+

    - Cooling class designations for gas-filled power transformers (IEC 60076-15):

      Same as liquid-immersed transformers, but with the first letter always `G` (Insulating gas).

    - Cooling class designations for dry-type power transformers (IEC 60076-11):

      +---------------------+--------+-------------------------------------------------------------+
      |                     | Letter | Description                                                 |
      +=====================+========+=============================================================+
      | First Letter        | A      | Air                                                         |
      | (Cooling medium)    |        |                                                             |
      +---------------------+--------+-------------------------------------------------------------+
      | Second Letter       | N      | Natural convection                                          |
      + (Cooling mechanism) +--------+-------------------------------------------------------------+
      |                     | F      | Forced circulation                                          |
      +---------------------+--------+-------------------------------------------------------------+
    """

    # Liquid-immersed: Mineral oil
    ONAN = "ONAN"  # Previous designation (1993): OA or ONS
    """Oil Natural/Air Natural.

    Oil-air (self-cooled).
    """
    ONAF = "ONAF"  # Previous designation (1993): FA or ONF
    """Oil Natural/Air Forced, Forced-air."""
    ONAN_ONAF_ONAF = "ONAN/ONAF/ONAF"  # Previous designation (1993): OA/FA/FA
    """Oil Natural Air Natural/Oil Natural Air Forced/Oil Natural Air Forced.

    Oil-air (self-cooled), followed by two stages of forced-air cooling (fans).
    """
    ONAN_ONAF_OFAF = "ONAN/ONAF/OFAF"  # Previous designation (1993): OA/FA/FOA
    """Oil Natural Air Natural/Oil Natural Air Forced/Oil Forced Air Forced.

    Oil-air (self-cooled), followed by one stage of forced-air cooling (fans), followed by 1 stage
    of forced oil (oil pumps).
    """
    ONAN_ODAF = "ONAF/ODAF"  # Previous designation (1993): OA/FOA
    """Oil Natural Air Natural/Oil Direct Air Forced.

    Oil-air (self-cooled), followed by one stage of directed oil flow pumps (with fans).
    """
    ONAF_ODAF_ODAF = "ONAF/ODAF/ODAF"  # Previous designation (1993): OA/FOA/FOA
    """Oil Natural Air Forced/Oil Direct Air Forced/Oil Direct Air Forced.

    Oil-air (self-cooled), followed by two stages of directed oil flow pumps (with fans).
    """
    OFAF = "OFAF"  # Previous designation (1993): FOA
    """Oil Forced Air Forced.

    Forced oil/air (with fans) rating only -- no self-cooled rating.
    """
    OFWF = "OFWF"  # Previous designation (1993): FOW
    """Oil Forced Water Forced.

    Forced oil/water cooled rating only (oil/water heat exchanger with oil and water pumps) -- no
    self-cooled rating.
    """
    ODAF = "ODAF"  # Previous designation (1993): FOA
    """Oil Direct Air Forced

    Forced oil/air cooled rating only with directed oil flow pumps and fans -- no self-cooled rating.
    """
    ODWF = "ODWF"  # Previous designation (1993): FOW
    """Oil Direct Water Forced

    Forced oil/water cooled rating only (oil/water heat exchanger with directed oil flow pumps and
    water pumps) --  no self-cooled rating.
    """

    # Liquid-immersed: Non-mineral oil
    KNAN = "KNAN"
    """Less flammable liquid-immersed self-cooled."""
    KNAF = "KNAF"
    """Less flammable liquid-immersed forced-air-cooled."""
    KFAF = "KFAF"
    """Less flammable liquid-immersed forced-liquid-cooled (non-directed flow) with forced-air cooler."""
    KDAF = "KDAF"
    """Less flammable liquid-immersed forced-liquid-cooled (directed flow) with forced-air cooler."""
    KNWF = "KNWF"
    """Less flammable liquid-immersed self cooled with forced-water cooler."""
    KFWF = "KFWF"
    """Less flammable liquid-immersed forced-liquid-cooled (non-directed flow) with forced-water cooler."""
    KDWF = "KDWF"
    """Less flammable liquid-immersed forced-liquid-cooled (directed flow) with forced-water cooler."""

    # Liquid-immersed: Liquid with no measurable flash point (L)
    LNAN = "LNAN"
    """Liquid with no measurable flash point self-cooled."""
    LNAF = "LNAF"
    """Liquid with no measurable flash point forced-air-cooled."""
    # <<<< Add others on demand >>>>

    # Gas-filled
    GNAN = "GNAN"
    """Gas Natural/Air Natural."""
    GNAF = "GNAF"
    """Gas Natural/Air Forced."""
    GFAF = "GFAF"
    """Gas Forced/Air Forced."""
    GDAF = "GDAF"
    """Gas Direct/Air Forced."""
    GNWF = "GNWF"
    """Gas Natural/Water Forced."""
    GFWF = "GFWF"
    """Gas Forced/Water Forced."""

    # Dry-type
    AN = "AN"
    """Air Natural."""
    AF = "AF"
    """Air Forced."""
    AN_AF = "AN/AF"
    """Air Natural/Air Forced."""

    @property
    def type(self) -> TransformerInsulation:
        """The type of the transformer based on the cooling class."""
        if self.name.startswith(("O", "K", "L")):
            return TransformerInsulation.LIQUID_IMMERSED
        elif self.name.startswith("G"):
            return TransformerInsulation.GAS_FILLED
        elif self.name.startswith("A"):
            return TransformerInsulation.DRY_TYPE
        else:
            raise NotImplementedError(self)
