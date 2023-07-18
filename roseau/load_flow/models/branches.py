import logging
from typing import Any, Optional, Union

import numpy as np
from shapely import LineString, Point
from typing_extensions import Self

from roseau.load_flow.converters import calculate_voltages
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg
from roseau.load_flow.utils import BranchType

logger = logging.getLogger(__name__)


class AbstractBranch(Element):
    """This is an abstract class for all the branches (lines, switches and transformers) of the network.

    See Also:
        `Line documentation <../../../models/Line/index.html>`_,
        `Transformer documentation <../../../models/Transformer/index.html>`_ and
        `Switch documentation <../../../models/Switch.html>`_
    """

    branch_type: BranchType

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        phases1: str,
        phases2: str,
        geometry: Optional[Union[Point, LineString]] = None,
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
        self.bus1 = bus1
        self.bus2 = bus2
        self.geometry = geometry
        self._connect(bus1, bus2)
        self._res_currents: Optional[tuple[np.ndarray, np.ndarray]] = None

    def __repr__(self) -> str:
        s = f"{type(self).__name__}(id={self.id!r}, phases1={self.phases1!r}, phases2={self.phases2!r}"
        s += f", bus1={self.bus1.id!r}, bus2={self.bus2.id!r}"
        if self.geometry is not None:
            s += f", geometry={self.geometry}"
        s += ")"
        return s

    def _res_currents_getter(self, warning: bool) -> tuple[np.ndarray, np.ndarray]:
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg.wraps(("A", "A"), (None,), strict=False)
    def res_currents(self) -> tuple[Q_, Q_]:
        """The load flow result of the branch currents (A)."""
        return self._res_currents_getter(warning=True)

    def _res_powers_getter(self, warning: bool) -> tuple[np.ndarray, np.ndarray]:
        cur1, cur2 = self._res_currents_getter(warning)
        pot1, pot2 = self._res_potentials_getter(warning=False)  # we warn on the previous line
        powers1 = pot1 * cur1.conj()
        powers2 = pot2 * cur2.conj()
        return powers1, powers2

    @property
    @ureg.wraps(("VA", "VA"), (None,), strict=False)
    def res_powers(self) -> tuple[Q_, Q_]:
        """The load flow result of the branch powers (VA)."""
        return self._res_powers_getter(warning=True)

    def _res_potentials_getter(self, warning: bool) -> tuple[np.ndarray, np.ndarray]:
        pot1 = self.bus1._get_potentials_of(self.phases1, warning)
        pot2 = self.bus2._get_potentials_of(self.phases2, warning=False)  # we warn on the previous line
        return pot1, pot2

    @property
    @ureg.wraps(("V", "V"), (None,), strict=False)
    def res_potentials(self) -> tuple[Q_, Q_]:
        """The load flow result of the branch potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(self, warning: bool) -> tuple[np.ndarray, np.ndarray]:
        pot1, pot2 = self._res_potentials_getter(warning)
        return calculate_voltages(pot1, self.phases1), calculate_voltages(pot2, self.phases2)

    @property
    @ureg.wraps(("V", "V"), (None,), strict=False)
    def res_voltages(self) -> tuple[Q_, Q_]:
        """The load flow result of the branch voltages (V)."""
        return self._res_voltages_getter(warning=True)

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
            "bus1": self.bus1.id,
            "bus2": self.bus2.id,
        }
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res

    def results_from_dict(self, data: JsonDict) -> None:
        currents1 = np.array([complex(i[0], i[1]) for i in data["currents1"]], dtype=complex)
        currents2 = np.array([complex(i[0], i[1]) for i in data["currents2"]], dtype=complex)
        self._res_currents = (currents1, currents2)

    def _results_to_dict(self, warning: bool) -> JsonDict:
        currents1, currents2 = self._res_currents_getter(warning)
        return {
            "id": self.id,
            "phases1": self.phases1,
            "phases2": self.phases2,
            "currents1": [[i.real, i.imag] for i in currents1],
            "currents2": [[i.real, i.imag] for i in currents2],
        }
