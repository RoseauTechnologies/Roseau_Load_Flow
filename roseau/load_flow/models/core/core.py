from abc import ABC
from typing import Any, Optional, TYPE_CHECKING

import shapely.wkt
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.utils import BranchType
from roseau.load_flow.utils.exceptions import ThundersIOError
from roseau.load_flow.utils.json_mixin import JsonMixin

if TYPE_CHECKING:
    from roseau.load_flow.models.buses.buses import AbstractBus


class Element(ABC):
    def __init__(self):
        self.connected_elements: list[Element] = []

    def disconnect(self):
        """Remove all the connections with the other elements."""
        for element in self.connected_elements:
            element.connected_elements[:] = [e for e in element.connected_elements if e != self]


class PotentialRef(Element):
    def __init__(self, element: Element):
        """Potential reference element constructor, this element will set the origin of the potentials as
        Va + Vb + Vc = 0 for delta elements or Vn = 0 for the others.

        Args:
            element:
                The element to connect to.
        """
        super().__init__()
        self.connected_elements = [element]
        element.connected_elements.append(self)


class Ground(Element):
    def __init__(self):
        """Ground constructor."""
        super().__init__()

    def connect(self, bus: "AbstractBus"):
        """Connect the ground to the bus neutral.

        Args:
            bus:
                The bus to connect to.
        """
        if self not in bus.connected_elements:
            self.connected_elements.append(bus)
            bus.connected_elements.append(self)


class AbstractBranch(Element, JsonMixin):
    type: BranchType = NotImplemented

    def __init__(
        self,
        id_: Any,
        n1: int,
        n2: int,
        bus1: "AbstractBus",
        bus2: "AbstractBus",
        geometry: Optional[BaseGeometry] = None,
    ) -> None:
        """AbstractBranch constructor.

        Args:
            id_:
                The identifier of the branch.

            n1:
                Number of ports in the first extremity of the branch.

            n2:
                Number of ports in the second extremity of the branch.

            bus1:
                Bus to connect to the first extremity of the branch.

            bus2:
                Bus to connect to the second extremity of the branch.

            geometry:
                The geometry of the branch.
        """
        super().__init__()
        self.id = id_
        self.n1 = n1
        self.n2 = n2
        self.connected_elements = [bus1, bus2]
        bus1.connected_elements.append(self)
        bus2.connected_elements.append(self)
        self.geometry = geometry

    def __str__(self) -> str:
        return f"id={self.id} - n1={self.n1} - n2={self.n2}"

    @staticmethod
    def from_dict(branch, bus1, bus2, ground, line_types, transformer_types, *args):
        from roseau.load_flow.models.lines.lines import Line, Switch
        from roseau.load_flow.models.transformers.transformers import Transformer

        try:
            geometry = shapely.wkt.loads(branch["geometry"])
        except KeyError:
            geometry = None
        if branch["type"] == "line":
            return Line.from_dict(
                id_=branch["id"],
                bus1=bus1,
                bus2=bus2,
                length=branch["length"],
                line_types=line_types,
                type_name=branch["type_name"],
                ground=ground,
                geometry=geometry,
            )
        elif branch["type"] == "transformer":
            return Transformer.from_dict(
                id_=branch["id"],
                bus1=bus1,
                bus2=bus2,
                type_name=branch["type_name"],
                transformer_types=transformer_types,
                tap=branch["tap"],
                geometry=geometry,
            )
        elif branch["type"] == "switch":
            return Switch(id_=branch["id"], n=bus1.n, bus1=bus1, bus2=bus2, geometry=geometry)
        else:
            raise ThundersIOError(f"Unknown branch type for branch {branch['id']}: {branch['type']}")

    def to_dict(self) -> dict[str, Any]:
        res = {
            "id": self.id,
            "bus1": self.connected_elements[0].id,
            "bus2": self.connected_elements[1].id,
        }
        if self.geometry is not None:
            res["geometry"] = str(self.geometry)
        return res
