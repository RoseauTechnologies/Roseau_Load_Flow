import json
import logging
import re
import textwrap
import warnings
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from importlib import resources
from pathlib import Path
from typing import Any, ClassVar, Generic, NoReturn, Self, TypeVar, overload

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from roseau.load_flow._solvers import AbstractSolver
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import CRSLike, Id, JsonDict, MapOrSeq, Solver, StrPath
from roseau.load_flow.utils.exceptions import find_stack_level
from roseau.load_flow.utils.helpers import abstractattrs
from roseau.load_flow_engine.cy_engine import CyElectricalNetwork, CyElement

logger = logging.getLogger(__name__)

_T = TypeVar("_T")
_E = TypeVar("_E", bound="AbstractElement")
_E_co = TypeVar("_E_co", bound="AbstractElement", covariant=True)
_N_co = TypeVar("_N_co", bound="AbstractNetwork", covariant=True)
_CyE_co = TypeVar("_CyE_co", bound=CyElement, default=CyElement, covariant=True)


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


@abstractattrs("is_multi_phase")
class RLFObject(metaclass=ABCMeta):
    """Base class for all objects in the library."""

    is_multi_phase: ClassVar[bool]
    """Is the object multi-phase?"""


class Identifiable(RLFObject, metaclass=ABCMeta):
    """An identifiable object."""

    @abstractmethod  # trick to prevent instantiation of the abstract class
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

            {"id": "bus1", "phases": "an", "potentials": [[230.0, 0.0], [0.0, 0.0]]}

        Note that complex values (like `potentials` in the example above) are stored as list of
        [real part, imaginary part] so that it is JSON-serializable

        Using the `full` argument, `bus.results_to_dict(full=True)` leads to the following results::

            {"id": "bus1", "phases": "an", "potentials": [[230.0, 0.0], [0.0, 0.0]], "voltages": [[230.0, 0.0]]}

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
                result = vector.str.fullmatch(pattern) | (vector.str.lower() == value.lower())
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


