"""
Type Aliases used by Roseau Load Flow.

.. warning::

    Types defined in this module are not part of the public API. You can use these types in your
    code, but they are not guaranteed to be stable.

Roseau Load Flow Helpers
------------------------

.. class:: Id

    The type of the identifier of an element. An element's ID can be an integer or a string.

.. class:: JsonDict

    A dictionary that can be serialized to JSON.

.. class:: StrPath

    The accepted type for file paths in roseau.load_flow. This is a string or a path-like object.

.. class:: MapOrSeq

    A mapping from element IDs to elements or a sequence of elements of unique IDs.


Roseau Load Flow Literals
-------------------------

.. class:: ControlType

    Available control types for flexible loads.

.. class:: ProjectionType

    Available projections types for flexible loads control.

.. class:: Solver

    Available solvers for the load flow computation.

.. class:: Side

    The side of a transformer (``"HV"`` or ``"LV"``) or a line/switch (1 or 2). ``None`` is used
    for terminal elements that do not have a side.

Union Input Types (Wide)
------------------------

.. class:: Int

    An Python int or a numpy integer.

.. class:: Float

    A Python real number (float or int) or a numpy real number (floating or integer).

.. class:: Complex

    A Python complex number (complex, float or int) or a numpy complex number (complexfloating,
    floating or integer).

.. class:: ComplexArrayLike1D

    A 1D array-like of complex numbers or a quantity of complex numbers. An array-like is a
    sequence or a numpy array.

.. class:: ComplexArrayLike2D

    A 2D array-like of complex numbers or a quantity of complex numbers. An array-like is a
    sequence or a numpy array.

.. class:: FloatArrayLike1D

    A 1D array-like of floating numbers or a quantity of floating numbers. An array-like is a
    sequence or a numpy array.

.. class:: ComplexScalarOrArrayLike1D

    A scalar or a 1D array-like of complex numbers or a quantity thereof.

.. class:: FloatScalarOrArrayLike1D

    A scalar or a 1D array-like of floating numbers or a quantity thereof.

.. class:: CRSLike

    Any type accepted by :class:`pyproj.CRS`. This can be a string (PROJ, JSON WKT, authority),
    an integer (EPSG code), a dictionary (PROJ parameters), a tuple (authority name and code), an
    object with a `to_wkt` method, or a CRS class.

Numpy Output Types (Narrow)
---------------------------

.. class:: ComplexMatrix

    A 2-D numpy array of complex numbers.

.. class:: FloatMatrix

    A 2-D numpy array of real numbers.

.. class:: ComplexArray

    A 1-D numpy array of complex numbers.

.. class:: FloatArray

    A 1-D numpy array of real numbers.

.. class:: BoolArray

    A 1-D numpy array of booleans.
"""

import os
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol, TypeAlias, TypeVar

import numpy as np
from numpy.typing import NDArray
from pyproj import CRS

from roseau.load_flow.units import Q_

T = TypeVar("T", bound=Any)


class _SupportsToWkt(Protocol):
    def to_wkt(self) -> str: ...


# RLF Helpers
Id: TypeAlias = int | str
JsonDict: TypeAlias = dict[str, Any]
StrPath: TypeAlias = str | os.PathLike[str]
MapOrSeq: TypeAlias = Mapping[int, T] | Mapping[str, T] | Mapping[Id, T] | Sequence[T]
QtyOrMag: TypeAlias = Q_[T] | T

# RLF Literals
ControlType: TypeAlias = Literal["constant", "p_max_u_production", "p_max_u_consumption", "q_u"]
ProjectionType: TypeAlias = Literal["euclidean", "keep_p", "keep_q"]
Solver: TypeAlias = Literal["newton", "newton_goldstein", "backward_forward"]
Side: TypeAlias = Literal[1, 2, "HV", "LV"] | None

# Input Types (Wide)
Int: TypeAlias = int | np.integer
Float: TypeAlias = float | np.floating | Int
Complex: TypeAlias = complex | np.complexfloating[Any, Any] | Float
ComplexArrayLike1D: TypeAlias = QtyOrMag[NDArray[np.number] | Sequence[Complex]] | Sequence[QtyOrMag[Complex]]
ComplexScalarOrArrayLike1D: TypeAlias = ComplexArrayLike1D | QtyOrMag[Complex]
ComplexArrayLike2D: TypeAlias = (
    QtyOrMag[NDArray[np.number] | Sequence[Sequence[Complex]]] | Sequence[Sequence[QtyOrMag[Complex]]]
)
FloatArrayLike1D: TypeAlias = QtyOrMag[NDArray[np.floating | np.integer] | Sequence[Float]] | Sequence[QtyOrMag[Float]]
FloatScalarOrArrayLike1D: TypeAlias = FloatArrayLike1D | QtyOrMag[Float]
CRSLike: TypeAlias = (
    # The following are documented in the pyproj.CRS class
    # - PROJ string
    # - JSON string with PROJ parameters
    # - CRS WKT string
    # - An authority string [i.e. 'epsg:4326']
    str
    # - An EPSG integer code [i.e. 4326]
    | int
    # - Dictionary of PROJ parameters
    | dict[str, Any]
    # - A tuple of ("auth_name": "auth_code") [i.e ('epsg', '4326')]
    | tuple[str, str]
    # - An object with a `to_wkt` method
    | _SupportsToWkt
    # - A CRS class
    | CRS
)

# Numpy Output Types (Narrow)
ComplexMatrix: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.complex128]]  # 2D
FloatMatrix: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]  # 2D
ComplexArray: TypeAlias = np.ndarray[tuple[int], np.dtype[np.complex128]]  # 1D
FloatArray: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]  # 1D
BoolArray: TypeAlias = np.ndarray[tuple[int], np.dtype[np.bool_]]  # 1D

__all__ = [
    # Helpers
    "Id",
    "JsonDict",
    "StrPath",
    "MapOrSeq",
    "QtyOrMag",
    # Literals
    "ControlType",
    "ProjectionType",
    "Solver",
    "Side",
    # Wide input types
    "Int",
    "Float",
    "Complex",
    "ComplexArrayLike1D",
    "ComplexArrayLike2D",
    "FloatArrayLike1D",
    "ComplexScalarOrArrayLike1D",
    "FloatScalarOrArrayLike1D",
    "CRSLike",
    # Numpy narrow output types
    "BoolArray",
    "FloatArray",
    "ComplexArray",
    "FloatMatrix",
    "ComplexMatrix",
]
