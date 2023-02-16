import json
import logging
import re
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict, Self, StrPath

logger = logging.getLogger(__name__)


class Identifiable(metaclass=ABCMeta):
    """An identifiable object."""

    def __init__(self, id: Id) -> None:
        if not isinstance(id, (int, str)):
            msg = f"{type(self).__name__} expected id to be int or str, got {type(id)}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_ID_TYPE)
        self.id = id

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"


class JsonMixin(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def from_dict(cls, data: JsonDict, *args: Any) -> Self:
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
    def to_dict(self) -> JsonDict:
        """Return the element information as a dictionary format."""
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
        output = json.dumps(res, ensure_ascii=False, indent=4)
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
