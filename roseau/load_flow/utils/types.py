import logging
from enum import Enum, auto, unique
from typing import Optional

import regex

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Self

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


@unique
class LineModel(Enum):
    """An enumerated class for the different line models."""

    UNKNOWN = auto()
    """The line is modelled through an unknown model."""
    LV_EXACT = auto()
    """The line is modelled through the position of the wire (with neutral). Some hypothesis limit this model to
            low voltages lines."""
    SYM = auto()
    """The line is modelled using a symmetric model (without neutral)."""
    SYM_NEUTRAL = auto()
    """The line is modelled  using a symmetric model (with neutral)."""
    ZY = auto()
    """The line is modelled using two 3x3 matrices (shunt admittance and line impedance, without neutral)."""
    ZY_NEUTRAL = auto()
    """The line is modelled using two 4x4 matrices (shunt admittance and line impedance, with neutral)."""
    Z = auto()
    """The line is modelled using a single 3x3 matrices (line impedance, without neutral)."""
    Z_NEUTRAL = auto()
    """The line is modelled using a single 4x4 matrices (line impedance, with neutral)."""

    def __str__(self) -> str:
        """Print a `LineModel`

        Returns:
            A printable string of the names of line model.
        """
        return self.name.lower()

    @classmethod
    def from_string(cls, string: str) -> Self:
        """Convert a string into a LineModel

        Args:
            string:
                The string to convert

        Returns:
            The corresponding LineModel.
        """
        string = string.lower()
        if string == "lv_exact":
            return cls.LV_EXACT
        elif string == "sym":
            return cls.SYM
        elif string == "sym_neutral":
            return cls.SYM_NEUTRAL
        elif string == "zy":
            return cls.ZY
        elif string == "zy_neutral":
            return cls.ZY_NEUTRAL
        elif string == "z":
            return cls.Z
        elif string == "z_neutral":
            return cls.Z_NEUTRAL
        elif string in ("", "nan", "unknown"):
            return cls.UNKNOWN
        else:
            msg = f"The string {string!r} cannot be converted into a LineModel."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)

    @classmethod
    def with_neutral(cls) -> tuple["LineModel", ...]:
        """Give the tuple of the line models which support the neutral.

        Returns:
            The tuple of line models which support the neutral.
        """
        return cls.SYM_NEUTRAL, cls.Z_NEUTRAL, cls.ZY_NEUTRAL, cls.LV_EXACT

    @classmethod
    def without_neutral(cls) -> tuple["LineModel", ...]:
        """Give the tuple of the line models which do not support the neutral.

        Returns:
            The tuple of line models which do not support the neutral.
        """
        return cls.SYM, cls.Z, cls.ZY

    @classmethod
    def with_shunt(cls) -> tuple["LineModel", ...]:
        """Give the tuple of the line models which support the shunt.

        Returns:
            The tuple of line models which supports the shunt.
        """
        return cls.LV_EXACT, cls.SYM, cls.SYM_NEUTRAL, cls.ZY, cls.ZY_NEUTRAL

    @classmethod
    def without_shunt(cls) -> tuple["LineModel", ...]:
        """Give the tuple of the line models which do not support the shunt.

        Returns:
            The tuple of line models which do not support the shunt.
        """
        return cls.Z_NEUTRAL, cls.Z


@unique
class BranchType(Enum):
    """The type of 'line' in a network."""

    LINE = auto()
    """The branch is a regular line."""
    TRANSFORMER = auto()
    """The branch is a regular transformer."""
    SWITCH = auto()
    """The branch is a regular switch."""

    def __str__(self) -> str:
        """Print a `BranchType`.

        Returns:
            A printable string of the connection type.
        """
        return self.name.lower()

    @classmethod
    def from_string(cls, string: str) -> Self:
        """Convert a string into a ConnectionType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding ConnectionType.
        """
        if string == "line":
            return cls.LINE
        elif string == "transformer":
            return cls.TRANSFORMER
        elif string == "switch":
            return cls.SWITCH
        else:
            msg = f"The string {string!r} cannot be converted into a BranchType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)


