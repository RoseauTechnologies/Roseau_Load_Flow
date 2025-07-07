from abc import ABCMeta, abstractmethod, update_abstractmethods
from collections.abc import Callable, Collection, Sized
from enum import StrEnum
from typing import Final, TypeVar

from roseau.load_flow.typing import Side

SIDE_INDEX: Final[dict[Side | None, int]] = {"HV": 0, "LV": 1, 1: 0, 2: 1, None: 0}
SIDE_SUFFIX: Final[dict[Side | None, str]] = {"HV": "_hv", "LV": "_lv", 1: "1", 2: "2", None: ""}
SIDE_DESC: Final[dict[Side | None, str]] = {
    "HV": "HV side ",
    "LV": "LV side ",
    1: "side (1) ",
    2: "side (2) ",
    None: "",
}

_NORM_TABLE = str.maketrans(".- /", "____")


def count_repr(items: Sized, /, singular: str, plural: str | None = None) -> str:
    """Singular/plural count representation: `1 bus` or `2 buses`."""
    n = len(items)
    if n == 1:
        return f"{n} {singular}"
    return f"{n} {plural if plural is not None else singular + 's'}"


def one_or_more_repr(items: Collection[object], /, singular: str, plural: str | None = None) -> tuple[str, str]:
    """Representation of one or more items: `Phase 'a' is` or `Phases ["a", "n"] are`."""
    n = len(items)
    if n == 1:
        return f"{singular} {next(iter(items))!r}", "is"
    return f"{plural if plural is not None else singular + 's'} {items!r}", "are"


def ensure_startsupper(s: str, /) -> str:
    """Ensure the string starts with an uppercase letter."""
    return s[:1].upper() + s[1:]


def id_sort_key(x: dict, /) -> tuple[str, str]:
    """Sorting key function for objects with an 'id' key."""
    return type(x["id"]).__name__, str(x["id"])


class CaseInsensitiveStrEnum(StrEnum):
    """A case-insensitive string enumeration with normalization.

    The special characters ``.- /`` are normalized to ``_`` in the enum members.

    Example::

        class AnEnum(CaseInsensitiveStrEnum):
            A_B = "a/b"
            TYPE_A = "type-A"
            FIRST_NAME = "first name"
            OBJ_ATTR = "obj.attr"


        AnEnum("A/B")  # -> AnEnum.A_B
        AnEnum("type-a")  # -> AnEnum.TYPE_A
        AnEnum("First Name")  # -> AnEnum.FIRST_NAME
        AnEnum("obj.ATTR")  # -> AnEnum.OBJ_ATTR
    """

    @classmethod
    def _missing_(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return cls[value.upper().translate(_NORM_TABLE)]
            except KeyError:
                pass
        return None


_ABCT = TypeVar("_ABCT", bound=ABCMeta)


@staticmethod
@abstractmethod
def _abstract_attr():
    """Placeholder used to mark abstract attributes in classes decorated with `abstractattrs`."""
    raise TypeError("abstract attributes are not callable")


def abstractattrs(*attrs: str) -> Callable[[_ABCT], _ABCT]:
    """Class decorator to mark attributes as abstract."""

    def decorator(cls: "_ABCT", /) -> "_ABCT":
        assert isinstance(cls, ABCMeta), "abstractattrs can only be used on ABC classes"
        for attr in attrs:
            if not hasattr(cls, attr):
                setattr(cls, attr, _abstract_attr)
        update_abstractmethods(cls)
        return cls

    return decorator
