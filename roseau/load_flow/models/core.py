import logging
import warnings
from abc import ABC
from typing import Any, ClassVar, NoReturn, Optional, TYPE_CHECKING, TypeVar, Union

import numpy as np
import shapely.wkt
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import BranchType
from roseau.load_flow.utils.mixins import Identifiable, JsonMixin

if TYPE_CHECKING:
    from roseau.load_flow.models.buses import Bus
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
    def _check_phases(cls, id: str, **kwargs: str) -> None:
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
            )


class PotentialRef(Element):
    """A potential reference.

    This element will set the reference of the potentials in a network. Only one potential
    reference per galvanically isolated section of the network can be set. The potential reference
    can be set on any bus or ground elements. If set on a bus with no neutral and without
    specifying the phase, the reference will be set as ``Va + Vb + Vc = 0``. For other buses, the
    default is ``Vn = 0``.
    """

    allowed_phases = frozenset({"a", "b", "c", "n"})

    def __init__(self, id: Id, element: Union["Bus", "Ground"], *, phase: Optional[str] = None, **kwargs: Any) -> None:
        """PotentialRef constructor.

        Args:
            id:
                A unique ID of the potential reference in the network references.

            element:
                The bus or ground element to set as a potential reference.

            phase:
                The phase of the bus to set as a potential reference. Cannot be used with a ground.
                If the element passed is a bus and the phase is not given, the neutral will be used
                if the bus has a neutral otherwise the equation ``Va + Vb + Vc = 0`` of the bus
                sets the potential reference.
        """
        from roseau.load_flow.models.buses import Bus  # TODO refactor potential ref and ground

        super().__init__(id, **kwargs)
        if isinstance(element, Bus):
            if phase is None:
                phase = "n" if "n" in element.phases else None
            else:
                self._check_phases(id, phases=phase)
        elif isinstance(element, Ground):
            if phase is not None:
                msg = f"Potential reference {self.id!r} connected to the ground cannot have a phase."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            msg = f"Potential reference {self.id!r} is connected to {element!r} which is not a ground nor a bus."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        self._connect(element)
        self.phase = phase

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, element={self.connected_elements[0]!r}, phase={self.phase!r})"

    @property
    def res_current(self) -> complex:
        """The sum of the currents of the connection associated to the potential reference.

        This sum should be equal to 0 after the load flow.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: JsonDict) -> "PotentialRef":
        return cls(data["id"], data["element"], phase=data.get("phases"))

    def to_dict(self) -> JsonDict:
        from roseau.load_flow.models.buses import Bus  # TODO refactor potential ref and ground

        res = {"id": self.id}
        e = self.connected_elements[0]
        if isinstance(e, Bus):
            res["bus"] = e.id
            res["phases"] = self.phase
        elif isinstance(e, Ground):
            res["ground"] = e.id
        else:
            assert False, f"Unexpected element type {type(e).__name__}"
        return res


class Ground(Element):
    """This element defines the ground.

    Only buses and lines that have shunt components can be connected to a ground.

    1. Connecting to a bus:

       To connect a ground to a bus on a given phase, use the :meth:`Ground.connect` method.
       This method lets you specify the bus to connect to as well as the phase of the connection.
       If the bus has a neutral and the phase is not specified, the ground will be connected to the
       neutral, otherwise, an error will be raised because the phase is needed.

    2. Connecting to a line with shunt components:

       To connect a ground to a line with shunt components, pass the ground object to the
       :class:`Line` constructor. Note that the ground connection is mandatory for shunt lines.
    """

    allowed_phases = frozenset({"a", "b", "c", "n"})

    def __init__(self, id: Id, **kwargs: Any) -> None:
        """Ground constructor.

        Args:
            id:
                A unique ID of the ground in the network grounds.
        """
        super().__init__(id, **kwargs)
        self._bus_phases: dict[Id, str] = {}
        """A map of bus id to phase connected to this ground."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    def connect(self, bus: "Bus", phase: str = "n") -> None:
        """Connect the ground to a bus on the given phase.

        Args:
            bus:
                The bus to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the bus phases. Defaults to ``"n"``.
        """
        self._check_phases(self.id, phases=phase)
        if phase not in bus.phases:
            msg = f"Cannot connect a ground to phase {phase!r} of bus {bus.id!r} that has phases {bus.phases!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        self._connect(bus)
        self._bus_phases[bus.id] = phase

    @classmethod
    def from_dict(cls, data: JsonDict) -> "Ground":
        self = cls(data["id"])
        self._bus_phases = data["buses"]
        return self

    def to_dict(self) -> JsonDict:
        # Shunt lines and potential references will have the ground in their dict not here.
        return {
            "id": self.id,
            "buses": [{"id": bus_id, "phase": phase} for bus_id, phase in self._bus_phases.items()],
        }


class AbstractBranch(Element):
    """This is an abstract class for all the branches (lines, switches and transformers) of the network."""

    branch_type: BranchType

    def __init__(
        self,
        id: Id,
        bus1: "Bus",
        bus2: "Bus",
        *,
        phases1: str,
        phases2: str,
        geometry: Optional[BaseGeometry] = None,
        **kwargs: Any,
    ) -> None:
        """AbstractBranch constructor.

        Args:
            id:
                A unique ID of the branch in the network branches.

            phases1:
                The phases of the first extremity of the branch.

            phases2:
                The phases of the second extremity of the branch.

            bus1:
                The bus to connect the first extremity of the branch to.

            bus2:
                The bus to connect the second extremity of the branch to.

            geometry:
                The geometry of the branch.
        """
        super().__init__(id, **kwargs)
        self._check_phases(id, phases1=phases1)
        self._check_phases(id, phases2=phases2)
        self.phases1 = phases1
        self.phases2 = phases2
        self._connect(bus1, bus2)
        self.geometry = geometry
        self._res_currents: Optional[tuple[np.ndarray, np.ndarray]] = None

    def __repr__(self) -> str:
        s = f"{type(self).__name__}(id={self.id!r}, phases1={self.phases1!r}, phases2={self.phases2!r}"
        s += f", bus1={self.connected_elements[0].id!r}, bus2={self.connected_elements[1].id!r}"
        if self.geometry is not None:
            s += f", geometry={self.geometry}"
        s += ")"
        return s

    def _res_currents_getter(self, warning: bool) -> tuple[np.ndarray, np.ndarray]:
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    def res_currents(self) -> tuple[np.ndarray, np.ndarray]:
        """The load flow result of the branch currents (A)."""
        return self._res_currents_getter(warning=True)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> "AbstractBranch":
        return cls(**data)  # not used anymore

    def to_dict(self) -> JsonDict:
        res = {
            "id": self.id,
            "type": str(self.branch_type),
            "phases1": self.phases1,
            "phases2": self.phases2,
            "bus1": self.connected_elements[0].id,
            "bus2": self.connected_elements[1].id,
        }
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res
