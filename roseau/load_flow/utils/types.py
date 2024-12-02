import logging
from enum import auto
from typing import Final

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
LoadTypeDtype = pd.CategoricalDtype(categories=["power", "current", "impedance"], ordered=True)
"""Categorical data type used for load types."""
SequenceDtype = pd.CategoricalDtype(categories=["zero", "pos", "neg"], ordered=True)
"""Categorical data type used for symmetrical components."""
_DTYPES: Final = {
    "bus_id": object,
    "branch_id": object,
    "transformer_id": object,
    "line_id": object,
    "switch_id": object,
    "load_id": object,
    "source_id": object,
    "ground_id": object,
    "potential_ref_id": object,
    "type": object,
    "phase": PhaseDtype,
    "current": complex,
    "current1": complex,
    "current2": complex,
    "power": complex,
    "flexible_power": complex,
    "power1": complex,
    "power2": complex,
    "potential": complex,
    "potential1": complex,
    "potential2": complex,
    "voltage": complex,
    "voltage1": complex,
    "voltage2": complex,
    "series_losses": complex,
    "shunt_losses": complex,
    "series_current": complex,
    "max_current": float,
    "loading": float,
    "max_loading": float,
    "sn": float,
    "ampacity": float,
    "voltage_level": float,
    "nominal_voltage": float,
    "min_voltage_level": float,
    "max_voltage_level": float,
    "violated": pd.BooleanDtype(),
    "flexible": pd.BooleanDtype(),
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
