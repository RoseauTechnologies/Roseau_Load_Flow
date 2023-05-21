"""
Type Aliases used by Roseau Load Flow.

.. class:: Id

    The type of the identifier of an element.

.. class:: JsonDict

    A dictionary that can be serialized to JSON.

.. class:: StrPath

    The accepted type for files of roseau.load_flow.io.

.. class:: ControlType

    Available types of control for flexible loads.

.. class:: ProjectionType

    Available types of projections for flexible loads control.

.. class:: Solver

    Available solvers for the load flow computation.

.. class:: Self

    The type of the class itself.
"""
import os
import sys
from typing import TYPE_CHECKING, Any, Literal, TypeVar, Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias as TypeAlias
elif TYPE_CHECKING:
    from typing_extensions import TypeAlias as TypeAlias
else:
    TypeAlias = Any

Id: TypeAlias = Union[int, str]
JsonDict: TypeAlias = dict[str, Any]
StrPath: TypeAlias = Union[str, os.PathLike[str]]
ControlType: TypeAlias = Literal["constant", "p_max_u_production", "p_max_u_consumption", "q_u"]
ProjectionType: TypeAlias = Literal["euclidean", "keep_p", "keep_q"]
Solver: TypeAlias = Literal["newton", "newton_goldstein"]

if sys.version_info >= (3, 11):
    from typing import Self as Self
elif TYPE_CHECKING:
    from typing_extensions import Self as Self
else:
    Self = TypeVar("Self")

__all__ = ["Id", "JsonDict", "StrPath", "ControlType", "ProjectionType", "Solver", "Self"]
