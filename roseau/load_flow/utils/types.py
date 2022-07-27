import logging
from enum import auto, Enum, unique
from typing import Optional

import regex

from roseau.load_flow.utils.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

# The local logger
logger = logging.getLogger(__name__)


@unique
class LineType(Enum):
    """The type of a line.

    Attributes:
        LineType.UNKNOWN:
            The line is an unknown line.

        LineType.OVERHEAD:
            The line is an overhead line.

        LineType.UNDERGROUND:
            The line is an underground line.

        LineType.TWISTED:
            The line is a twisted line.
    """

    UNKNOWN = 0
    OVERHEAD = 1
    UNDERGROUND = 2
    TWISTED = 3

    def __str__(self) -> str:
        """Print a `LineType`

        Returns:
             A printable string of the line type.
        """
        return super().__str__().split(".", 1)[-1].lower()

    @classmethod
    def from_string(cls, string: str) -> "LineType":
        """Convert a string into a LineType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding LineType.
        """
        string = string.lower()
        if string in ("unknown", "", "nan"):
            return cls.UNKNOWN
        elif string in ("overhead", "aérien", "aerien", "galerie"):
            return cls.OVERHEAD
        elif string in ("underground", "souterrain", "sous-marin"):
            return cls.UNDERGROUND
        elif string in ("twisted", "torsadé", "torsade"):
            return cls.TWISTED
        else:
            msg = f"The string {string!r} can not be converted into a LineType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)


@unique
class ConductorType(Enum):
    """The type of conductor.

    Attributes:
        ConductorType.UNKNOWN:
            The conductor is made with unknown material.

        ConductorType.AL:
            The conductor is in Aluminium.

        ConductorType.CU:
            The conductor is in Copper.

        ConductorType.AM:
            The conductor is in Almélec.

        ConductorType.AA:
            The conductor is in Alu-Acier.

        ConductorType.LA:
            The conductor is in Almélec-Acier.
    """

    UNKNOWN = 0
    AL = 1
    CU = 2
    AM = 3
    AA = 4
    LA = 5

    def __str__(self) -> str:
        """Print a `ConductorType`

        Returns:
            A printable string of the conductor type.
        """
        if self == ConductorType.UNKNOWN:
            return "unknown"
        elif self == ConductorType.AL:
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
    def from_string(cls, string: str) -> "ConductorType":
        """Convert a string into a ConductorType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding ConductorType.
        """
        string = string.lower()
        if string in ("unknown", "", "nan"):
            return cls.UNKNOWN
        elif string == "al":
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
            msg = f"The string {string!r} can not be converted into a ConductorType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE)


