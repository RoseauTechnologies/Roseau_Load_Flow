import logging
from abc import ABC
from typing import Any, ClassVar, Optional, TYPE_CHECKING

import numpy as np
import shapely.wkt
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils import BranchType
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

if TYPE_CHECKING:
    from roseau.load_flow.models.buses import Bus
    from roseau.load_flow.models.lines import Line, LineCharacteristics, Switch
    from roseau.load_flow.models.transformers import Transformer, TransformerCharacteristics

logger = logging.getLogger(__name__)


class Element(ABC):
    """An abstract class to describe an element of an Electrical network"""

    allowed_phases: ClassVar[frozenset[str]]  # frozenset for immutability and uniqueness
    """The allowed phases for this element type.

    It is a frozen set of strings like ``"abc"`` or ``"an"`` etc. The order of the phases is
    important. For a full list of supported phases, use ``print(<Element class>.allowed_phases)``.
    """

    def __init__(self, **kwargs):
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

    def disconnect(self):
        """Remove all the connections with the other elements."""
        for element in self.connected_elements:
            element.connected_elements[:] = [e for e in element.connected_elements if e != self]


class PotentialRef(Element):
    """The potential reference of the network.

    This element will set the origin of the potentials as `Va + Vb + Vc = 0` for delta elements
    or `Vn = 0` for others.
    """  # TODO: update the docstring with the new semantics

    allowed_phases = frozenset({"a", "b", "c", "n"})

    def __init__(self, element: Element, *, phase: Optional[str] = None, **kwargs):
        """PotentialRef constructor.

        Args:
            element:
                The element to connect to, normally the ground element.

            phase:
                The phase of the potential reference. If not given, the phase of the element will
                be used.
        """
        from roseau.load_flow.models.buses import Bus  # TODO refactor potential ref and ground

        if isinstance(element, Bus):
            if phase is None:
                phase = "n" if "n" in element.phases else None
            else:
                self._check_phases(element.id, phases=phase)
        elif isinstance(element, Ground):
            if phase is not None:
                # TODO: add ID to the error message when the ID is implemented
                msg = "Potential reference connected to the ground cannot have a phase."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            msg = f"Only buses and ground can be connected to a potential reference, got {element!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        super().__init__(**kwargs)
        self.connected_elements = [element]
        element.connected_elements.append(self)
        self.phase = phase

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.connected_elements[0]!r})"

    @property
    @ureg.wraps("V", None, strict=False)
    def current(self) -> complex:
        """Compute the sum of the currents of the connection associated to the potential reference.

        This sum should be equal to 0 after the load flow.

        Returns:
            The sum of the current of the connection.
        """
        raise NotImplementedError


class Ground(Element):
    """This element defines the ground."""

    allowed_phases = frozenset({"a", "b", "c", "n"})

    def __init__(self, **kwargs):
        """Ground constructor."""
        super().__init__(**kwargs)
        self.phase: Optional[str] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def connect(self, bus: "Bus", phase: str = "n"):
        """Connect the ground to the bus neutral.

        Args:
            bus:
                The bus to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the bus phases. Defaults to ``"n"``.
        """
        self._check_phases(None, phases=phase)  # TODO: pass ID when implemented
        if phase not in bus.phases:
            msg = f"Cannot connect a ground to phase {phase!r} of bus {bus.id!r} that has phases {bus.phases!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        if self not in bus.connected_elements:
            self.connected_elements.append(bus)
            bus.connected_elements.append(self)
        self.phase = phase


class AbstractBranch(Element, JsonMixin):
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
        id: Any,
        phases1: str,
        phases2: str,
        bus1: "Bus",
        bus2: "Bus",
        geometry: Optional[BaseGeometry] = None,
        **kwargs,
    ) -> None:
        """AbstractBranch constructor.

        Args:
            id:
                The unique id of the branch.

            phases1:
                The phases of the first extremity of the branch. Only 3-phase elements are
                currently supported. Allowed values are: ``"abc"`` or ``"abcn"``.

            phases2:
                The phases of the second extremity of the branch.

            bus1:
                The bus to connect the first extremity of the branch to.

            bus2:
                The bus to connect the second extremity of the branch to.

            geometry:
                The geometry of the branch.
        """
        self._check_phases(id, phases1=phases1)
        self._check_phases(id, phases2=phases2)
        super().__init__(**kwargs)
        self.id = id
        self.phases1 = phases1
        self.phases2 = phases2
        self.connected_elements = [bus1, bus2]
        bus1.connected_elements.append(self)
        bus2.connected_elements.append(self)
        self.geometry = geometry
        self._currents = None

    def __repr__(self) -> str:
        s = f"{type(self).__name__}(id={self.id!r}, phases1={self.phases1!r}, phases2={self.phases2!r}"
        s += f", bus1={self.connected_elements[0].id!r}, bus2={self.connected_elements[1].id!r}"
        if self.geometry is not None:
            s += f", geometry={self.geometry}"
        s += ")"
        return s

    def __str__(self) -> str:
        return f"id={self.id!r} - phases1={self.phases1!r} - phases2={self.phases2!r}"

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
        data: dict[str, Any],
        bus1: "Bus",
        bus2: "Bus",
        ground: Ground,
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
            return cls._line_class().from_dict(
                id=data["id"],
                bus1=bus1,
                bus2=bus2,
                length=data["length"],
                line_types=line_types,
                type_name=data["type_name"],
                ground=ground,
                geometry=geometry,
            )
        elif data["type"] == "transformer":
            return cls._transformer_class().from_dict(
                id=data["id"],
                bus1=bus1,
                bus2=bus2,
                type_name=data["type_name"],
                transformer_types=transformer_types,
                tap=data["tap"],
                geometry=geometry,
            )
        elif data["type"] == "switch":
            return cls._switch_class()(id=data["id"], phases=bus1.phases, bus1=bus1, bus2=bus2, geometry=geometry)
        else:
            msg = f"Unknown branch type for branch {data['id']}: {data['type']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)

    def to_dict(self) -> dict[str, Any]:
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
