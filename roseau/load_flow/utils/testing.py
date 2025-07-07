import re
import warnings
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from functools import cache
from typing import ParamSpec, TypeVar

from roseau.load_flow.utils.mixins import AbstractNetwork

P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def check_result_warning(match: str | re.Pattern[str]) -> Generator[None]:
    __tracebackhide__ = True  # Hide traceback in pytest output
    with warnings.catch_warnings(record=True) as records:
        yield
    (record,) = records  # One record expected
    assert isinstance(record.message, Warning)
    assert re.match(match, record.message.args[0])
    assert record.category is UserWarning


def invoke_result_access(
    en_or_elm: object, res_name: str, func: Callable[P, AbstractContextManager[R]], /, *args: P.args, **kwargs: P.kwargs
) -> R:
    """Invoke a context manager when accessing a result on a network or element.

    This function is used in the tests to ensure result access emits proper warnings or exceptions.

    Args:
        en_or_elm:
            The electrical network or element to access the result on.

        res_name:
            The name of the result attribute or method to access.

        func:
            A context manager callable that will be called with the provided arguments around the
            result access (e.g. `pytest.raises`).

        *args:
            Positional arguments to pass to the context manager function.

        **kwargs:
            Keyword arguments to pass to the context manager function.
    """
    __tracebackhide__ = True  # Hide traceback in pytest output
    try:
        with func(*args, **kwargs) as ctx:
            attr = getattr(en_or_elm, res_name)
            if callable(attr):
                attr()
    except BaseException as e:
        msg = f"While accessing '{res_name}' on {en_or_elm.__class__} object"
        if hasattr(en_or_elm, "id"):
            msg += f" with id '{en_or_elm.id}'"  # type: ignore
        e.add_note(msg)
        raise
    return ctx


@cache
def get_result_names(en_or_elm_class: type[object], /) -> Generator[str]:
    """Access all results on an electrical network using a context manager."""
    assert isinstance(en_or_elm_class, type), "en_or_elm_class must be a class"
    yield from (attr for attr in dir(en_or_elm_class) if attr.startswith("res_"))


def access_elements_results(
    en: "AbstractNetwork", func: Callable[P, AbstractContextManager[R]], /, *args: P.args, **kwargs: P.kwargs
) -> Generator[R]:
    for element_type, elements in en._elements_by_type.items():
        for element in elements.values():
            # Invoke the result access for each element
            for result_name in get_result_names(type(element)):
                # Check if the result access should be skipped
                if element_type == "bus":
                    if result_name == "res_violated" and element.min_voltage is None and element.max_voltage is None:
                        continue  # No min or max voltages so no call to results
                    if result_name.startswith("res_voltage_level") and element.nominal_voltage is None:
                        continue  # No nominal voltage so no call to results
                elif element_type == "line":
                    if result_name == "res_violated" or result_name == "res_loading":
                        continue  # No ampacities
                    if ("shunt" in result_name or "ground" in result_name) and not element.with_shunt:
                        continue  # No results if no shunt
                elif element_type == "load":
                    if result_name.startswith("res_flexible") and not element.is_flexible:
                        continue

                yield invoke_result_access(element, result_name, func, *args, **kwargs)

            # Other results for sides of the element
            if element_type in ("line", "switch", "transformer"):
                for result_name in get_result_names(type(element.side1)):
                    if "shunt" in result_name and not element.with_shunt:
                        continue
