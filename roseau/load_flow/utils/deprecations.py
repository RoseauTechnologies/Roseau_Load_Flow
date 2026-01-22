# The deprecate_renamed_parameter, deprecate_nonkeyword_arguments, and deprecate_parameter_as_multi_positional
# functions are adapted from the `polars._utils.deprecation` module from the polars library licensed
# under the MIT license.
# polars source code is available at https://github.com/pola-rs/polars
import inspect
from collections.abc import Callable, Mapping, Sequence
from functools import wraps

from roseau.load_flow.utils.helpers import warn_external


def deprecate_renamed_parameters[**P, T](
    replaced_names: Mapping[str, str], *, version: str, category: type[Warning] = FutureWarning
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to mark function parameters as deprecated due to being renamed.

    Use as follows::

        @deprecate_renamed_parameters({"old_name1": "new_name1", "old_name2": "new_name2"}, version="0.12.0")
        def my_func(new_name1, new_name2): ...
    """

    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for old_name, new_name in replaced_names.items():
                if old_name in kwargs:
                    func_name = function.__qualname__.removesuffix(".__init__").removesuffix(".__new__")
                    if new_name in kwargs:
                        raise TypeError(
                            f"{func_name}() got both {old_name!r} and {new_name!r} as arguments; "
                            f"{old_name!r} is deprecated, use {new_name!r} instead."
                        )
                    warn_external(
                        message=(
                            f"Argument {old_name!r} for {func_name}() is deprecated. It has been "
                            f"renamed to {new_name!r}."
                        ),
                        category=category,
                    )
                    kwargs[new_name] = kwargs.pop(old_name)
            return function(*args, **kwargs)

        wrapper.__signature__ = inspect.signature(function)  # type: ignore
        return wrapper

    return decorate


def deprecate_renamed_parameter[**P, T](
    old_name: str, new_name: str, *, version: str, category: type[Warning] = FutureWarning
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to mark a function parameter as deprecated due to being renamed.

    Use as follows::

        @deprecate_renamed_parameter("old_name", "new_name", version="0.12.0")
        def my_func(new_name): ...
    """
    return deprecate_renamed_parameters({old_name: new_name}, version=version, category=category)


def deprecate_nonkeyword_arguments[**P, T](
    allowed_args: Sequence[str] | None = None, message: str | None = None, *, version: str
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to deprecate the use of non-keyword arguments of a function.

    Args:
        allowed_args:
            The names of some first arguments of the decorated function that are allowed to be given
            as positional arguments. Should include "self" when decorating class methods. If set to
            ``None`` (default), equal to all arguments that do not have a default value.

        message:
            Optionally overwrite the default warning message.

        version:
            The roseau-Load-flow version number in which the warning is first issued. This argument
            is used to help developers determine when to remove the deprecated functionality.
    """
    assert not isinstance(allowed_args, str), "allowed_args should be a list or tuple of strings or None"

    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        old_sig = inspect.signature(function)

        if allowed_args is not None:
            allow_args = list(allowed_args)
        else:
            allow_args = [
                p.name
                for p in old_sig.parameters.values()
                if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty
            ]

        new_params = [
            p.replace(kind=p.KEYWORD_ONLY)
            if (p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.name not in allow_args)
            else p
            for p in old_sig.parameters.values()
        ]
        new_params.sort(key=lambda p: p.kind)

        new_sig = old_sig.replace(parameters=new_params)

        num_allowed_args = len(allow_args)
        if message is None:
            func_name = function.__qualname__.removesuffix(".__init__").removesuffix(".__new__")
            msg = f"All arguments of {func_name}()"
            if "self" in allow_args:
                allow_args.remove("self")
            if not allow_args:
                pass
            elif len(allow_args) == 1:
                msg += f" except for {allow_args[0]!r}"
            else:
                msg += f" except for {', '.join([f'{x!r}' for x in allow_args[:-1]])} and {allow_args[-1]!r}"
            msg += " will be keyword-only in the future. Use keyword arguments to silence this warning."
        else:
            msg = message

        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if len(args) > num_allowed_args:
                warn_external(message=msg, category=FutureWarning)
            return function(*args, **kwargs)

        wrapper.__signature__ = new_sig  # type: ignore
        return wrapper

    return decorate


def deprecate_parameter_as_multi_positional[**P, T](
    old_name: str, *, version: str
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to mark a function argument as deprecated due to being made multi-positional.

    Use as follows::

        @deprecate_parameter_as_multi_positional("param", version="0.10.0")
        def my_func(*param): ...
    """

    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                arg_value = kwargs.pop(old_name)
            except KeyError:
                return function(*args, **kwargs)

            warn_external(
                message=(
                    f"Passing {old_name!r} as a keyword argument is deprecated. Pass it as a "
                    "positional argument instead."
                ),
                category=FutureWarning,
            )

            if not isinstance(arg_value, Sequence) or isinstance(arg_value, str):
                arg_value = (arg_value,)
            elif not isinstance(arg_value, tuple):
                arg_value = tuple(arg_value)
            return function(*args, *arg_value, **kwargs)

        wrapper.__signature__ = inspect.signature(function)  # type: ignore
        return wrapper

    return decorate
