"""
This module contains the exceptions used by Roseau Load Flow.
"""
import unicodedata
from enum import Enum, auto
from typing import Union

from typing_extensions import Self


class RoseauLoadFlowExceptionCode(Enum):
    """Error codes used by Roseau Load Flow."""

    # Generic
    BAD_GEOMETRY_TYPE = auto()
    BAD_PHASE = auto()
    BAD_ID_TYPE = auto()

    # Grounds and Potential references
    BAD_GROUND_ID = auto()
    BAD_POTENTIAL_REF_ID = auto()

    # Buses
    BAD_BUS_ID = auto()
    BAD_BUS_TYPE = auto()
    BAD_POTENTIALS_SIZE = auto()
    BAD_VOLTAGES = auto()
    BAD_VOLTAGES_SIZE = auto()
    BAD_SHORT_CIRCUIT = auto()

    # Branches
    BAD_BRANCH_ID = auto()
    BAD_BRANCH_TYPE = auto()
    BAD_Z_LINE_SHAPE = auto()
    BAD_Y_SHUNT_SHAPE = auto()
    BAD_LINE_MODEL = auto()
    BAD_LINE_TYPE = auto()
    BAD_CONDUCTOR_TYPE = auto()
    BAD_INSULATOR_TYPE = auto()
    BAD_Z_LINE_VALUE = auto()
    BAD_Y_SHUNT_VALUE = auto()
    BAD_TRANSFORMER_WINDINGS = auto()
    BAD_TRANSFORMER_TYPE = auto()
    BAD_TRANSFORMER_VOLTAGES = auto()
    BAD_TRANSFORMER_PARAMETERS = auto()
    BAD_TYPE_NAME_SYNTAX = auto()
    BAD_LENGTH_VALUE = auto()

    # Control
    BAD_CONTROL_TYPE = auto()
    BAD_CONTROL_VALUE = auto()

    # Projection
    BAD_PROJECTION_TYPE = auto()
    BAD_PROJECTION_VALUE = auto()

    # Flexible parameter
    BAD_FLEXIBLE_PARAMETER_VALUE = auto()

    # Load
    BAD_LOAD_ID = auto()
    BAD_LOAD_TYPE = auto()
    BAD_I_SIZE = auto()
    BAD_Z_SIZE = auto()
    BAD_Z_VALUE = auto()
    BAD_S_SIZE = auto()
    BAD_S_VALUE = auto()
    BAD_PARAMETERS_SIZE = auto()

    # Source
    BAD_SOURCE_ID = auto()

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
    BAD_REQUEST = auto()
    BAD_LOAD_FLOW_RESULT = auto()
    LOAD_FLOW_NOT_RUN = auto()
    SEVERAL_NETWORKS = auto()
    TOO_MANY_BUSES = auto()
    BAD_JACOBIAN = auto()

    # Solver
    BAD_SOLVER_NAME = auto()
    BAD_SOLVER_PARAMS = auto()
    NETWORK_SOLVER_MISMATCH = auto()

    # DGS export
    DGS_BAD_PHASE_TECHNOLOGY = auto()
    DGS_BAD_PHASE_NUMBER = auto()

    # JSON export
    JSON_LINE_PARAMETERS_DUPLICATES = auto()
    JSON_TRANSFORMER_PARAMETERS_DUPLICATES = auto()
    JSON_PREF_INVALID = auto()
    JSON_NO_RESULTS = auto()

    # Catalogue Mixin
    CATALOGUE_MISSING = auto()
    CATALOGUE_NOT_FOUND = auto()
    CATALOGUE_SEVERAL_FOUND = auto()

    # Import Error
    IMPORT_ERROR = auto()

    @classmethod
    def package_name(cls) -> str:
        return "roseau.load_flow"

    def __str__(self) -> str:
        return f"{self.package_name()}.{self.name}".lower()

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return other.lower() == str(self).lower()
        return super().__eq__(other)

    @classmethod
    def from_string(cls, string: Union[str, "RoseauLoadFlowExceptionCode"]) -> Self:
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
        error_str = string.removeprefix(f"{cls.package_name()}.")

        # Get the value of this string
        return cls[error_str.upper()]


class RoseauLoadFlowException(Exception):
    """Base exception for Roseau Load Flow."""

    def __init__(self, msg: str, code: RoseauLoadFlowExceptionCode, *args: object) -> None:
        """Constructor of RoseauLoadFlowException.

        Args:
            msg:
                A text description that provides the reason of the exception and potential
                solution.

            code:
                The code that identifies the reason of the exception.
        """
        super().__init__(msg, code, *args)
        self.msg = msg
        self.code = code

    def __str__(self) -> str:
        return f"{self.msg} [{self.code.name.lower()}]"
