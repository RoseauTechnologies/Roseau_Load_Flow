import json
import logging
import re
import textwrap
import warnings
from abc import ABCMeta, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, NoReturn, Optional, TypeVar, Union, overload

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict, StrPath
from roseau.load_flow_engine.cy_engine import CyElement

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork
    from roseau.load_flow.single import ElectricalNetwork as SingleElectricalNetwork

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def _json_encoder_default(obj: object) -> object:
    """Numpy compatible JSON serialization hook."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif np.isscalar(obj) and pd.isna(obj):
        return None
    # raise the default error from the json module
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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

    _no_results = True
    _results_valid = False

    @classmethod
    @abstractmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        """Create an element from a dictionary created with :meth:`to_dict`.

        Note:
            This method does not work on all classes that define it as some of them require
            additional information to be constructed. It can only be safely used on the
            `ElectricNetwork`, `LineParameters` and `TransformerParameters` classes.

        Args:
            data:
                The dictionary containing the element's data.

            include_results:
                If True (default) and the results of the load flow are included in the dictionary,
                the results are also loaded into the element.

        Returns:
            The constructed element.
        """
        raise NotImplementedError

    @classmethod
    def from_json(cls, path: StrPath, *, include_results: bool = True) -> Self:
        """Construct an element from a JSON file created with :meth:`to_json`.

        Note:
            This method does not work on all classes that define it as some of them require
            additional information to be constructed. It can only be safely used on the
            `ElectricNetwork`, `LineParameters` and `TransformerParameters` classes.

        Args:
            path:
                The path to the network data file.

            include_results:
                If True (default) and the results of the load flow are included in the file,
                the results are also loaded into the element.

        Returns:
            The constructed element.
        """
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data=data, include_results=include_results)

    @abstractmethod
    def _to_dict(self, include_results: bool) -> JsonDict:
        """Return the element information as a dictionary format."""
        raise NotImplementedError

    def to_dict(self, *, include_results: bool = True) -> JsonDict:
        """Convert the element to a dictionary.

        Args:
            include_results:
                If True (default), the results of the load flow are included in the dictionary.
                If no results are available, this option is ignored.

        Returns:
            A JSON serializable dictionary with the element's data.
        """
        if include_results and self._no_results:
            include_results = False
        if include_results and not self._results_valid:
            msg = (
                f"Trying to convert {type(self).__name__} with invalid results to a dict. Either "
                f"call `en.solve_load_flow()` before converting or pass `include_results=False`."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_FLOW_RESULT)
        return self._to_dict(include_results=include_results)

    def to_json(self, path: StrPath, *, include_results: bool = True) -> Path:
        """Save this element to a JSON file.

        .. note::
            The path is `expanded`_ then `resolved`_ before writing the file.

        .. _expanded: https://docs.python.org/3/library/pathlib.html#pathlib.Path.expanduser
        .. _resolved: https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve

        .. warning::
            If the file exists, it will be overwritten.

        Args:
            path:
                The path to the output file to write the network to.

            include_results:
                If True (default), the results of the load flow are included in the JSON file.
                If no results are available, this option is ignored.

        Returns:
            The expanded and resolved path of the written file.
        """
        res = self.to_dict(include_results=include_results)
        output = json.dumps(res, ensure_ascii=False, indent=2, default=_json_encoder_default)
        # Collapse multi-line arrays of 2-to-4 elements into single line
        # e.g complex value represented as [real, imag] or rows of the z_line matrix
        output = re.sub(r"\[(?:\s+(\S+,))?(?:\s+?( \S+,))??(?:\s+?( \S+,))??\s+?( \S+)\s+]", r"[\1\2\3\4]", output)
        if not output.endswith("\n"):
            output += "\n"
        path = Path(path).expanduser().resolve()
        path.write_text(output)
        return path

    @abstractmethod
    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        """Return the results of the element as a dictionary format"""
        raise NotImplementedError

    def results_to_dict(self, full: bool = False) -> JsonDict:
        """Return the results of the element as a dictionary.

        The results dictionary of an element contains the ID of the element, its phases, and the
        result. For example, `bus.results_to_dict()` returns a dictionary with the form::

            {"id": "bus1", "phases": "an", "potentials": [[230.0, 0.0]]}

        Note that complex values (like `potentials` in the example above) are stored as list of
        [real part, imaginary part] so that it is JSON-serializable

        Using the `full` argument, `bus.results_to_dict(full=True)` leads to the following results::

            {"id": "bus1", "phases": "an", "potentials": [[230.0, 0.0]], "voltages": [[230.0, 0.0]]}

        The results dictionary of the network contains the results of all of its elements grouped
        by the element type. It has the form::

            {
                "buses": [bus1_dict, bus2_dict, ...],
                "lines": [line1_dict, line2_dict, ...],
                "transformers": [transformer1_dict, transformer2_dict, ...],
                "switches": [switch1_dict, switch2_dict, ...],
                "loads": [load1_dict, load2_dict, ...],
                "sources": [source1_dict, source2_dict, ...],
                "grounds": [ground1_dict, ground2_dict, ...],
                "potential_refs": [p_ref1_dict, p_ref2_dict, ...],
            }

        where each dict is produced by the element's `results_to_dict()` method.

        Args:
            full:
                If `True`, all the results are added in the resulting dictionary. `False` by default.

        Returns:
            The dictionary of results.
        """
        return self._results_to_dict(warning=True, full=full)

    def results_to_json(self, path: StrPath, *, full: bool = False) -> Path:
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

            full:
                If `True`, all the results are added in the resulting dictionary, including results computed from other
                results (such as voltages that could be computed from potentials). `False` by default.

        Returns:
            The expanded and resolved path of the written file.
        """
        dict_results = self._results_to_dict(warning=True, full=full)
        output = json.dumps(dict_results, indent=4, default=_json_encoder_default)
        output = re.sub(r"\[\s+(.*),\s+(.*)\s+]", r"[\1, \2]", output)
        path = Path(path).expanduser().resolve()
        if not output.endswith("\n"):
            output += "\n"
        path.write_text(output)
        return path


