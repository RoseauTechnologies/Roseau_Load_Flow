import logging
from enum import Enum, auto, unique

import pandas as pd
from typing_extensions import Self

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


@unique
class LineType(Enum):
    """The type of a line."""

    OVERHEAD = auto()
    """The line is an overhead line."""
    UNDERGROUND = auto()
    """The line is an underground line."""
    TWISTED = auto()
    """The line is a twisted line."""

    def __str__(self) -> str:
        """Print a `LineType`

        Returns:
             A printable string of the line type.
        """
        return self.name.lower()

    @classmethod
    def from_string(cls, string: str) -> Self:
        """Convert a string into a LineType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding LineType.
        """
        string = string.lower()
        if string in ("overhead", "aérien", "aerien", "galerie", "a", "o"):
            return cls.OVERHEAD
        elif string in ("underground", "souterrain", "sous-marin", "s", "u"):
            return cls.UNDERGROUND
        elif string in ("twisted", "torsadé", "torsade", "t"):
            return cls.TWISTED
        else:
            msg = f"The string {string!r} cannot be converted into a LineType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)

    #
    # WordingCodeMixin
    #
    def code(self) -> str:
        """The code method is modified to retrieve a code that can be used in line type names.

        Returns:
            The code of the enumerated value.
        """
        if self == LineType.OVERHEAD:
            return "O"
        elif self == LineType.UNDERGROUND:
            return "U"
        elif self == LineType.TWISTED:
            return "T"
        else:  # pragma: no cover
            msg = f"There is code missing here. I do not know the LineType {self!r}."
            logger.error(msg)
            raise NotImplementedError(msg)


# Add the list of codes for each line type
LineType.CODES = {LineType.OVERHEAD: {"A", "O"}, LineType.UNDERGROUND: {"U", "S"}, LineType.TWISTED: {"T"}}


@unique
class ConductorType(Enum):
    """The type of conductor."""

    AL = auto()
    """The conductor is in Aluminium."""
    CU = auto()
    """The conductor is in Copper."""
    AM = auto()
    """The conductor is in Almélec."""
    AA = auto()
    """The conductor is in Alu-Acier."""
    LA = auto()
    """The conductor is in Almélec-Acier."""

    def __str__(self) -> str:
        """Print a `ConductorType`

        Returns:
            A printable string of the conductor type.
        """
        if self == ConductorType.AL:
            return "Al"
        elif self == ConductorType.CU:
            return "Cu"
        elif self == ConductorType.AM:
            return "AM"
        elif self == ConductorType.AA:
            return "AA"
        elif self == ConductorType.LA:
            return "LA"
        else:
            s = super().__str__()
            msg = f"The ConductorType {s} is not known..."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE)

    @classmethod
    def from_string(cls, string: str) -> Self:
        """Convert a string into a ConductorType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding ConductorType.
        """
        string = string.lower()
        if string == "al":
            return cls.AL
        elif string == "cu":
            return cls.CU
        elif string == "am":
            return cls.AM
        elif string == "aa":
            return cls.AA
        elif string == "la":
            return cls.LA
        else:
            msg = f"The string {string!r} cannot be converted into a ConductorType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE)

    #
    # WordingCodeMixin
    #
    def code(self) -> str:
        """The code method is modified to retrieve a code that can be used in line type names.

        Returns:
            The code of the enumerated value.
        """
        return self.name.upper()


@unique
class InsulatorType(Enum):
    """The type of the insulator for a wire."""

    UNKNOWN = auto()
    """The insulator of the conductor is made with unknown material."""
    HDPE = auto()
    """The insulator of the conductor is made with High-Density PolyEthylene."""
    LDPE = auto()
    """The insulator of the conductor is made with Low-Density PolyEthylene."""
    PEX = auto()
    """The insulator of the conductor is made with Cross-linked polyethylene."""
    EPR = auto()
    """The insulator of the conductor is made with Ethylene-Propylene Rubber."""
    PVC = auto()
    """The insulator of the conductor is made with PolyVinyl Chloride."""

    def __str__(self) -> str:
        """Print a `InsulatorType`

        Returns:
            A printable string of the insulator type.
        """
        return self.name.upper()

    @classmethod
    def from_string(cls, string: str) -> Self:
        """Convert a string into a InsulatorType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding InsulatorType.
        """
        if string.lower() in ("", "unknown", "nan"):
            return cls.UNKNOWN
        elif string == "HDPE":
            return cls.HDPE
        elif string == "LDPE":
            return cls.LDPE
        elif string == "PEX":
            return cls.PEX
        elif string == "EPR":
            return cls.EPR
        elif string == "PVC":
            return cls.PVC
        else:
            msg = f"The string {string!r} cannot be converted into a InsulatorType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_INSULATOR_TYPE)
