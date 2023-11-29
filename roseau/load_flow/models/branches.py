import logging
from typing import Any, Optional, Union

import numpy as np
from shapely import LineString, Point
from typing_extensions import Self

from roseau.load_flow.converters import calculate_voltages
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps

logger = logging.getLogger(__name__)


class AbstractBranch(Element):
    """Base class of all the branches (lines, switches and transformers) of the network.

    See Also:
        :doc:`Line models documentation </models/Line/index>`,
        :doc:`Transformer models documentation </models/Transformer/index>` and
        :doc:`Switch model documentation </models/Switch>`
    """

    branch_type: str

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
        self._res_currents: Optional[tuple[ComplexArray, ComplexArray]] = None

    def __repr__(self) -> str:
        s = f"{type(self).__name__}(id={self.id!r}, phases1={self.phases1!r}, phases2={self.phases2!r}"
        s += f", bus1={self.bus1.id!r}, bus2={self.bus2.id!r}"
        if self.geometry is not None:
            s += f", geometry={self.geometry}"
        s += ")"
        return s

    def _res_currents_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_currents(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch currents (A)."""
        return self._res_currents_getter(warning=True)

    def _res_powers_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        cur1, cur2 = self._res_currents_getter(warning)
        pot1, pot2 = self._res_potentials_getter(warning=False)  # we warn on the previous line
        powers1 = pot1 * cur1.conj()
        powers2 = pot2 * cur2.conj()
        return powers1, powers2

    @property
    @ureg_wraps(("VA", "VA"), (None,))
    def res_powers(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch powers (VA)."""
        return self._res_powers_getter(warning=True)

    def _res_potentials_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        pot1 = self.bus1._get_potentials_of(self.phases1, warning)
        pot2 = self.bus2._get_potentials_of(self.phases2, warning=False)  # we warn on the previous line
        return pot1, pot2

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_potentials(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        pot1, pot2 = self._res_potentials_getter(warning)
        return calculate_voltages(pot1, self.phases1), calculate_voltages(pot2, self.phases2)

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_voltages(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch voltages (V)."""
        return self._res_voltages_getter(warning=True)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        return cls(**data)  # not used anymore

    def to_dict(self, *, _lf_only: bool = False) -> JsonDict:
        res = {
            "id": self.id,
            "type": self.branch_type,
            "phases1": self.phases1,
            "phases2": self.phases2,
            "bus1": self.bus1.id,
            "bus2": self.bus2.id,
        }
        if not _lf_only and self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res

    def results_from_dict(self, data: JsonDict) -> None:
        currents1 = np.array([complex(i[0], i[1]) for i in data["currents1"]], dtype=np.complex128)
        currents2 = np.array([complex(i[0], i[1]) for i in data["currents2"]], dtype=np.complex128)
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