@abstractattrs("element_type")
class AbstractElement(Identifiable, JsonMixin, Generic[_N_co, _CyE_co]):
    """An abstract class of an element in an Electrical network."""

    element_type: ClassVar[str]
    """The type of the element. It is a string like ``"load"`` or ``"line"`` etc."""

    @abstractmethod
    def __init__(self, id: Id) -> None:
        """AbstractElement constructor.

        Args:
            id:
                A unique ID of the element in the network. Two elements of the same type cannot
                have the same ID.
        """
        self._cy_initialized = False
        super().__init__(id)
        self._connected_elements: list[AbstractElement[_N_co, Any]] = []
        self._network: _N_co | None = None
        self._cy_element: _CyE_co
        self._fetch_results = False
        self._no_results = True
        self._results_valid = True
        self._element_info = f"{self.element_type} {id!r}"  # for logging

    def __setattr__(self, name, value):
        if name == "_cy_element":
            self._cy_initialized = True
        return super().__setattr__(name, value)

    def __delattr__(self, name):
        if name == "_cy_element":
            self._cy_initialized = False
        return super().__delattr__(name)

    @property
    def network(self) -> _N_co | None:
        """Return the network the element belong to (if any)."""
        return self._network

    def _set_network(self, value: _N_co | None) -> None:
        """Network setter with the ability to set the network to `None`.

        This method must not be exposed through a traditional public setter. It is internally used
        in the `_connect` and `_disconnect` methods.

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
            if value.is_multi_phase != self.is_multi_phase:
                phases = {True: "multi-phase", False: "single-phase"}
                msg = (
                    f"Cannot connect {phases[self.is_multi_phase]} {self._element_info} to "
                    f"{phases[value.is_multi_phase]} network."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
            value._connect_element(element=self)

        # Assign the new network to self
        self._network = value

        # In case of disconnection, do nothing to connected elements
        if value is None:
            return

        # Recursively call this method to the elements connected to self
        for e in self._connected_elements:
            if e._network == value:
                continue
            else:
                # Recursive call
                e._set_network(value)

    def _connect(self, *elements: "AbstractElement[_N_co, CyElement]") -> None:
        """Connect this element to another element.

        Args:
            elements:
                The elements to connect to self.
        """
        # Get the common network. May raise exception
        network = self._network
        for element in elements:
            if network is None:
                network = element._network
            elif element._network is not None and element._network != network:
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
        if self._cy_initialized:
            self._cy_element.disconnect()
            # The cpp element has been disconnected and can't be reconnected easily, it's safer to delete it
            del self._cy_element

    def _invalidate_network_results(self) -> None:
        """Invalidate the network making the result"""
        if self._network is not None:
            self._network._results_valid = False

    @abstractmethod
    def _refresh_results(self) -> None:
        """Refresh the results of the element."""
        raise NotImplementedError

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
        if warning and self._network is not None and not self._network._results_valid:
            warnings.warn(
                message=(
                    f"The results of {type(self).__name__} {self.id!r} may be outdated. Please re-run a load flow to "
                    "ensure the validity of results."
                ),
                category=UserWarning,
                stacklevel=find_stack_level(),
            )
        self._fetch_results = False
        return value

    def _check_geometry(self, geometry: BaseGeometry | None) -> BaseGeometry | None:
        """Check if the geometry is a valid shapely geometry."""
        # We couldn't use the public class shapely.Geometry because it has no attributes
        # Change if this ticket is resolved: https://github.com/shapely/shapely/issues/2166
        if geometry is None:
            return None
        if not isinstance(geometry, BaseGeometry):
            msg = (
                f"The geometry of {self._element_info} is not a valid shapely geometry. Got {type(geometry).__name__}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)
        return geometry

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


class AbstractNetwork(RLFObject, JsonMixin, Generic[_E_co]):
    """An abstract class of an electrical network."""

    _DEFAULT_SOLVER: Solver = "newton_goldstein"

    @abstractmethod
    def __init__(self, *, crs: CRSLike | None = None) -> None:
        # Attributes initialized in subclasses
        self._no_results: bool
        self._results_valid: bool
        self._elements_by_type: dict[str, dict[Id, _E_co]]
        # Other attributes
        self._elements: list[_E_co] = []
        self._has_loop = False
        self._has_floating_neutral = False
        self._check_validity(constructed=True)
        self._create_network()
        self._valid = True
        self._solver = AbstractSolver.from_dict(data={"name": self._DEFAULT_SOLVER, "params": {}}, network=self)
        self.crs: CRSLike | None = crs

        # Track parameters to check for duplicates
        self._parameters: dict[str, dict[Id, Identifiable]] = {"line": {}, "transformer": {}}
        for line in self._elements_by_type["line"].values():
            self._add_parameters("line", line.parameters)  # type: ignore
        for transformer in self._elements_by_type["transformer"].values():
            self._add_parameters("transformer", transformer.parameters)  # type: ignore

    @classmethod
    def from_element(cls, initial_bus: AbstractElement, crs: CRSLike | None = None) -> Self:
        """Construct the network from only one element (bus) and add the others automatically.

        Args:
            initial_bus:
                Any bus of the network. The network is constructed from this bus and all the
                elements connected to it. This is usually the main source bus of the network.

        crs:
            An optional Coordinate Reference System to use with geo data frames. Can be anything
            accepted by geopandas and pyproj, such as an authority string or WKT string.

        Returns:
            The network constructed from the given bus and all the elements connected to it.
        """
        elements_by_type = defaultdict(list)
        elements: list[AbstractElement] = [initial_bus]
        visited_elements: set[AbstractElement] = set()
        while elements:
            e = elements.pop(-1)
            visited_elements.add(e)
            elements_by_type[e.element_type].append(e)
            for connected_element in e._connected_elements:
                if connected_element not in visited_elements and connected_element not in elements:
                    elements.append(connected_element)
        elements_kwargs = {
            "buses": elements_by_type["bus"],
            "lines": elements_by_type["line"],
            "transformers": elements_by_type["transformer"],
            "switches": elements_by_type["switch"],
            "loads": elements_by_type["load"],
            "sources": elements_by_type["source"],
        }
        if cls.is_multi_phase:
            elements_kwargs["potential_refs"] = elements_by_type["potential ref"]
            elements_kwargs["grounds"] = elements_by_type["ground"]
            elements_kwargs["ground_connections"] = elements_by_type["ground connection"]
        return cls(**elements_kwargs, crs=crs)

    def solve_load_flow(
        self,
        max_iterations: int = 20,
        tolerance: float = 1e-6,
        warm_start: bool = True,
        solver: Solver = _DEFAULT_SOLVER,
        solver_params: JsonDict | None = None,
    ) -> tuple[int, float]:
        """Solve the load flow for this network.

        To get the results of the load flow for the whole network, use the `res_` properties on the
        network (e.g. ``print(net.res_buses``). To get the results for a specific element, use the
        `res_` properties on the element (e.g. ``print(net.buses["bus1"].res_potentials)``.

        You need to activate the license before calling this method. You may set the environment
        variable ``ROSEAU_LOAD_FLOW_LICENSE_KEY`` to your license key and it will be picked
        automatically when calling this method. See the :ref:`license` page for more information.

        Args:
            max_iterations:
                The maximum number of allowed iterations.

            tolerance:
                Tolerance needed for the convergence.

            warm_start:
                If true (the default), the solver is initialized with the potentials of the last
                successful load flow result (if any). Otherwise, the potentials are reset to their
                initial values.

            solver:
                The name of the solver to use for the load flow. The options are:

                - ``newton``: The classical *Newton-Raphson* method.
                - ``newton_goldstein``: The *Newton-Raphson* method with the *Goldstein and Price*
                  linear search algorithm. It generally has better convergence properties than the
                  classical Newton-Raphson method. This is the default.
                - ``backward_forward``: the *Backward-Forward Sweep* method. It usually executes
                  faster than the other approaches but may exhibit weaker convergence properties. It
                  does not support meshed networks or floating neutrals.

            solver_params:
                A dictionary of parameters used by the solver. Available parameters depend on the
                solver chosen. For more information, see the :ref:`solvers` page.

        Returns:
            The number of iterations performed and the residual error at the last iteration.
        """
        if not self._valid:
            self._check_validity(constructed=False)
            self._create_network()  # <-- calls _propagate_voltages, no warm start
            self._solver.update_network(self)

        # Update solver
        if solver != self._solver.name:
            solver_params = solver_params if solver_params is not None else {}
            self._solver = AbstractSolver.from_dict(data={"name": solver, "params": solver_params}, network=self)
        elif solver_params is not None:
            self._solver.update_params(solver_params)

        if not warm_start:
            self._reset_inputs()

        iterations, residual = self._solver.solve_load_flow(max_iterations=max_iterations, tolerance=tolerance)
        self._no_results = False

        # Lazily update the results of the elements
        for element in self._elements:
            element._fetch_results = True
            element._no_results = False

        # The results are now valid
        self._results_valid = True

        return iterations, residual

    @property
    def buses_clusters(self) -> list[set[Id]]:
        """Clusters of buses connected by lines and switches.

        Each cluster is a set of bus IDs.

        This can be useful to isolate parts of the network for localized analysis. For example, to
        study a LV subnetwork of a MV feeder.

        See Also:
            :meth:`Bus.get_connected_buses() <roseau.load_flow.models.Bus.get_connected_buses>`: Get
            the buses in the same galvanically isolated section as a certain bus.
        """
        visited: set[Id] = set()
        result: list[set[Id]] = []
        for bus in self._elements_by_type["bus"].values():
            if bus.id in visited:
                continue
            bus_cluster = set(bus.get_connected_buses())  # type: ignore
            visited |= bus_cluster
            result.append(bus_cluster)
        return result

    @staticmethod
    def _elements_as_dict(elements: MapOrSeq[_E], error_code: RoseauLoadFlowExceptionCode) -> dict[Id, _E]:
        """Convert a sequence or a mapping of elements to a dictionary of elements with their IDs as keys."""
        typ = error_code.name.removeprefix("BAD_").removesuffix("_ID").replace("_", " ")
        elements_dict: dict[Id, _E] = {}
        if isinstance(elements, Mapping):
            for element_id, element in elements.items():
                if element.id != element_id:
                    msg = (
                        f"{typ.capitalize()} ID {element.id!r} does not match its key in the dictionary {element_id!r}."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg, code=error_code)
                elements_dict[element_id] = element
        else:
            for element in elements:
                if element.id in elements_dict:
                    msg = f"Duplicate {typ.lower()} ID {element.id!r} in the network."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg, code=error_code)
                elements_dict[element.id] = element
        return elements_dict

    @abstractmethod
    def _add_ground_connections(self, element: AbstractElement[Self]) -> None:
        """Add automatic ground connections to the network."""
        # Currently only single-phase networks have automatic ground connections but this will change
        raise NotImplementedError

    def _connect_element(self, element: _E_co) -> None:  # type: ignore
        """Connect an element to the network.

        When an element is added to the network, extra processing is done to keep the network valid.
        This method is used in the by the `network` setter of `Element` instances to add the element
        to the internal dictionary of `self`.

        Args:
            element:
                The element to add. Only lines, loads, buses and sources can be added.
        """
        # The C++ electrical network and the tape will be recomputed
        if not isinstance(element, AbstractElement) or (et := element.element_type) not in self._elements_by_type:
            msg = f"Unknown element {element!r} cannot be added to the network."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        disconnectable = et in ("load", "source")
        self._add_element_to_dict(element, self._elements_by_type[et], disconnectable=disconnectable)
        if et in ("line", "transformer"):
            self._add_parameters(et, element.parameters)  # type: ignore
        self._add_ground_connections(element)
        self._valid = False
        self._results_valid = False

    def _disconnect_element(self, element: _E_co) -> None:  # type: ignore
        """Remove an element of the network.

        When an element is removed from the network, extra processing is needed to keep the network
        valid. This method is used in the by the `network` setter of `Element` instances (when the
        provided network is `None`) to remove the element to the internal dictionary of `self`.

        Args:
            element:
                The element to disconnect.
        """
        # The C++ electrical network and the tape will be recomputed
        et = element.element_type
        if et in ("load", "source"):
            self._elements_by_type[et].pop(element.id)
        else:
            if et in ("bus", "transformer", "line", "switch"):
                msg = f"{element!r} is a {et} and cannot be disconnected from a network."
            else:
                msg = f"{element!r} is not a valid load or source."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        element._network = None
        self._valid = False
        self._results_valid = False

    def _add_parameters(self, element_type: str, params: Identifiable) -> None:
        params_map = self._parameters[element_type]
        if params.id not in params_map:
            params_map[params.id] = params
        elif params is not params_map[params.id]:
            msg = (
                f"{element_type.capitalize()} parameters IDs must be unique in the network. "
                f"ID {params.id!r} is used by several {element_type} parameters objects."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_ID)

    def _remove_parameters(self, element_type: str, params_id: Id) -> None:
        del self._parameters[element_type][params_id]

    def _add_element_to_dict(self, element: _E, to: dict[Id, _E], disconnectable: bool = False) -> None:
        if element.id in to and (old := to[element.id]) is not element:
            element._disconnect()  # Don't leave it lingering in other elements _connected_elements
            old_type = type(old).__name__
            prefix = "An" if old_type[0] in "AEIOU" else "A"
            msg = f"{prefix} {old_type} of ID {element.id!r} is already connected to the network."
            if disconnectable:
                msg += " Disconnect the old element first if you meant to replace it."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        to[element.id] = element
        element._network = self

    @abstractmethod
    def _get_has_floating_neutral(self) -> bool:
        raise NotImplementedError

    def _create_network(self) -> None:
        """Create the Cython and C++ electrical network of all the passed elements."""
        self._valid = True
        self._propagate_voltages()
        self._has_floating_neutral = self._get_has_floating_neutral()
        cy_elements = [e._cy_element for e in self._elements]
        self._cy_electrical_network = CyElectricalNetwork(elements=np.array(cy_elements), nb_elements=len(cy_elements))

    def _check_validity(self, constructed: bool) -> None:
        """Check the validity of the network to avoid having a singular jacobian matrix. It also assigns the `self`
        to the network field of elements.

        Args:
            constructed:
                True if the network is already constructed, and we have added an element, False
                otherwise.
        """
        elements = {e for collection in self._elements_by_type.values() for e in collection.values()}

        if not elements:
            msg = "Cannot create a network without elements."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.EMPTY_NETWORK)

        # Temporarily print a better error message for missing ground_connections to help with the
        # transition. TODO remove this special case in version 0.15.0
        grounds = [e for e in elements if e.element_type == "ground"]
        ground_connections = [e for e in elements if e.element_type == "ground connection"]
        missing_gc = next((gc for g in grounds for gc in g.connections), None)  # type: ignore
        if not ground_connections and missing_gc is not None:
            gc_hint = "ground.connections" if len(grounds) == 1 else "[gc for g in grounds for gc in g.connections]"
            msg = (
                f"It looks like you forgot to add the ground connections to the network. Either use "
                f"`ElectricalNetwork.from_element()` to create the network or add the ground connections "
                f"manually, e.g: `ElectricalNetwork(..., ground_connections={gc_hint})`."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT)

        found_source = False
        for element in elements:
            # Check connected elements and check network assignment
            for adj_element in element._connected_elements:
                if adj_element not in elements:
                    msg = (
                        f"{type(adj_element).__name__} element ({adj_element.id!r}) is connected "
                        f"to {type(element).__name__} element ({element.id!r}) but "
                    )
                    if constructed:
                        msg += "was not passed to the ElectricalNetwork constructor."
                    else:
                        msg += "has not been added to the network. It must be added with 'connect'."
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT)

            # Check that there is at least a `VoltageSource` element in the network
            if element.element_type == "source":
                found_source = True

        # Raises an error if no voltage sources
        if not found_source:
            msg = "There is no voltage source provided in the network, you must provide at least one."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE)

        # Check the potential references
        self._check_ref(elements)

        # Assign the network
        for element in elements:
            if element.network is None:
                element._network = self
            elif element.network != self:
                element._raise_several_network()

    def _reset_inputs(self) -> None:
        """Reset the input vector used for the first step of the newton algorithm to its initial value."""
        if self._solver is not None:
            self._solver.reset_inputs()

    @abstractmethod
    def _propagate_voltages(self) -> None:
        """Propagate the sources voltages to set uninitialized potentials of buses and compute self._elements."""
        raise NotImplementedError

    def _check_connectivity(self, visited_elements: Collection[_E_co]) -> None:
        """Check that all the elements are connected to a voltage source."""
        if len(visited_elements) < sum(map(len, self._elements_by_type.values())):
            unconnected_elements = [
                e
                for elements in self._elements_by_type.values()
                for e in elements.values()
                if e not in visited_elements
            ]
            printable_elements = textwrap.wrap(
                ", ".join(f"{type(e).__name__}({e.id!r})" for e in unconnected_elements), 500
            )
            msg = f"The elements {printable_elements} are not electrically connected to a voltage source."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.POORLY_CONNECTED_ELEMENT)

    @classmethod
    @abstractmethod
    def _check_ref(cls, elements: Iterable[_E_co]) -> None:
        raise NotImplementedError

    def _check_valid_results(self) -> bool:
        """Check that the results exist and warn if they are invalid."""
        if self._no_results:
            msg = "The load flow results are not available because the load flow has not been run yet."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN)

        if not self._results_valid:
            warnings.warn(
                message=(
                    "The results of this network may be outdated. Please re-run a load flow to "
                    "ensure the validity of results."
                ),
                category=UserWarning,
                stacklevel=find_stack_level(),
            )
            return False
        return True

    #
    # DGS interface
    #
    @classmethod
    @abstractmethod
    def _from_dgs(cls, data: Mapping[str, Any], /, use_name_as_id: bool = False) -> Self:
        raise NotImplementedError

    @classmethod
    def dgs_export_definition_folder_path(cls) -> Path:
        """Returns the path to the DGS pfd file to use as "Export Definition Folder"."""
        return Path(resources.files("roseau.load_flow") / "data" / "io" / "DGS-RLF.pfd").expanduser().absolute()  # type: ignore

    @classmethod
    def from_dgs_dict(cls, data: Mapping[str, Any], /, use_name_as_id: bool = False) -> Self:
        """Construct an electrical network from a json DGS file (PowerFactory).

        Only JSON format of DGS is currently supported. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.

        Args:
            data:
                The dictionary containing the network DGS data.

            use_name_as_id:
                If True, use the name of the elements (the ``loc_name`` field) as their id. Otherwise,
                use the id from the DGS file (the ``FID`` field). Only use if you are sure the names
                are unique. Default is False.

        Returns:
            The constructed network.
        """
        return cls._from_dgs(data, use_name_as_id=use_name_as_id)

    @classmethod
    def from_dgs_file(cls, path: StrPath, *, use_name_as_id: bool = False, encoding: str | None = None) -> Self:
        """Construct an electrical network from a json DGS file (PowerFactory).

        Only JSON format of DGS is currently supported. See the
        :ref:`Data Exchange page <data-exchange-power-factory>` for more information.

        Args:
            path:
                The path to the network DGS data file.

            use_name_as_id:
                If True, use the name of the elements (the ``loc_name`` field) as their id. Otherwise,
                use the id from the DGS file (the ``FID`` field). Only use if you are sure the names
                are unique. Default is False.

            encoding:
                The encoding of the file to be passed to the `open` function.

        Returns:
            The constructed network.
        """
        with open(path, encoding=encoding) as f:
            data = json.load(f)
        return cls._from_dgs(data, use_name_as_id=use_name_as_id)
