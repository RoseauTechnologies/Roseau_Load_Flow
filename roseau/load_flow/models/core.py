import logging
from abc import ABC
from typing import Any, Optional, TYPE_CHECKING

import numpy as np
import shapely.wkt
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils import BranchType
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

if TYPE_CHECKING:
    from roseau.load_flow.models.buses import AbstractBus
    from roseau.load_flow.models.lines import AbstractLine, Switch
    from roseau.load_flow.models.transformers import AbstractTransformer

logger = logging.getLogger(__name__)


class Element(ABC):
    """An abstract class to describe an element of an Electrical network"""

    def __init__(self, **kwargs):
        self.connected_elements: list[Element] = []

    def disconnect(self):
        """Remove all the connections with the other elements."""
        for element in self.connected_elements:
            element.connected_elements[:] = [e for e in element.connected_elements if e != self]


class PotentialRef(Element):
    """This elements defines the potential reference"""

    def __init__(self, element: Element, **kwargs):
        """Potential reference element constructor, this element will set the origin of the potentials as
        Va + Vb + Vc = 0 for delta elements or Vn = 0 for the others.

        Args:
            element:
                The element to connect to.
        """
        super().__init__(**kwargs)
        self.connected_elements = [element]
        element.connected_elements.append(self)

    @property
    @ureg.wraps("V", None, strict=False)
    def current(self) -> complex:
        """Compute the sum of the currents of the connection associated to the potential reference. This sum should be
        equal to 0 after the load flow.

        Returns:
            The sum of the current of the connection.
        """
        raise NotImplementedError


class Ground(Element):
    """This element defines the ground."""

    def __init__(self, **kwargs):
        """Ground constructor."""
        super().__init__(**kwargs)

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
    """This is an abstract class for all the branches (lines, switches and transformers) of the network."""

    branch_type: BranchType = NotImplemented

    @classmethod
    def _line_class(cls) -> type["AbstractLine"]:
        from roseau.load_flow.models.lines.lines import AbstractLine

        return AbstractLine

    @classmethod
    def _transformer_class(cls) -> type["AbstractTransformer"]:
        from roseau.load_flow.models.transformers.transformers import AbstractTransformer

        return AbstractTransformer

    @classmethod
    def _switch_class(cls) -> type["Switch"]:
        from roseau.load_flow.models.lines.lines import Switch

        return Switch

    def __init__(
        self,
        id: Any,
        n1: int,
        n2: int,
        bus1: "AbstractBus",
        bus2: "AbstractBus",
        geometry: Optional[BaseGeometry] = None,
        **kwargs,
    ) -> None:
        """AbstractBranch constructor.

        Args:
            id:
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
        super().__init__(**kwargs)
        self.id = id
        self.n1 = n1
        self.n2 = n2
        self.connected_elements = [bus1, bus2]
        bus1.connected_elements.append(self)
        bus2.connected_elements.append(self)
        self.geometry = geometry
        self._currents = None

    def __str__(self) -> str:
        return f"id={self.id} - n1={self.n1} - n2={self.n2}"

    @property
    @ureg.wraps(("A", "A"), None, strict=False)
    def currents(self) -> tuple[np.ndarray, np.ndarray]:
        """Current accessor

        Returns:
            The complex currents of each phase.
        """
        return self._currents

    @currents.setter
    def currents(self, value: np.ndarray):
        self._currents = value

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, branch, bus1, bus2, ground, line_types, transformer_types, *args):

        if "geometry" not in branch:
            geometry = None
        elif isinstance(branch["geometry"], str):
            geometry = shapely.wkt.loads(branch["geometry"])
        else:
            geometry = shape(branch["geometry"])

        if branch["type"] == "line":
            return cls._line_class().from_dict(
                id=branch["id"],
                bus1=bus1,
                bus2=bus2,
                length=branch["length"],
                line_types=line_types,
                type_name=branch["type_name"],
                ground=ground,
                geometry=geometry,
            )
        elif branch["type"] == "transformer":
            return cls._transformer_class().from_dict(
                id=branch["id"],
                bus1=bus1,
                bus2=bus2,
                type_name=branch["type_name"],
                transformer_types=transformer_types,
                tap=branch["tap"],
                geometry=geometry,
            )
        elif branch["type"] == "switch":
            return cls._switch_class()(id=branch["id"], n=bus1.n, bus1=bus1, bus2=bus2, geometry=geometry)
        else:
            msg = f"Unknown branch type for branch {branch['id']}: {branch['type']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE)

    def to_dict(self) -> dict[str, Any]:
        res = {
            "id": self.id,
            "bus1": self.connected_elements[0].id,
            "bus2": self.connected_elements[1].id,
        }
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res