EXTRACT_WINDINGS_RE = regex.compile(
    "(?(DEFINE)(?P<y_winding>yn?)(?P<d_winding>d)(?P<z_winding>zn?)(?P<p_set_1>[06])"
    "(?P<p_set_2>5|11))"
    ""
    "(?|(?P<w1>(?&y_winding))(?P<w2>(?&y_winding))(?P<p>(?&p_set_1)?)"  # yy
    "|(?P<w1>(?&y_winding))(?P<w2>(?&d_winding))(?P<p>(?&p_set_2)?)"  # yd
    "|(?P<w1>(?&y_winding))(?P<w2>(?&z_winding))(?P<p>(?&p_set_2)?)"  # yz
    "|(?P<w1>(?&d_winding))(?P<w2>(?&z_winding))(?P<p>(?&p_set_1)?)"  # dz
    "|(?P<w1>(?&d_winding))(?P<w2>(?&y_winding))(?P<p>(?&p_set_2)?)"  # dy
    "|(?P<w1>(?&d_winding))(?P<w2>(?&d_winding))(?P<p>(?&p_set_1)?))",  # dd
    regex.IGNORECASE,
)
"""The pattern to extract the winding of the primary and of the secondary of the transformer."""


@unique
class TransformerType(Enum):
    """The type of transformer."""

    Yy = auto()
    """A Wye-Wye transformer without neutral connected to the rest of the network."""
    YNy = auto()
    """A Wye-Wye transformer with a neutral connected to the network on the first winding."""
    YNyn = auto()
    """A Wye-Wye transformer with a neutral connected to the network on the two windings."""
    Yyn = auto()
    """A Wye-Wye transformer with a neutral connected to the network on the second winding."""
    Dz = auto()
    """A Delta-Zigzag transformer without neutral connected to the rest of the network."""
    Dzn = auto()
    """A Delta-Zigzag transformer with a neutral connected to the network on the second winding."""
    Dy = auto()
    """A Delta-Wye transformer without neutral connected to the rest of the network."""
    Dyn = auto()
    """A Delta-Wye transformer with a neutral connected to the network on the second winding."""
    Yz = auto()
    """A Wye-Zigzag transformer without neutral connected to the rest of the network."""
    YNz = auto()
    """A Wye-Zigzag transformer with a neutral connected to the network on the first winding."""
    YNzn = auto()
    """A Wye-Zigzag transformer with a neutral connected to the network on the two windings."""
    Yzn = auto()
    """A Wye-Zigzag transformer with a neutral connected to the network on the second winding."""
    Yd = auto()
    """A Wye-Delta transformer without neutral connected to the rest of the network."""
    YNd = auto()
    """A Wye-Delta transformer with a neutral connected to the network on the first winding."""
    Dd = auto()
    """A Delta-Delta transformer without neutral connected to the rest of the network."""

    def __str__(self) -> str:
        """Print a `TransformerType`

        Returns:
            A printable string of the transformer type.
        """
        return self.name

    @classmethod
    def from_string(cls, string: str) -> Self:
        """Convert a string into a TransformerType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding TransformerType
        """
        winding1, winding2, phase_displacement = cls.extract_windings(string=string)
        try:
            return getattr(cls, f"{winding1}{winding2}")
        except AttributeError:
            msg = f"The string {string!r} cannot be converted into a TransformerType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE) from None

    @property
    def windings(self) -> tuple[str, str]:
        """Retrieve the windings and the phase displacement of the current

        Returns:
            The high voltages winding and the low voltages winding.
        """
        winding1, winding2, phase_displacement = self.extract_windings(str(self))
        return winding1, winding2

    @classmethod
    def validate_windings(cls, string: str) -> bool:
        """Validate the windings of the high and low voltages sides

        Args:
            string:
                A string depicting a winding

        Returns:
            True if the provided string corresponds to valid transformer windings.
        """
        try:
            match = EXTRACT_WINDINGS_RE.fullmatch(string=string)
            return bool(match) and bool(match.group("p"))
        except Exception:
            return False

    @classmethod
    def extract_windings(cls, string: str) -> tuple[str, str, Optional[int]]:
        """Extract the windings of the high and low voltages sides

        Args:
            string:
                A string depicting a winding

        Returns:
            The high voltages winding, the low voltages winding, and the phase displacement.
        """
        match = EXTRACT_WINDINGS_RE.fullmatch(string=string)
        if match:
            groups = match.groupdict()
            winding1, winding2, phase_displacement = groups["w1"], groups["w2"], groups["p"]
            if phase_displacement:
                return winding1.upper(), winding2.lower(), int(phase_displacement)
            else:
                return winding1.upper(), winding2.lower(), None
        else:
            msg = f"Transformer windings cannot be extracted from the string {string!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
