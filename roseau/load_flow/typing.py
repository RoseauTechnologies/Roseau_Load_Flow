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
"""
import os
from typing import Any, Literal, Union

from typing_extensions import TypeAlias

Id: TypeAlias = Union[int, str]
JsonDict: TypeAlias = dict[str, Any]
StrPath: TypeAlias = Union[str, os.PathLike[str]]
ControlType: TypeAlias = Literal["constant", "p_max_u_production", "p_max_u_consumption", "q_u"]
ProjectionType: TypeAlias = Literal["euclidean", "keep_p", "keep_q"]
Solver: TypeAlias = Literal["newton", "newton_goldstein"]


__all__ = ["Id", "JsonDict", "StrPath", "ControlType", "ProjectionType", "Solver"]
