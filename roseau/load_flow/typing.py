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

.. class:: Authentication

    Valid authentication types.

.. class:: ComplexArray

    A numpy array of complex numbers.
"""
import os
from typing import Any, Literal, Union

import numpy as np
from numpy.typing import NDArray
from requests.auth import HTTPBasicAuth
from typing_extensions import TypeAlias

Id: TypeAlias = Union[int, str]
JsonDict: TypeAlias = dict[str, Any]
StrPath: TypeAlias = Union[str, os.PathLike[str]]
ControlType: TypeAlias = Literal["constant", "p_max_u_production", "p_max_u_consumption", "q_u"]
ProjectionType: TypeAlias = Literal["euclidean", "keep_p", "keep_q"]
Solver: TypeAlias = Literal["newton", "newton_goldstein"]
Authentication: TypeAlias = Union[tuple[str, str], HTTPBasicAuth]
ComplexArray: TypeAlias = NDArray[np.complex_]


__all__ = [
    "Id",
    "JsonDict",
    "StrPath",
    "ControlType",
    "ProjectionType",
    "Solver",
    "Authentication",
    "ComplexArray",
]
