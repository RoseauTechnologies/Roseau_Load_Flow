"""
Type Aliases used by Roseau Load Flow.

.. class:: Id

    The type of the identifier of an element.

.. class:: JsonDict

    A dictionary that can be serialized to JSON.

.. class:: StrPath

    The accepted type for files of roseau.load_flow.io.

.. class:: Self

    The type of the class itself.
"""
import os
import sys
from typing import Any, TYPE_CHECKING, TypeVar, Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias as TypeAlias
elif TYPE_CHECKING:
    from typing_extensions import TypeAlias as TypeAlias
else:
    TypeAlias = Any

Id: TypeAlias = Union[int, str]
JsonDict: TypeAlias = dict[str, Any]
StrPath: TypeAlias = Union[str, os.PathLike[str]]


if sys.version_info >= (3, 11):
    from typing import Self as Self
elif TYPE_CHECKING:
    from typing_extensions import Self as Self
else:
    Self = TypeVar("Self")
