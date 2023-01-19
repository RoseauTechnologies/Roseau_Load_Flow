"""Aliases for types used in the load flow module.

These will help users to get better IDE support.
"""
import os
import sys
from typing import Any, TYPE_CHECKING, TypeVar, Union

Id = Union[int, str]
"""The type of the identifier of an element."""

JsonDict = dict[str, Any]
"""A dictionary that can be serialized to JSON."""

StrPath = Union[str, os.PathLike[str]]
"""The accepted type for files of roseau.load_flow.io."""


if sys.version_info >= (3, 11):
    from typing import Self as Self
elif TYPE_CHECKING:
    from typing_extensions import Self as Self
else:
    Self = TypeVar("Self")
