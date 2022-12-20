"""Aliases for types used in the load flow module.

These will help users to get better IDE support.
"""
import os
from typing import Any, Union

Id = Union[int, str]
"""The type of the identifier of an element."""

JsonDict = dict[str, Any]
"""A dictionary that can be serialized to JSON."""

StrPath = Union[str, os.PathLike[str]]
"""The accepted type for files of roseau.load_flow.io."""
