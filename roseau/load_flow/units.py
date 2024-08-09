"""
Units registry used by Roseau Load Flow using the `pint`_ package.

.. class:: ureg

    The :class:`pint.UnitRegistry` object to use in this project. You should not need to use it
    directly.

.. class:: Q_

    The :class:`pint.Quantity` class to use in this project. You can use it to provide quantities
    in units different from the default ones. For example, to create a constant power load of 1 MVA,
    you can do:

    >>> load = rlf.PowerLoad("load", bus=bus, powers=Q_([1, 1, 1], "MVA"))

    which is equivalent to:

    >>> load = rlf.PowerLoad("load", bus=bus, powers=[1000000, 1000000, 1000000])  # in VA

.. _pint: https://pint.readthedocs.io/en/stable/getting/overview.html
"""

from collections.abc import Callable, Iterable, Sequence
from decimal import Decimal
from fractions import Fraction
from types import GenericAlias
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar, overload

import numpy as np
from numpy.typing import NDArray
from pint import Unit, UnitRegistry
from pint.facets.numpy.quantity import NumpyQuantity
from pint.util import UnitsContainer

from roseau.load_flow._wrapper import wraps

FuncT = TypeVar("FuncT", bound=Callable)

ureg: UnitRegistry = UnitRegistry(
    preprocessors=[
        lambda s: s.replace("%", " percent "),
    ]
)
ureg.define("volt_ampere_reactive = 1 * volt_ampere = VAr")

if TYPE_CHECKING:
    # Copy types from pint and add complex
    Scalar: TypeAlias = int | float | Decimal | Fraction | complex | np.number[Any]
    Array: TypeAlias = np.ndarray[Any, Any]
    UnitLike = str | dict[str, Scalar] | UnitsContainer | Unit

    NpNumT = TypeVar("NpNumT", bound=np.number[Any])
    MagBound = Scalar | Array | Sequence[Scalar | Array] | Sequence[Sequence[Scalar | Array]]
    MagT = TypeVar("MagT", bound=MagBound)
    MagT_co = TypeVar("MagT_co", covariant=True, bound=MagBound)

    # Redefine Q_ with support for complex and better type hints
    class Q_(NumpyQuantity[MagT_co]):  # type: ignore # noqa: N801
        @overload  # Known magnitude type
        def __new__(cls, value: MagT, units: UnitLike | None = None) -> "Q_[MagT]": ...

        @overload  # Unknown magnitude type
        def __new__(cls, value: str, units: UnitLike | None = None) -> "Q_[Any]": ...

        @overload  # int sequence becomes int64 array
        def __new__(
            cls, value: Sequence[int | Sequence[int]], units: UnitLike | None = None
        ) -> "Q_[NDArray[np.int64]]": ...

        @overload  # float sequence becomes float64 array
        def __new__(
            cls, value: Sequence[float | Sequence[float]], units: UnitLike | None = None
        ) -> "Q_[NDArray[np.float64]]": ...

        @overload  # complex sequence becomes complex128 array
        def __new__(
            cls, value: Sequence[complex | Sequence[complex]], units: UnitLike | None = None
        ) -> "Q_[NDArray[np.complex128]]": ...

        @overload  # numpy number sequence becomes array with same dtype
        def __new__(
            cls, value: Sequence[NpNumT | Sequence[NpNumT]], units: UnitLike | None = None
        ) -> "Q_[NDArray[NpNumT]]": ...

        @overload  # quantity gets passed through (copied) when units are None
        def __new__(cls, value: "Q_[MagT]", units: None = None) -> "Q_[MagT]": ...

        @overload  # quantity may get altered when units are not None (conversion)
        def __new__(cls, value: "Q_[Any]", units: UnitLike | None = None) -> "Q_[Any]": ...

        def __new__(cls, value: MagT_co, units: UnitLike | None = None) -> "Q_[MagT_co]":  # type: ignore
            return super().__new__(cls, value, units)  # type: ignore

        def __init__(self, value: MagT_co, units: UnitLike | None = None) -> None:
            super().__init__(value, units)  # type: ignore  # for PyCharm only, it does not recognize __new__ alone

        def __getattr__(self, name: str) -> Any: ...  # attributes of the magnitude are accessible on the quantity

else:
    ureg.Quantity.__class_getitem__ = classmethod(GenericAlias)
    globals()["Q_"] = ureg.Quantity  # Use globals() to trick PyCharm


def ureg_wraps(
    ret: str | Unit | None | Iterable[str | Unit | None],
    args: str | Unit | None | Iterable[str | Unit | None],
    strict: bool = True,
) -> Callable[[FuncT], FuncT]:
    """Wraps a function to become pint-aware.

    Args:
        ret:
            Units of each of the return values. Use `None` to skip argument conversion.
        args:
            Units of each of the input arguments. Use `None` to skip argument conversion.
        strict:
            Indicates that only quantities are accepted. (Default value = True)
    """
    return wraps(ureg, ret, args)
