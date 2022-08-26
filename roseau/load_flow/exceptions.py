import unicodedata
from enum import auto, Enum
from typing import Union


class RoseauLoadFlowExceptionCode(Enum):
    """An abstract class that will be used in every Roseau Packages."""

    # Generic
    BAD_GEOMETRY_TYPE = auto()

    # Buses
    DUPLICATE_BUS_ID = auto()
    BAD_BUS_TYPE = auto()
    BAD_POTENTIALS_SIZE = auto()
    BAD_VOLTAGES_SIZE = auto()

    # Branches
    DUPLICATE_BRANCH_ID = auto()
    BAD_BRANCH_TYPE = auto()
    BAD_Z_LINE_SHAPE = auto()
    BAD_Y_SHUNT_SHAPE = auto()
    BAD_LINE_MODEL = auto()
    BAD_LINE_TYPE = auto()
    BAD_CONDUCTOR_TYPE = auto()
    BAD_ISOLATION_TYPE = auto()
    BAD_Z_LINE_VALUE = auto()
    BAD_Y_SHUNT_VALUE = auto()
    BAD_TRANSFORMER_WINDINGS = auto()
    BAD_TRANSFORMER_TYPE = auto()
    BAD_TRANSFORMER_VOLTAGES = auto()
    BAD_TRANSFORMER_PARAMETERS = auto()
    BAD_TYPE_NAME_SYNTAX = auto()

    # Control
    BAD_CONTROL_TYPE = auto()

    # Load
    DUPLICATE_LOAD_ID = auto()
    BAD_LOAD_TYPE = auto()
    BAD_Y_SIZE = auto()
    BAD_Z_SIZE = auto()
    BAD_Z_VALUE = auto()
    BAD_S_SIZE = auto()
    BAD_S_VALUE = auto()
    BAD_PARAMETERS_SIZE = auto()

    # Network
    BAD_VOLTAGES_SOURCES_CONNECTION = auto()
    SWITCHES_LOOP = auto()
    NO_POTENTIAL_REFERENCE = auto()
    SEVERAL_POTENTIAL_REFERENCE = auto()
    UNKNOWN_ELEMENT = auto()
    NO_VOLTAGE_SOURCE = auto()
    BAD_ELEMENT_OBJECT = auto()
    DISCONNECTED_ELEMENT = auto()
    BAD_ELEMENT_ID = auto()
    NO_LOAD_FLOW_CONVERGENCE = auto()

    # DGS export
    DGS_BAD_PHASE_TECHNOLOGY = auto()
    DGS_BAD_PHASE_NUMBER = auto()

    # JSON export
    JSON_LINE_CHARACTERISTICS_DUPLICATES = auto()
    JSON_TRANSFORMER_CHARACTERISTICS_DUPLICATES = auto()

    @classmethod
    @property
    def package_name(cls) -> str:
        return "roseau.load_flow"

    def __str__(self) -> str:
        return f"{self.package_name}.{self.name}".lower()

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return other.lower() == str(self).lower()
        return super().__eq__(other)

    @classmethod
    def from_string(cls, string: Union[str, "RoseauLoadFlowExceptionCode"]) -> "RoseauLoadFlowExceptionCode":
        """A method to convert a string into an error code enumerated type.

        Args:
            string:
                The string depicted the error code. If a good element is given

        Returns:
            The enumerated type value corresponding with `string`.
        """
        if isinstance(string, cls):
            return string
        elif isinstance(string, str):
            pass
        else:
            string = str(string)

        # Withdraw accents and make lowercase
        string = unicodedata.normalize("NFKD", string.lower()).encode("ASCII", "ignore").decode()

        # Withdraw the package prefix (e.g. roseau.core)
        error_str = string.removeprefix(f"{cls.package_name}.")

        # Get the value of this string
        return cls[error_str.upper()]


class RoseauLoadFlowException(Exception):
    """A base exception for this repository"""

    def __init__(self, msg: str, code: RoseauLoadFlowExceptionCode, *args) -> None:
        """Constructor for RoseauCoreException

        Args:
            msg:
                A message in English.

            code:
                The code related to this exception.
        """
        super().__init__(msg, code, *args)
        self.msg = msg
        self.code = code

    def __str__(self) -> str:
        return str(self.code)
