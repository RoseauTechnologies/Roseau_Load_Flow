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

import functools
from collections.abc import Callable, Iterable, MutableSequence, Sequence
from decimal import Decimal
from fractions import Fraction
from inspect import Parameter, Signature, signature
from itertools import zip_longest
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, overload

import numpy as np
from numpy.typing import NDArray
from pint.facets.numpy.quantity import NumpyQuantity
from pint.registry import Unit, UnitRegistry
from pint.util import UnitsContainer, to_units_container

__all__ = ["ureg", "Q_", "ureg_wraps"]

ureg: UnitRegistry = UnitRegistry(
    preprocessors=[
        lambda s: s.replace("%", " percent "),
    ]
)
ureg.define("volt_ampere_reactive = 1 * volt_ampere = VAr")

if TYPE_CHECKING:
    # Copy types from pint and add complex
    type Scalar = int | float | Decimal | Fraction | complex | np.number[Any]
    type Array = np.ndarray[Any, Any]
    type UnitLike = str | dict[str, Scalar] | UnitsContainer | Unit
    type Magnitude = Scalar | Array | Sequence[Scalar | Array] | Sequence[Sequence[Scalar | Array]]
    M_co = TypeVar("M_co", covariant=True, bound=Magnitude)

    # Redefine Q_ with support for complex and better type hints
    class Q_(NumpyQuantity[M_co]):  # type: ignore # noqa: N801
        @overload  # Known magnitude type
        def __new__[M: Magnitude](cls, value: M, units: UnitLike | None = None) -> "Q_[M]": ...

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
        def __new__[N: np.number](
            cls, value: Sequence[N | Sequence[N]], units: UnitLike | None = None
        ) -> "Q_[NDArray[N]]": ...

        @overload  # quantity gets passed through (copied) when units are None
        def __new__[M: Magnitude](cls, value: "Q_[M]", units: None = None) -> "Q_[M]": ...

        @overload  # quantity may get altered when units are not None (conversion)
        def __new__(cls, value: "Q_[Any]", units: UnitLike | None = None) -> "Q_[Any]": ...

        def __new__(cls, value: M_co, units: UnitLike | None = None) -> "Q_[M_co]":  # type: ignore
            return super().__new__(cls, value, units)  # type: ignore

        def __init__(self, value: M_co, units: UnitLike | None = None) -> None:
            super().__init__(value, units)  # type: ignore  # for PyCharm only, it does not recognize __new__ alone

        def __getattr__(self, name: str) -> Any: ...  # attributes of the magnitude are accessible on the quantity

else:
    ureg.Quantity.__class_getitem__ = classmethod(GenericAlias)
    globals()["Q_"] = ureg.Quantity  # Use globals() to trick PyCharm

type OptionalUnits = str | Unit | None | tuple[str | Unit | None, ...] | list[str | Unit | None]


class _IdentityFunction(Protocol):
    def __call__[F: Callable](self, fn: F, /) -> F: ...


def ureg_wraps(ret: OptionalUnits, args: OptionalUnits, strict: bool = True) -> _IdentityFunction:
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


def _parse_wrap_args(args: Iterable[str | Unit | None]) -> Callable:
    """Create a converter function for the wrapper"""
    # _to_units_container
    args_as_uc = [to_units_container(arg) for arg in args]

    # Check for references in args, remove None values
    unit_args_ndx = {ndx for ndx, arg in enumerate(args_as_uc) if arg is not None}

    def _converter(ureg: "UnitRegistry", sig: "Signature", values: "list[Any]", kw: "dict[str, Any]"):
        len_initial_values = len(values)

        # pack kwargs
        for i, param_name in enumerate(sig.parameters):
            if i >= len_initial_values:
                values.append(kw[param_name])

        # convert arguments
        for ndx in unit_args_ndx:
            value = values[ndx]
            if isinstance(value, ureg.Quantity):
                values[ndx] = ureg.convert(value.magnitude, value.units, args_as_uc[ndx])
            elif isinstance(value, MutableSequence):
                for i, val in enumerate(value):
                    if isinstance(val, ureg.Quantity):
                        value[i] = ureg.convert(val.magnitude, val.units, args_as_uc[ndx])

        # unpack kwargs
        for i, param_name in enumerate(sig.parameters):
            if i >= len_initial_values:
                kw[param_name] = values[i]

        return values[:len_initial_values], kw

    return _converter


def _apply_defaults(sig: Signature, args: tuple[Any], kwargs: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    """Apply default keyword arguments.

    Named keywords may have been left blank. This function applies the default
    values so that every argument is defined.
    """
    n = len(args)
    for i, param in enumerate(sig.parameters.values()):
        if i >= n and param.default != Parameter.empty and param.name not in kwargs:
            kwargs[param.name] = param.default
    return list(args), kwargs


def wraps(ureg: UnitRegistry, ret: OptionalUnits, args: OptionalUnits) -> _IdentityFunction:
    """Wraps a function to become pint-aware.

    Use it when a function requires a numerical value but in some specific
    units. The wrapper function will take a pint quantity, convert to the units
    specified in `args` and then call the wrapped function with the resulting
    magnitude.

    The value returned by the wrapped function will be converted to the units
    specified in `ret`.

    Args:
        ureg:
            A UnitRegistry instance.

        ret:
            Units of each of the return values. Use `None` to skip argument conversion.

        args:
             Units of each of the input arguments. Use `None` to skip argument conversion.

    Returns:
        The wrapper function.

    Raises:
        TypeError
            if the number of given arguments does not match the number of function parameters.
            if any of the provided arguments is not a unit a string or Quantity
    """
    if not isinstance(args, (list, tuple)):
        args = (args,)

    for arg in args:
        if arg is not None and not isinstance(arg, (ureg.Unit, str)):
            raise TypeError(f"wraps arguments must by of type str or Unit, not {type(arg)} ({arg})")

    converter = _parse_wrap_args(args)

    is_ret_container = isinstance(ret, (list, tuple))
    if is_ret_container:
        for arg in ret:
            if arg is not None and not isinstance(arg, (ureg.Unit, str)):
                raise TypeError(f"wraps 'ret' argument must by of type str or Unit, not {type(arg)} ({arg})")
        ret = ret.__class__([to_units_container(arg, ureg) for arg in ret])
    else:
        if ret is not None and not isinstance(ret, (ureg.Unit, str)):
            raise TypeError(f"wraps 'ret' argument must by of type str or Unit, not {type(ret)} ({ret})")
        ret = to_units_container(ret, ureg)

    def decorator(func):
        sig = signature(func)
        count_params = len(sig.parameters)
        if len(args) != count_params:
            raise TypeError(f"{func.__name__} takes {count_params} parameters, but {len(args)} units were passed")

        assigned = tuple(attr for attr in functools.WRAPPER_ASSIGNMENTS if hasattr(func, attr))
        updated = tuple(attr for attr in functools.WRAPPER_UPDATES if hasattr(func, attr))

        @functools.wraps(func, assigned=assigned, updated=updated)
        def wrapper(*values, **kw):
            values, kw = _apply_defaults(sig, values, kw)

            # In principle, the values are used as is
            # When then extract the magnitudes when needed.
            new_values, new_kw = converter(ureg, sig, values, kw)

            result = func(*new_values, **new_kw)

            if is_ret_container:
                return ret.__class__(
                    res if unit is None else ureg.Quantity(res, unit) for unit, res in zip_longest(ret, result)
                )

            if ret is None:
                return result

            return ureg.Quantity(result, ret)

        return wrapper

    return decorator