@unique
class IsolationType(Enum):
    """The type of the isolation for a wire.

    Attributes:
        IsolationType.UNKNOWN:
            The isolation of the conductor is made with unknown material.

        IsolationType.HDPE:
            The isolation of the conductor is made with High-Density PolyEthylene.

        IsolationType.LDPE:
            The isolation of the conductor is made with Low-Density PolyEthylene.

        IsolationType.PEX:
            The isolation of the conductor is made with Cross-linked polyethylene.

        IsolationType.EPR:
            The isolation of the conductor is made with Ethylene-Propylene Rubber.

        IsolationType.PVC:
            The isolation of the conductor is made with PolyVinyl Chloride.
    """

    UNKNOWN = 0
    HDPE = 1
    LDPE = 2
    PEX = 3
    EPR = 4
    PVC = 5

    def __str__(self) -> str:
        """Print a `IsolationType`

        Returns:
            A printable string of the isolation type.
        """
        return super().__str__().split(".", 1)[-1].upper()

    @classmethod
    def from_string(cls, string: str) -> "IsolationType":
        """Convert a string into a IsolationType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding IsolationType.
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
            msg = f"The string {string!r} can not be converted into a IsolationType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ISOLATION_TYPE)


@unique
class LineModel(Enum):
    """An enumerated class for the different line models

    Attributes:
        LineModel.UNKNOWN:
            The line is modelled through an unknown model.

        LineModel.LV_EXACT:
            The line is modelled through the position of the wire (with neutral). Some hypothesis limit this model to
            low voltages lines.

        LineModel.SYM:
            The line is modelled using a symmetric model (without neutral).

        LineModel.SYM_NEUTRAL:
            The line is modelled  using a symmetric model (with neutral).

        LineModel.ZY:
            The line is modelled using two 3x3 matrices (shunt admittance and line impedance, without neutral).

        LineModel.ZY_NEUTRAL:
            The line is modelled using two 4x4 matrices (shunt admittance and line impedance, with neutral).

        LineModel.Z:
            The line is modelled using a single 3x3 matrices (line impedance, without neutral).

        LineModel.Z_NEUTRAL:
            The line is modelled using a single 4x4 matrices (line impedance, with neutral).
    """

    UNKNOWN = 0
    LV_EXACT = 1
    SYM = 2
    SYM_NEUTRAL = 3
    ZY = 4
    ZY_NEUTRAL = 5
    Z = 6
    Z_NEUTRAL = 7

    def __str__(self) -> str:
        """Print a `LineModel`

        Returns:
            A printable string of the names of line model.
        """
        return super().__str__().split(".", 1)[-1].lower()

    @classmethod
    def from_string(cls, string: str) -> "LineModel":
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
            msg = f"The string {string!r} can not be converted into a LineModel."
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
    """The type of 'line' in a network.

    Attributes:
        BranchType.LINE:
            The branch is a regular line.

        BranchType.TRANSFORMER:
            The branch is a regular transformer.

        BranchType.SWITCH:
            The branch is a regular switch.
    """

    LINE = auto()
    TRANSFORMER = auto()
    SWITCH = auto()

    def __str__(self) -> str:
        """Print a `BranchType`.

        Returns:
            A printable string of the connection type.
        """
        return super().__str__().split(".", 1)[-1].lower()

    @classmethod
    def from_string(cls, string: str) -> "BranchType":
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
            msg = f"The string {string!r} can not be converted into a BranchType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)


EXTRACT_WINDINGS_RE: regex.Regex = regex.compile(
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
    """The type of transformer.

    Attributes:
        TransformerType.Yy:
            A Wye-Wye transformer without neutral connected to the rest of the network.

        TransformerType.YNy:
            A Wye-Wye transformer with a neutral connected to the network on the first winding.

        TransformerType.YNyn:
            A Wye-Wye transformer with a neutral connected to the network on the two windings.

        TransformerType.Yyn:
            A Wye-Wye transformer with a neutral connected to the network on the second winding.

        TransformerType.Dz:
            A Delta-Zigzag transformer without neutral connected to the rest of the network.

        TransformerType.Dzn:
            A Delta-Zigzag transformer with a neutral connected to the network on the second winding.

        TransformerType.Dy:
            A Delta-Wye transformer without neutral connected to the rest of the network.

        TransformerType.Dyn:
            A Delta-Wye transformer with a neutral connected to the network on the second winding.

        TransformerType.Yz:
            A Wye-Zigzag transformer without neutral connected to the rest of the network.

        TransformerType.YNz:
            A Wye-Zigzag transformer with a neutral connected to the network on the first winding.

        TransformerType.YNzn:
            A Wye-Zigzag transformer with a neutral connected to the network on the two windings.

        TransformerType.Yzn:
            A Wye-Zigzag transformer with a neutral connected to the network on the second winding.
    """

    Yy = auto()
    YNy = auto()
    YNyn = auto()
    Yyn = auto()
    Dz = auto()
    Dzn = auto()
    Dy = auto()
    Dyn = auto()
    Yz = auto()
    YNz = auto()
    YNzn = auto()
    Yzn = auto()
    Yd = auto()
    YNd = auto()
    Dd = auto()

    def __str__(self) -> str:
        """Print a `TransformerType`

        Returns:
            A printable string of the transformer type.
        """
        return super().__str__().split(".", 1)[-1]

    @classmethod
    def from_string(cls, string: str) -> "TransformerType":
        """Convert a string into a TransformerType

        Args:
            string:
                The string to convert

        Returns:
            The corresponding TransformerType
        """
        winding1, winding2, phase_displacement = TransformerType.extract_windings(string=string)
        try:
            return getattr(cls, f"{winding1}{winding2}")
        except AttributeError:
            msg = f"The string {string!r} can not be converted into a TransformerType."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE)

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
            match: regex.regex.Match = EXTRACT_WINDINGS_RE.fullmatch(string=string)
            return bool(match) and bool(match.group("p"))
        except RoseauLoadFlowException:
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
        match: regex.regex.Match = EXTRACT_WINDINGS_RE.fullmatch(string=string)
        if match:
            groups = match.groupdict()
            winding1, winding2, phase_displacement = groups["w1"], groups["w2"], groups["p"]
            if phase_displacement:
                return winding1.upper(), winding2.lower(), int(phase_displacement)
            else:
                return winding1.upper(), winding2.lower(), None
        else:
            msg = f"Transformer windings can not be extracted from the string {string!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
