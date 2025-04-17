from collections.abc import Collection, Sized
from enum import StrEnum

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