class NetworkElement(Identifiable, metaclass=ABCMeta):
    """An element belonging to a network"""

    def __init__(self, id: Id):
        super().__init__(id)
        self._connected_elements: list[NetworkElement] = []
        self._network: ElectricalNetwork | None = None
        self._cy_element: CyElement | None = None
        self._fetch_results = False
        self._no_results = True
        self._results_valid = True

    @property
    def network(self) -> Optional["ElectricalNetwork"]:
        """Return the network the element belong to (if any)."""
        return self._network

    def _set_network(self, value: Union["ElectricalNetwork", "SingleElectricalNetwork"] | None) -> None:
        """Network setter with the ability to set the network to `None`. This method must not be exposed through a
        traditional public setter. It is internally used in the `_connect` and `_disconnect` methods.

        Args:
            value:
                The new network for `self`. May also be None.
        """
        # The setter cannot be used to replace an existing network
        if self._network is not None and value is not None and self._network != value:
            self._raise_several_network()

        # Add/remove the element to the dictionaries of elements in the network
        if value is None:
            if self._network is not None:
                self._network._disconnect_element(element=self)
        else:
            value._connect_element(element=self)

        # Assign the new network to self
        self._network = value

        # In case of disconnection, do nothing to connected elements
        if value is None:
            return

        # Recursively call this method to the elements connected to self
        for e in self._connected_elements:
            if e.network == value:
                continue
            else:
                # Recursive call
                e._set_network(value)

    def _connect(self, *elements: "NetworkElement") -> None:
        """Connect this element to another element.

        Args:
            elements:
                The elements to connect to self.
        """
        # Get the common network. May raise exception
        network = self.network
        for element in elements:
            if network is None:
                network = element.network
            elif element.network is not None and element.network != network:
                element._raise_several_network()

        # Modify objects. Append to the connected_elements
        for element in elements:
            if element not in self._connected_elements:
                self._connected_elements.append(element)
            if self not in element._connected_elements:
                element._connected_elements.append(self)

        # Propagate the new network to `self` and other newly connected elements (recursively)`
        if network is not None:
            self._set_network(network)

    def _disconnect(self) -> None:
        """Remove all the connections with the other elements."""
        for element in self._connected_elements:
            element._connected_elements.remove(self)
        self._connected_elements = []
        self._set_network(None)
        if self._cy_element is not None:
            self._cy_element.disconnect()
            # The cpp element has been disconnected and can't be reconnected easily, it's safer to delete it
            self._cy_element = None

    def _invalidate_network_results(self) -> None:
        """Invalidate the network making the result"""
        if self.network is not None:
            self.network._results_valid = False

    def _res_getter(self, value: _T | None, warning: bool) -> _T:
        """A safe getter for load flow results.

        Args:
            value:
                The optional array(s) of results.

            warning:
                If True and if the results may be invalid (because of an invalid network), a warning log is emitted.

        Returns:
            The input if valid. May also emit a warning for potential invalid results.
        """
        if value is None:
            msg = (
                f"Results for {type(self).__name__} {self.id!r} are not available because the load "
                f"flow has not been run yet."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN)
        if warning and self.network is not None and not self.network._results_valid:
            warnings.warn(
                message=(
                    f"The results of {type(self).__name__} {self.id!r} may be outdated. Please re-run a load flow to "
                    "ensure the validity of results."
                ),
                category=UserWarning,
                # Ignore all private RLF stacks:
                # - this method
                # - _res_..._getter caller function
                # - res_... property
                # - ureg wrappers
                # TODO: dynamic stacklevel computation similar to pandas and matplotlib
                stacklevel=6,
            )
        self._fetch_results = False
        return value

    @staticmethod
    def _parse_geometry(geometry: str | dict[str, Any] | None) -> BaseGeometry | None:
        if geometry is None:
            return None
        elif isinstance(geometry, str):
            return shapely.from_wkt(geometry)
        else:
            return shape(geometry)

    def _raise_several_network(self) -> NoReturn:
        """Raise an exception when there are several networks involved during a connection of elements."""
        msg = f"The {type(self).__name__} {self.id!r} is already assigned to another network."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.SEVERAL_NETWORKS)


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
    def _filter_catalogue_str(value: str | re.Pattern[str], strings: pd.Series) -> "pd.Series[bool]": ...

    @overload
    @staticmethod
    def _filter_catalogue_str(value: str | re.Pattern[str], strings: list[str]) -> list[str]: ...

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
            result = vector.str.fullmatch(value)
        else:
            try:
                pattern = re.compile(pattern=value, flags=re.IGNORECASE)
                result = vector.str.fullmatch(pattern)
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
