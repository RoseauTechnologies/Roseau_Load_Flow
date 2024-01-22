import json
import logging
import re
import textwrap
from abc import ABCMeta, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Generic, NoReturn, TypeVar, overload

import pandas as pd
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict, StrPath

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class Identifiable(metaclass=ABCMeta):
    """An identifiable object."""

    def __init__(self, id: Id) -> None:
        if not isinstance(id, int | str):
            msg = f"{type(self).__name__} expected id to be int or str, got {type(id)}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_ID_TYPE)
        self.id = id

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"


class JsonMixin(metaclass=ABCMeta):
    """Mixin for classes that can be serialized to and from JSON."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: JsonDict) -> Self:
        """Create an element from a dictionary."""
        raise NotImplementedError

    @classmethod
    def from_json(cls, path: StrPath) -> Self:
        """Construct an electrical network from a json file created with :meth:`to_json`.

        Args:
            path:
                The path to the network data file.

        Returns:
            The constructed network.
        """
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data=data)

    @abstractmethod
    def to_dict(self, *, _lf_only: bool = False) -> JsonDict:
        """Return the element information as a dictionary format.

        Args:
            _lf_only:
                Internal argument, please do not use.
        """
        raise NotImplementedError

    def to_json(self, path: StrPath) -> Path:
        """Save the current network to a json file.

        .. note::
            The path is `expanded`_ then `resolved`_ before writing the file.

        .. _expanded: https://docs.python.org/3/library/pathlib.html#pathlib.Path.expanduser
        .. _resolved: https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve

        .. warning::
            If the file exists, it will be overwritten.

        Args:
            path:
                The path to the output file to write the network to.

        Returns:
            The expanded and resolved path of the written file.
        """
        res = self.to_dict()
        output = json.dumps(res, ensure_ascii=False, indent=2)
        output = re.sub(r"\[\s+(.*),\s+(.*)\s+]", r"[\1, \2]", output)
        if not output.endswith("\n"):
            output += "\n"
        path = Path(path).expanduser().resolve()
        path.write_text(output)
        return path

    def results_to_dict(self) -> JsonDict:
        """Return the results of the element as a dictionary format"""
        return self._results_to_dict(True)

    @abstractmethod
    def _results_to_dict(self, warning: bool) -> JsonDict:
        """Return the results of the element as a dictionary format"""
        raise NotImplementedError

    def results_to_json(self, path: StrPath) -> Path:
        """Write the results of the load flow to a json file.

        .. note::
            The path is `expanded`_ then `resolved`_ before writing the file.

        .. _expanded: https://docs.python.org/3/library/pathlib.html#pathlib.Path.expanduser
        .. _resolved: https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve

        .. warning::
            If the file exists, it will be overwritten.

        Args:
            path:
                The path to the output file to write the results to.

        Returns:
            The expanded and resolved path of the written file.
        """
        dict_results = self.results_to_dict()
        output = json.dumps(dict_results, indent=4)
        output = re.sub(r"\[\s+(.*),\s+(.*)\s+]", r"[\1, \2]", output)
        path = Path(path).expanduser().resolve()
        if not output.endswith("\n"):
            output += "\n"
        path.write_text(output)
        return path

    @abstractmethod
    def results_from_dict(self, data: JsonDict) -> None:
        """Fill an element with the provided results' dictionary."""
        raise NotImplementedError

    def results_from_json(self, path: StrPath) -> None:
        """Load the results of a load flow from a json file created by :meth:`results_to_json`.

        The results are stored in the network elements.

        Args:
            path:
                The path to the JSON file containing the results.
        """
        data = json.loads(Path(path).read_text())
        self.results_from_dict(data)


class CatalogueMixin(Generic[_T], metaclass=ABCMeta):
    """A mixin class for objects which can be built from a catalogue. It adds the `from_catalogue` class method."""

    @classmethod
    @abstractmethod
    def catalogue_path(cls) -> Path:
        """Get the path to the catalogue."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def catalogue_data(cls) -> _T:
        """Get the catalogue data."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_catalogue(cls, **kwargs) -> Self:
        """Build an instance from the catalogue.

        Keyword Args:
            Arguments that can be used to select the options of the instance to create.

        Returns:
            The instance of the selected object.
        """
        raise NotImplementedError

    @overload
    @staticmethod
    def _filter_catalogue_str(value: str | re.Pattern[str], strings: pd.Series) -> "pd.Series[bool]":
        ...

    @overload
    @staticmethod
    def _filter_catalogue_str(value: str | re.Pattern[str], strings: list[str]) -> list[str]:
        ...

    @staticmethod
    def _filter_catalogue_str(
        value: str | re.Pattern[str], strings: list[str] | pd.Series
    ) -> "pd.Series[bool] | list[str]":
        """Filter the catalogue using a string/regexp value.

        Args:
            value:
                The string or regular expression to use as a filter.

            strings:
                The catalogue data to filter. Either a :class:`pandas.Series` or a list of strings.

        Returns:
            The mask of matching results if `strings` is a :class:`pandas.Series`, otherwise
            the list of matching results.
        """
        vector = pd.Series(strings)
        if isinstance(value, re.Pattern):
            result = vector.str.match(value)
        else:
            try:
                pattern = re.compile(pattern=value, flags=re.IGNORECASE)
                result = vector.str.match(pattern)
            except re.error:
                # fallback to string comparison
                result = vector.str.lower() == value.lower()
        if isinstance(strings, pd.Series):
            return result
        else:
            return vector[result].tolist()

    @staticmethod
    def _raise_not_found_in_catalogue(
        value: object, name: str, name_plural: str, strings: pd.Series, query_msg_list: list[str]
    ) -> NoReturn:
        """Raise an exception when no element has been found in the catalogue.

        Args:
            value:
                The value that has been searched in the catalogue.

            name:
                The name of the element to display in the error message.

            name_plural:
                The plural form of the name of the element to display in the error message.

            strings:
                The catalogue data to filter.

            query_msg_list:
                The query information to display in the error message.
        """
        available_values = textwrap.shorten(", ".join(map(repr, strings.unique().tolist())), width=500)
        msg = f"No {name} matching {value} has been found"
        if query_msg_list:
            msg += f" for the query {', '.join(query_msg_list)}"
        msg += f". Available {name_plural} are {available_values}."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND)

    @staticmethod
    def _assert_one_found(found_data: Sequence[object], display_name: str, query_info: str) -> None:
        """Assert that only one element has been found in the catalogue.

        Args:
            found_data:
                The data found in the catalogue. If multiple elements have been found, they are
                displayed in the error message.

            display_name:
                The name of the element to display in the error message.

            query_info:
                The query information to display in the error message.
        """
        if len(found_data) == 1:
            return
        msg_middle = f"{display_name} matching the query ({query_info}) have been found"
        if len(found_data) == 0:
            msg = f"No {msg_middle}. Please look at the catalogue using the `get_catalogue` class method."
            code = RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND
        else:
            msg = f"Several {msg_middle}: {textwrap.shorten(', '.join(map(repr, found_data)), width=500)}."
            code = RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=code)
