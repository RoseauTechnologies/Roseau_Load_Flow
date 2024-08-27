"""
This module contains the exceptions used by Roseau Load Flow.
"""

from enum import auto

from roseau.load_flow._compat import StrEnum


class RoseauLoadFlowExceptionCode(StrEnum):
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
    BAD_POTENTIALS_SIZE = auto()
    BAD_VOLTAGES = auto()
    BAD_VOLTAGES_SIZE = auto()
    BAD_SHORT_CIRCUIT = auto()

    # Branches
    BAD_BRANCH_TYPE = auto()

    # Lines
    BAD_LINE_ID = auto()
    BAD_Z_LINE_SHAPE = auto()
    BAD_Y_SHUNT_SHAPE = auto()
    BAD_LINE_MODEL = auto()
    BAD_LINE_TYPE = auto()
    BAD_CONDUCTOR_TYPE = auto()
    BAD_INSULATOR_TYPE = auto()
    BAD_Z_LINE_VALUE = auto()
    BAD_Y_SHUNT_VALUE = auto()
    BAD_TYPE_NAME_SYNTAX = auto()
    BAD_LENGTH_VALUE = auto()

    # Transformer
    BAD_TRANSFORMER_ID = auto()
    BAD_TRANSFORMER_WINDINGS = auto()
    BAD_TRANSFORMER_TYPE = auto()
    BAD_TRANSFORMER_VOLTAGES = auto()
    BAD_TRANSFORMER_IMPEDANCE = auto()
    BAD_TRANSFORMER_PARAMETERS = auto()

    # Switch
    BAD_SWITCH_ID = auto()

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
    EMPTY_NETWORK = auto()
    UNKNOWN_ELEMENT = auto()
    NO_VOLTAGE_SOURCE = auto()
    BAD_ELEMENT_OBJECT = auto()
    DISCONNECTED_ELEMENT = auto()
    POORLY_CONNECTED_ELEMENT = auto()
    NO_LOAD_FLOW_CONVERGENCE = auto()
    BAD_LOAD_FLOW_RESULT = auto()
    LOAD_FLOW_NOT_RUN = auto()
    SEVERAL_NETWORKS = auto()
    BAD_JACOBIAN = auto()

    # Solver
    BAD_SOLVER_NAME = auto()
    BAD_SOLVER_PARAMS = auto()

    # DGS export
    DGS_BAD_PHASE_TECHNOLOGY = auto()
    DGS_BAD_PHASE_NUMBER = auto()
    DGS_BAD_TYPE_ID = auto()
    DGS_MISSING_REQUIRED_DATA = auto()

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

    # License errors
    LICENSE_ERROR = auto()

    # OpenDSS import
    DSS_BAD_LOSS = auto()

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return other.lower() == self.lower()
        return super().__eq__(other)

    @classmethod
    def _missing_(cls, value: object) -> "RoseauLoadFlowExceptionCode | None":
        if isinstance(value, str):
            try:
                return cls[value.upper().replace(" ", "_").replace("-", "_")]
            except KeyError:
                return None


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
