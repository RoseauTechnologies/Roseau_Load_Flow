import logging
import warnings
from abc import ABC
from typing import Any, ClassVar, NoReturn, Optional, TYPE_CHECKING, TypeVar, Union

import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import Identifiable, JsonMixin

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

    def __init__(self, id: Id, **kwargs: Any) -> None:
        """Element constructor.

        Args:
            id:
                A unique ID of the element in the network. Two elements of the same type cannot
                have the same ID.
        """
        super().__init__(id)
        self.connected_elements: list[Element] = []
        self._network: Optional["ElectricalNetwork"] = None

    @property
    def network(self) -> Optional["ElectricalNetwork"]:
        """Return the network the element belong to (if any)."""
        return self._network

    @classmethod
    def _check_phases(cls, id: Id, **kwargs: str) -> None:
        name, phases = kwargs.popitem()  # phases, phases1 or phases2
        if phases not in cls.allowed_phases:
            msg = (
                f"{cls.__name__} of id {id!r} got invalid {name} {phases!r}, allowed values are: "
                f"{sorted(cls.allowed_phases)}"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)

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

        # Modify objects. Append to the connected_elements and assign the common network
        for element in elements:
            if element not in self.connected_elements:
                self.connected_elements.append(element)
            if self not in element.connected_elements:
                element.connected_elements.append(self)
            if element.network is None and network is not None:
                network._connect_element(element=element)

        if self._network is None and network is not None:
            network._connect_element(element=self)

    def _disconnect(self) -> None:
        """Remove all the connections with the other elements. This method can be used in a public `disconnect`
        method for"""
        for element in self.connected_elements:
            element.connected_elements.remove(self)
            if element.network is not None:
                element.network._disconnect_element(element=self)

        if self._network is not None:
            self.network._disconnect_element(element=self)

    def _invalidate_network_results(self) -> None:
        """Invalidate the network making the result"""
        if self.network is not None:
            self.network._results_valid = False

    def _res_getter(self, value: Optional[_T], warning: bool) -> _T:
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
            self._raise_load_flow_not_run()
        if warning:
            self._warn_invalid_results()
        return value

    @staticmethod
    def _parse_geometry(geometry: Union[str, None, Any]) -> Optional[BaseGeometry]:
        if geometry is None:
            return None
        elif isinstance(geometry, str):
            return shapely.from_wkt(geometry)
        else:
            return shape(geometry)

    def _raise_load_flow_not_run(self) -> NoReturn:
        """Raise an exception when accessing results and the load flow has not been run yet."""
        msg = (
            f"Results for {type(self).__name__} {self.id!r} are not available because the load "
            f"flow has not been run yet."
        )
        logger.error(msg)
        raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN)

    def _raise_several_network(self) -> NoReturn:
        """Raise an exception when there are several networks involved during a connection of elements."""
        msg = f"The {type(self).__name__} {self.id!r} is already assigned to another network."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.SEVERAL_NETWORKS)

    def _warn_invalid_results(self) -> None:
        """Warn when the network of `self` is invalid."""
        if self.network is not None and not self.network._results_valid:
            warnings.warn(
                message="The results of this element may be outdated. Please re-run a load flow to ensure "
                "the validity of results.",
                category=UserWarning,
                stacklevel=2,
            )
