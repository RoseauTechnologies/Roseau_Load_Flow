import functools
from collections.abc import Callable, Iterable, MutableSequence
from inspect import Parameter, Signature, signature
from itertools import zip_longest
from typing import Any, TypeVar

from pint import Quantity, Unit
from pint.registry import UnitRegistry
from pint.util import to_units_container

T = TypeVar("T")
FuncT = TypeVar("FuncT", bound=Callable)


def _parse_wrap_args(args: Iterable[str | Unit | None]) -> Callable:
    """Create a converter function for the wrapper"""
    # _to_units_container
    args_as_uc = [to_units_container(arg) for arg in args]

    # Check for references in args, remove None values
    unit_args_ndx = {ndx for ndx, arg in enumerate(args_as_uc) if arg is not None}

    def _converter(ureg: "UnitRegistry", sig: "Signature", values: "list[Any]", kw: "dict[Any]"):
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


def wraps(
    ureg: UnitRegistry,
    ret: str | Unit | Iterable[str | Unit | None] | None,
    args: str | Unit | Iterable[str | Unit | None] | None,
) -> Callable[[FuncT], FuncT]:
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

    def decorator(func: "Callable[..., Any]") -> "Callable[..., Quantity]":
        sig = signature(func)
        count_params = len(sig.parameters)
        if len(args) != count_params:
            raise TypeError(f"{func.__name__} takes {count_params} parameters, but {len(args)} units were passed")

        assigned = tuple(attr for attr in functools.WRAPPER_ASSIGNMENTS if hasattr(func, attr))
        updated = tuple(attr for attr in functools.WRAPPER_UPDATES if hasattr(func, attr))

        @functools.wraps(func, assigned=assigned, updated=updated)
        def wrapper(*values, **kw) -> "Quantity":
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
