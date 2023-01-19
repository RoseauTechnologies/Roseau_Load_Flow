import logging
from typing import Any, Optional

import numpy as np
from shapely.geometry.base import BaseGeometry

from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict, Self
from roseau.load_flow.utils import BranchType

logger = logging.getLogger(__name__)


class AbstractBranch(Element):
    """This is an abstract class for all the branches (lines, switches and transformers) of the network."""

    branch_type: BranchType

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
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
    def from_dict(cls, data: JsonDict) -> Self:
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
