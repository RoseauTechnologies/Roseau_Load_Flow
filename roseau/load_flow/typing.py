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

.. class:: Authentication

    Valid authentication types used to connect to the Roseau Load Flow solver API.

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
"""
import os
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeVar, Union

import numpy as np
from numpy.typing import NDArray
from requests.auth import HTTPBasicAuth
from typing_extensions import TypeAlias

from roseau.load_flow.units import Q_

T = TypeVar("T")

Id: TypeAlias = Union[int, str]
JsonDict: TypeAlias = dict[str, Any]
StrPath: TypeAlias = Union[str, os.PathLike[str]]
ControlType: TypeAlias = Literal["constant", "p_max_u_production", "p_max_u_consumption", "q_u"]
ProjectionType: TypeAlias = Literal["euclidean", "keep_p", "keep_q"]
Solver: TypeAlias = Literal["newton", "newton_goldstein"]
Authentication: TypeAlias = Union[tuple[str, str], HTTPBasicAuth]
MapOrSeq: TypeAlias = Union[Mapping[Id, T], Sequence[T]]
ComplexArray: TypeAlias = NDArray[np.complex128]
# TODO: improve the types below when shape-typing becomes supported
ComplexArrayLike1D: TypeAlias = Union[
    ComplexArray,
    Q_[ComplexArray],
    Q_[Sequence[complex]],
    Sequence[Union[complex, Q_[complex]]],
]
ComplexArrayLike2D: TypeAlias = Union[
    ComplexArray,
    Q_[ComplexArray],
    Q_[Sequence[Sequence[complex]]],
    Sequence[Sequence[Union[complex, Q_[complex]]]],
]


__all__ = [
    "Id",
    "JsonDict",
    "StrPath",
    "ControlType",
    "ProjectionType",
    "Solver",
    "Authentication",
    "MapOrSeq",
    "ComplexArray",
    "ComplexArrayLike1D",
    "ComplexArrayLike2D",
]
