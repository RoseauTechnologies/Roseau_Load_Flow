"""
Internal utility classes and functions for Roseau Load Flow.
"""

from roseau.load_flow.utils.deprecations import (
    deprecate_nonkeyword_arguments,
    deprecate_parameter_as_multi_positional,
    deprecate_renamed_parameter,
    deprecate_renamed_parameters,
)
from roseau.load_flow.utils.dtypes import (
    DTYPES,
    BranchTypeDtype,
    LoadTypeDtype,
    PhaseDtype,
    SequenceDtype,
    VoltagePhaseDtype,
)
from roseau.load_flow.utils.exceptions import find_stack_level
from roseau.load_flow.utils.helpers import CaseInsensitiveStrEnum, count_repr
from roseau.load_flow.utils.log import set_logging_config
from roseau.load_flow.utils.mixins import CatalogueMixin, Identifiable, JsonMixin
from roseau.load_flow.utils.versions import show_versions

__all__ = [
    # Mixins
    "Identifiable",
    "JsonMixin",
    "CatalogueMixin",
    # Exceptions and warnings
    "find_stack_level",
    "deprecate_nonkeyword_arguments",
    "deprecate_parameter_as_multi_positional",
    "deprecate_renamed_parameter",
    "deprecate_renamed_parameters",
    # DTypes
    "DTYPES",
    "BranchTypeDtype",
    "LoadTypeDtype",
    "PhaseDtype",
    "SequenceDtype",
    "VoltagePhaseDtype",
    # Versions
    "show_versions",
    # Logging
    "set_logging_config",
    # General purpose
    "count_repr",
    # Enums
    "CaseInsensitiveStrEnum",
]


def __getattr__(name: str):
    import warnings

    deprecation_template = (
        "Importing {name} from 'roseau.load_flow.utils' is deprecated. Use 'rlf.{module}.{name}' instead."
    )
    if name in (
        "ALPHA",
        "ALPHA2",
        "PI",
        "SQRT3",
        "DELTA_P",
        "EPSILON_0",
        "EPSILON_R",
        "F",
        "MU_0",
        "MU_R",
        "OMEGA",
        "RHO",
        "TAN_D",
    ):
        warnings.warn(
            deprecation_template.format(name=name, module="constants"),
            category=FutureWarning,
            stacklevel=find_stack_level(),
        )
        from roseau.load_flow import constants

        return getattr(constants, name)
    elif name in ("PositiveSequence", "NegativeSequence", "ZeroSequence"):
        warnings.warn(
            deprecation_template.format(name=name, module="sym"),
            category=FutureWarning,
            stacklevel=find_stack_level(),
        )
        from roseau.load_flow import sym

        return getattr(sym, name)
    elif name in ("LineType", "Material", "Insulator"):
        warnings.warn(
            deprecation_template.format(name=name, module="types"),
            category=FutureWarning,
            stacklevel=find_stack_level(),
        )
        from roseau.load_flow import types

        return getattr(types, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
