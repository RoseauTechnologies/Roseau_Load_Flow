"""
Type Aliases used by Roseau Load Flow.

.. warning::

    Types defined in this module are not part of the public API. You can use these types in your
    code, but they are not guaranteed to be stable.

.. class:: Id

    The type of the identifier of an element. An element's ID can be an integer or a string.

.. class:: JsonDict

    A dictionary that can be serialized to JSON.

.. class:: StrPath

    The accepted type for file paths in roseau.load_flow. This is a string or a path-like object.

.. class:: ControlType

    Available control types for flexible loads.

.. class:: ProjectionType

    Available projections types for flexible loads control.

.. class:: Solver

    Available solvers for the load flow computation.

.. class:: MapOrSeq

    A mapping from element IDs to elements or a sequence of elements of unique IDs.

.. class:: ComplexArray

    A numpy array of complex numbers.

.. class:: ComplexArrayLike1D

    A 1D array-like of complex numbers or a quantity of complex numbers. An array-like is a
    sequence or a numpy array.

.. class:: ComplexArrayLike2D

    A 2D array-like of complex numbers or a quantity of complex numbers. An array-like is a
    sequence or a numpy array.

.. class:: FloatArrayLike1D

    A 1D array-like of floating numbers or a quantity of floating numbers. An array-like is a
    sequence or a numpy array.
"""

import os
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeAlias, TypeVar

import numpy as np
from numpy.typing import NDArray

from roseau.load_flow.units import Q_

T = TypeVar("T", bound=Any)

Id: TypeAlias = int | str
JsonDict: TypeAlias = dict[str, Any]
StrPath: TypeAlias = str | os.PathLike[str]
ControlType: TypeAlias = Literal["constant", "p_max_u_production", "p_max_u_consumption", "q_u"]
ProjectionType: TypeAlias = Literal["euclidean", "keep_p", "keep_q"]
Solver: TypeAlias = Literal["newton", "newton_goldstein"]
MapOrSeq: TypeAlias = Mapping[int, T] | Mapping[str, T] | Mapping[Id, T] | Sequence[T]
ComplexArray: TypeAlias = NDArray[np.complex128]
QtyOrMag: TypeAlias = Q_[T] | T

Int: TypeAlias = int | np.integer[Any]
Float: TypeAlias = float | np.floating[Any] | Int
Complex: TypeAlias = complex | np.complexfloating[Any, Any] | Float

ComplexArrayLike1D: TypeAlias = QtyOrMag[NDArray[np.number] | Sequence[Complex]] | Sequence[QtyOrMag[Complex]]
ComplexScalarOrArrayLike1D: TypeAlias = ComplexArrayLike1D | QtyOrMag[Complex]
ComplexArrayLike2D: TypeAlias = (
    QtyOrMag[NDArray[np.number] | Sequence[Sequence[Complex]]] | Sequence[Sequence[QtyOrMag[Complex]]]
)
FloatArrayLike1D: TypeAlias = (
    QtyOrMag[NDArray[np.floating[Any] | np.integer[Any]] | Sequence[Float]] | Sequence[QtyOrMag[Float]]
)

__all__ = [
    "Id",
    "JsonDict",
    "StrPath",
    "ControlType",
    "ProjectionType",
    "Solver",
    "MapOrSeq",
    "ComplexArray",
    "ComplexArrayLike1D",
    "ComplexArrayLike2D",
    "FloatArrayLike1D",
]
