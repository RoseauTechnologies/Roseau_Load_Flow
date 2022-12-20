import logging
from abc import ABC
from typing import Any, ClassVar, Optional, TYPE_CHECKING, Union

import numpy as np
import shapely.wkt
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import BranchType, ureg
from roseau.load_flow.utils.mixins import Identifiable, JsonMixin

if TYPE_CHECKING:
    from roseau.load_flow.models.buses import Bus
    from roseau.load_flow.models.lines import Line, LineCharacteristics, Switch
    from roseau.load_flow.models.transformers import Transformer, TransformerCharacteristics

logger = logging.getLogger(__name__)


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

    def connect(self, element: "Element") -> None:
        """Connect this element to another element.

        Args:
            element:
                The element to connect to.
        """
        if element not in self.connected_elements:
            self.connected_elements.append(element)
        if self not in element.connected_elements:
            element.connected_elements.append(self)

    def disconnect(self) -> None:
        """Remove all the connections with the other elements."""
        for element in self.connected_elements:
            element.connected_elements.remove(self)


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
        self.connect(element)
        self.phase = phase

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, element={self.connected_elements[0]!r}, phase={self.phase!r})"

    @property
    @ureg.wraps("V", None, strict=False)
    def current(self) -> complex:
        """Compute the sum of the currents of the connection associated to the potential reference.

        This sum should be equal to 0 after the load flow.

        Returns:
            The sum of the current of the connection.
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

       To connect a ground to a bus on a given phase, use the :meth:`Ground.connect_to_bus` method.
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
        self.phases: dict[Id, str] = {}
        """A map of bus id to phase connected to this ground."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    def connect_to_bus(self, bus: "Bus", phase: str = "n"):
        """Connect the ground to a bus on the given phase.

        Args:
            bus:
                The bus to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the bus phases. Defaults to ``"n"``.
        """
        self._check_phases(id, phases=phase)
        if phase not in bus.phases:
            msg = f"Cannot connect a ground to phase {phase!r} of bus {bus.id!r} that has phases {bus.phases!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        self.connect(bus)
        self.phases[bus.id] = phase

    @classmethod
    def from_dict(cls, data: JsonDict) -> "Ground":
        self = cls(data["id"])
        self.phases = data["buses"]
        return self

    def to_dict(self) -> JsonDict:
        # Shunt lines and potential references will have the ground in their dict not here.
        return {"id": self.id, "buses": self.phases}


class AbstractBranch(Element):
    """This is an abstract class for all the branches (lines, switches and transformers) of the network."""

    branch_type: BranchType

    @classmethod
    def _line_class(cls) -> type["Line"]:
        from roseau.load_flow.models.lines.lines import Line

        return Line

    @classmethod
    def _transformer_class(cls) -> type["Transformer"]:
        from roseau.load_flow.models.transformers.transformers import Transformer

        return Transformer

    @classmethod
    def _switch_class(cls) -> type["Switch"]:
        from roseau.load_flow.models.lines.lines import Switch

        return Switch

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
        self.connect(bus1)
        self.connect(bus2)
        self.geometry = geometry
        self._currents = None

    def __repr__(self) -> str:
        s = f"{type(self).__name__}(id={self.id!r}, phases1={self.phases1!r}, phases2={self.phases2!r}"
        s += f", bus1={self.connected_elements[0].id!r}, bus2={self.connected_elements[1].id!r}"
        if self.geometry is not None:
            s += f", geometry={self.geometry}"
        s += ")"
        return s

    @property
    @ureg.wraps(("A", "A"), None, strict=False)
    def currents(self) -> tuple[np.ndarray, np.ndarray]:
        """Arrays of the actual currents of each phase of the two extremities (A) as computed by the load flow."""
        return self._currents

    @currents.setter
    def currents(self, value: tuple[np.ndarray, np.ndarray]) -> None:
        self._currents = value

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(
        cls,
        data: JsonDict,
        bus1: "Bus",
        bus2: "Bus",
        ground: Optional[Ground],
        line_types: dict[str, "LineCharacteristics"],
        transformer_types: dict[str, "TransformerCharacteristics"],
        *args,
    ) -> "AbstractBranch":

        if "geometry" not in data:
            geometry = None
        elif isinstance(data["geometry"], str):
            geometry = shapely.wkt.loads(data["geometry"])
        else:
            geometry = shape(data["geometry"])

        if data["type"] == "line":
            assert data["phases2"] == data["phases1"]  # line phases must be the same
            return cls._line_class().from_dict(
                id=data["id"],
                bus1=bus1,
                bus2=bus2,
                length=data["length"],
                line_type=line_types[data["type_id"]],
                phases=data["phases1"],  # or phases2, they are the same
                ground=ground,
                geometry=geometry,
            )
        elif data["type"] == "transformer":
            return cls._transformer_class().from_dict(
                id=data["id"],
                bus1=bus1,
                bus2=bus2,
                transformer_type=transformer_types[data["type_id"]],
                tap=data["tap"],
                phases1=data["phases1"],
                phases2=data["phases2"],
                geometry=geometry,
            )
        elif data["type"] == "switch":
            assert data["phases2"] == data["phases1"]  # switch phases must be the same
            return cls._switch_class()(data["id"], bus1, bus2, phases=bus1.phases, geometry=geometry)
        else:
            msg = f"Unknown branch type for branch {data['id']}: {data['type']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)

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
