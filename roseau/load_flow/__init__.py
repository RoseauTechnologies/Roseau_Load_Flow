"""
Welcome to the API reference of Roseau Load Flow.

For the most part, public classes and functions can be imported directly from this module.

See Package Contents below for a list of available classes and functions.
"""

import importlib.metadata
from typing import Any

from roseau.load_flow import constants, converters, plotting, sym
from roseau.load_flow.__about__ import (
    __authors__,
    __copyright__,
    __credits__,
    __email__,
    __license__,
    __maintainer__,
    __status__,
    __url__,
)
from roseau.load_flow.constants import SQRT3
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.license import License, activate_license, deactivate_license, get_license
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractConnectable,
    AbstractLoad,
    AbstractTerminal,
    Bus,
    Control,
    CurrentLoad,
    Element,
    FlexibleParameter,
    Ground,
    GroundConnection,
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
from roseau.load_flow.sym import ALPHA, ALPHA2, NegativeSequence, PositiveSequence, ZeroSequence
from roseau.load_flow.types import Insulator, LineType, Material, TransformerCooling, TransformerInsulation
from roseau.load_flow.units import Q_, ureg
from roseau.load_flow.utils import show_versions

__version__ = importlib.metadata.version("roseau-load-flow")

__all__ = [
    "__authors__",
    "__copyright__",
    "__credits__",
    "__email__",
    "__license__",
    "__maintainer__",
    "__status__",
    "__url__",
    "__version__",
    "show_versions",
    "converters",
    "constants",
    "plotting",
    "sym",
    # Electrical Network
    "ElectricalNetwork",
    # Buses
    "Bus",
    # Core models
    "Element",
    "Ground",
    "GroundConnection",
    "PotentialRef",
    "AbstractBranch",
    "AbstractTerminal",
    "AbstractConnectable",
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
    # Units
    "Q_",
    "ureg",
    # Types
    "LineType",
    "Material",
    "Insulator",
    "TransformerCooling",
    "TransformerInsulation",
    # License
    "activate_license",
    "deactivate_license",
    "get_license",
    "License",
    # Constants
    "ALPHA",
    "ALPHA2",
    "SQRT3",
    "PositiveSequence",
    "NegativeSequence",
    "ZeroSequence",
]


def __getattr__(name: str) -> Any:
    deprecated_classes = {"ConductorType": Material, "InsulatorType": Insulator}

    if name in deprecated_classes and name not in globals():
        import warnings

        from roseau.load_flow.utils.exceptions import find_stack_level

        new_class = deprecated_classes[name]
        warnings.warn(
            f"The `{name}` class is deprecated. Use `{new_class.__name__}` instead.",
            category=FutureWarning,
            stacklevel=find_stack_level(),
        )
        globals()[name] = new_class
        return new_class
    else:
        # raise AttributeError with original error message
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
