import logging
import warnings
from abc import ABC
from typing import TYPE_CHECKING, Any, ClassVar, NoReturn, Optional, TypeVar

import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import Identifiable, JsonMixin
from roseau.load_flow_engine.cy_engine import CyElement

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class Element(ABC, Identifiable, JsonMixin):
    """An abstract class of an element in an Electrical network."""

    allowed_phases: ClassVar[frozenset[str]]  # frozenset for immutability and uniqueness
    """The allowed phases for this element type.

    It is a frozen set of strings like ``"abc"`` or ``"an"`` etc. The order of the phases is
    important. For a full list of supported phases, use ``print(<Element class>.allowed_phases)``.
    """

    def __init__(self, id: Id) -> None:
        """Element constructor.

        Args:
            id:
                A unique ID of the element in the network. Two elements of the same type cannot
                have the same ID.
        """
        if type(self) is Element:
            raise TypeError("Can't instantiate abstract class Element")
        super().__init__(id)
        self._connected_elements: list[Element] = []
        self._network: ElectricalNetwork | None = None
        self._cy_element: CyElement | None = None
        self._fetch_results = False
        self._no_results = True
        self._results_valid = True

    @property
    def network(self) -> Optional["ElectricalNetwork"]:
        """Return the network the element belong to (if any)."""
        return self._network

    @classmethod
    def _check_phases(cls, id: Id, allowed_phases: frozenset[str] | None = None, **kwargs: str) -> None:
        if allowed_phases is None:
            allowed_phases = cls.allowed_phases
        name, phases = kwargs.popitem()  # phases, phases1 or phases2
        if phases not in allowed_phases:
            msg = (
                f"{cls.__name__} of id {id!r} got invalid {name} {phases!r}, allowed values are: "
                f"{sorted(allowed_phases)}"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)

    def _set_network(self, value: Optional["ElectricalNetwork"]) -> None:
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

    def _connect(self, *elements: "Element") -> None:
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
