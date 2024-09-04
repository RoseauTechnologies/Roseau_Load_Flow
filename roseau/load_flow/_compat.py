import sys
from enum import Enum

from typing_extensions import Self

if sys.version_info >= (3, 11):  # pragma: no-cover-if-py-lt-311
    from enum import StrEnum as StrEnum
else:  # pragma: no-cover-if-py-gte-311

    class StrEnum(str, Enum):
        """
        Enum where members are also (and must be) strings. This is a backport of
        `enum.StrEnum` from Python 3.11.
        """

        def __new__(cls, *values) -> Self:
            "values must already be of type `str`"
            if len(values) > 3:
                raise TypeError(f"too many arguments for str(): {values!r}")
            if len(values) == 1 and not isinstance(values[0], str):
                # it must be a string
                raise TypeError(f"{values[0]!r} is not a string")
            if len(values) >= 2 and not isinstance(values[1], str):
                # check that encoding argument is a string
                raise TypeError(f"encoding must be a string, not {values[1]!r}")
            if len(values) == 3 and not isinstance(values[2], str):
                # check that errors argument is a string
                raise TypeError(f"errors must be a string, not {values[2]!r}")
            value = str(*values)
            member = str.__new__(cls, value)
            member._value_ = value
            return member

        def __str__(self) -> str:
            return str.__str__(self)

        def _generate_next_value_(name, start, count, last_values) -> str:  # noqa: N805
            """
            Return the lower-cased version of the member name.
            """
            return name.lower()
