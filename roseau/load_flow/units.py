"""
Units registry used by Roseau Load Flow using the `pint`_ package.

.. class:: ureg

    The :class:`~pint.UnitRegistry` object to use in this project.

.. class:: Q_

    The :class:`~pint.Quantity` class to use in this project.

.. _pint: https://pint.readthedocs.io/en/stable/getting/overview.html
"""
from collections.abc import Callable, Iterable
from types import GenericAlias
from typing import TYPE_CHECKING, TypeVar, Union

from pint import Unit, UnitRegistry
from pint.facets.plain import PlainQuantity
from typing_extensions import TypeAlias

T = TypeVar("T")
FuncT = TypeVar("FuncT", bound=Callable)

ureg: UnitRegistry = UnitRegistry(
    preprocessors=[
        lambda s: s.replace("%", " percent "),
    ]
)
ureg.define("volt_ampere_reactive = 1 * volt_ampere = VAr")

if TYPE_CHECKING:
    Q_: TypeAlias = PlainQuantity[T]
else:
    Q_ = ureg.Quantity
    Q_.__class_getitem__ = classmethod(GenericAlias)


def ureg_wraps(
    ret: Union[str, Unit, None, Iterable[Union[str, Unit, None]]],
    args: Union[str, Unit, None, Iterable[Union[str, Unit, None]]],
    strict: bool = True,
) -> Callable[[FuncT], FuncT]:
    """Wraps a function to become pint-aware.

    Args:
        ureg:
            a UnitRegistry instance.
        ret:
            Units of each of the return values. Use `None` to skip argument conversion.
        args:
            Units of each of the input arguments. Use `None` to skip argument conversion.
        strict:
            Indicates that only quantities are accepted. (Default value = True)
    """
    return ureg.wraps(ret, args, strict)
