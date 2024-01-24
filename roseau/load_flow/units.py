"""
Units registry used by Roseau Load Flow using the `pint`_ package.

.. class:: ureg

    The :class:`pint.UnitRegistry` object to use in this project. You should not need to use it
    directly.

.. class:: Q_

    The :class:`pint.Quantity` class to use in this project. You can use it to provide quantities
    in units different from the default ones. For example, to create a constant power load of 1 MVA,
    you can do:

    >>> load = lf.PowerLoad("load", bus=bus, powers=Q_([1, 1, 1], "MVA"))

    which is equivalent to:

    >>> load = lf.PowerLoad("load", bus=bus, powers=[1000000, 1000000, 1000000])  # in VA

.. _pint: https://pint.readthedocs.io/en/stable/getting/overview.html
"""
from collections.abc import Callable, Iterable
from types import GenericAlias
from typing import TYPE_CHECKING, TypeAlias, TypeVar

from pint import Unit, UnitRegistry
from pint.facets.plain import PlainQuantity

from roseau.load_flow._wrapper import wraps

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
