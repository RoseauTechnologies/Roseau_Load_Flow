from collections.abc import Collection, Sized

from roseau.load_flow._compat import StrEnum


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


class CaseInsensitiveStrEnum(StrEnum):
    """A case-insensitive string enumeration."""

    @classmethod
    def _missing_(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        return None
