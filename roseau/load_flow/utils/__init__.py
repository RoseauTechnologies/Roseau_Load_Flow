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
    SourceTypeDtype,
    VoltagePhaseDtype,
)
from roseau.load_flow.utils.helpers import (
    SIDE_DESC,
    SIDE_INDEX,
    SIDE_SUFFIX,
    CaseInsensitiveStrEnum,
    abstractattrs,
    count_repr,
    ensure_startsupper,
    geom_mapping,
    id_sort_key,
    one_or_more_repr,
    warn_external,
)
from roseau.load_flow.utils.log import set_logging_config
from roseau.load_flow.utils.mixins import AbstractElement, AbstractNetwork, CatalogueMixin, Identifiable, JsonMixin
from roseau.load_flow.utils.versions import show_versions

__all__ = [
    # Mixins
    "Identifiable",
    "JsonMixin",
    "CatalogueMixin",
    "AbstractElement",
    "AbstractNetwork",
    # Exceptions and warnings
    "warn_external",
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
    "SourceTypeDtype",
    "VoltagePhaseDtype",
    # Versions
    "show_versions",
    # Logging
    "set_logging_config",
    # General purpose
    "count_repr",
    "one_or_more_repr",
    "id_sort_key",
    "ensure_startsupper",
    "geom_mapping",
    # Enums
    "CaseInsensitiveStrEnum",
    # Decorators
    "abstractattrs",
    # Branch side helpers
    "SIDE_DESC",
    "SIDE_INDEX",
    "SIDE_SUFFIX",
]
