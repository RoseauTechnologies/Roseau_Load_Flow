"""
Welcome to the API reference of Roseau Load Flow.

For the most part, public classes and functions can be imported directly from this module.

See Package Contents below for a list of available classes and functions.
"""
import importlib.metadata

from roseau.load_flow.__about__ import (
    __author__,
    __copyright__,
    __credits__,
    __email__,
    __license__,
    __maintainer__,
    __status__,
    __url__,
)
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    Control,
    CurrentLoad,
    Element,
    FlexibleParameter,
    Ground,
    ImpedanceLoad,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    Projection,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.utils._versions import show_versions

__version__ = importlib.metadata.version("roseau_load_flow")

__all__ = [
    "__author__",
    "__copyright__",
    "__credits__",
    "__email__",
    "__license__",
    "__maintainer__",
    "__status__",
    "__url__",
    "__version__",
    "show_versions",
    # Electrical Network
    "ElectricalNetwork",
    # Buses
    "Bus",
    # Core
    "Element",
    "Ground",
    "PotentialRef",
    "AbstractBranch",
    # Lines
    "Switch",
    "Line",
    "LineParameters",
    # Loads
    "AbstractLoad",
    "ImpedanceLoad",
    "PowerLoad",
    "CurrentLoad",
    "FlexibleParameter",
    "Control",
    "Projection",
    # Transformers
    "Transformer",
    "TransformerParameters",
    "VoltageSource",
    # Exceptions
    "RoseauLoadFlowException",
    "RoseauLoadFlowExceptionCode",
]
