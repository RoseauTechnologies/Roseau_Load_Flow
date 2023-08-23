import logging
from enum import Enum, auto, unique

from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

# The local logger
logger = logging.getLogger(__name__)


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
            return "A"
        elif self == LineType.UNDERGROUND:
            return "S"
        elif self == LineType.TWISTED:
            return "T"
        else:  # pragma: no cover
            msg = f"There is code missing here. I do not know the LineType {self!r}."
            logger.error(msg)
            raise NotImplementedError(msg)


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
class InsulationType(Enum):
    """The type of the insulation for a wire."""

    UNKNOWN = auto()
    """The insulation of the conductor is made with unknown material."""
    HDPE = auto()
    """The insulation of the conductor is made with High-Density PolyEthylene."""
    LDPE = auto()
    """The insulation of the conductor is made with Low-Density PolyEthylene."""
    PEX = auto()
    """The insulation of the conductor is made with Cross-linked polyethylene."""
    EPR = auto()
    """The insulation of the conductor is made with Ethylene-Propylene Rubber."""
    PVC = auto()
    """The insulation of the conductor is made with PolyVinyl Chloride."""

    def __str__(self) -> str:
        """Print a `InsulationType`

        Returns:
            A printable string of the insulation type.
        """
        return self.name.upper()

    @classmethod
    def from_string(cls, string: str) -> Self:
        """Convert a string into a InsulationType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding InsulationType.
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
            msg = f"The string {string!r} cannot be converted into a InsulationType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_INSULATION_TYPE)
