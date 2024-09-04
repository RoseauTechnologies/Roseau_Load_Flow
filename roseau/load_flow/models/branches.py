import logging
from functools import cached_property

from shapely.geometry.base import BaseGeometry
from typing_extensions import Self

from roseau.load_flow.converters import _calculate_voltages
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

    def __init__(
        self, id: Id, bus1: Bus, bus2: Bus, *, phases1: str, phases2: str, geometry: BaseGeometry | None = None
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
        if type(self) is AbstractBranch:
            raise TypeError("Can't instantiate abstract class AbstractBranch")
        super().__init__(id)
        self._check_phases(id=id, phases1=phases1)
        self._check_phases(id=id, phases2=phases2)
        self._n1 = len(phases1)
        self._n2 = len(phases2)
        self._phases1 = phases1
        self._phases2 = phases2
        self._bus1 = bus1
        self._bus2 = bus2
        self.geometry = geometry
        self._connect(bus1, bus2)
        self._res_currents: tuple[ComplexArray, ComplexArray] | None = None

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}: id={self.id!r}, bus1={self.bus1.id!r}, bus2={self.bus2.id!r}, "
            f"phases1={self.phases1!r}, phases2={self.phases2!r}>"
        )

    @property
    def phases1(self) -> str:
        """The phases of the branch at the first bus."""
        return self._phases1

    @property
    def phases2(self) -> str:
        """The phases of the branch at the second bus."""
        return self._phases2

    @cached_property
    def _all_phases(self) -> str:
        return "".join(sorted(set(self._phases1) | set(self._phases2)))

    @property
    def bus1(self) -> Bus:
        """The first bus of the branch."""
        return self._bus1

    @property
    def bus2(self) -> Bus:
        """The second bus of the branch."""
        return self._bus2

    def _res_currents_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        if self._fetch_results:
            self._res_currents = self._cy_element.get_currents(self._n1, self._n2)
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_currents(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch currents (A)."""
        return self._res_currents_getter(warning=True)

    def _res_powers_getter(
        self,
        warning: bool,
        potentials1: ComplexArray | None = None,
        potentials2: ComplexArray | None = None,
        currents1: ComplexArray | None = None,
        currents2: ComplexArray | None = None,
    ) -> tuple[ComplexArray, ComplexArray]:
        if currents1 is None or currents2 is None:
            currents1, currents2 = self._res_currents_getter(warning)
        if potentials1 is None or potentials2 is None:
            potentials1, potentials2 = self._res_potentials_getter(warning=False)  # we warn on the previous line
        powers1 = potentials1 * currents1.conj()
        powers2 = potentials2 * currents2.conj()
        return powers1, powers2

    @property
    @ureg_wraps(("VA", "VA"), (None,))
    def res_powers(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch powers (VA)."""
        return self._res_powers_getter(warning=True)

    def _res_potentials_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        pot1 = self.bus1._get_potentials_of(phases=self.phases1, warning=warning)
        pot2 = self.bus2._get_potentials_of(phases=self.phases2, warning=False)  # we warn on the previous line
        return pot1, pot2

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_potentials(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(
        self, warning: bool, potentials1: ComplexArray | None = None, potentials2: ComplexArray | None = None
    ) -> tuple[ComplexArray, ComplexArray]:
        if potentials1 is None or potentials2 is None:
            potentials1, potentials2 = self._res_potentials_getter(warning)
        return _calculate_voltages(potentials=potentials1, phases=self.phases1), _calculate_voltages(
            potentials=potentials2, phases=self.phases2
        )

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_voltages(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch voltages (V)."""
        return self._res_voltages_getter(warning=True)

    def _cy_connect(self) -> None:
        """Connect the Cython elements of the buses and the branch"""
        connections = []
        assert isinstance(self.bus1, Bus)
        for i, phase in enumerate(self.phases1):
            if phase in self.bus1.phases:
                j = self.bus1.phases.index(phase)
                connections.append((i, j))
        self._cy_element.connect(self.bus1._cy_element, connections, True)

        connections = []
        assert isinstance(self.bus2, Bus)
        for i, phase in enumerate(self.phases2):
            if phase in self.bus2.phases:
                j = self.bus2.phases.index(phase)
                connections.append((i, j))
        self._cy_element.connect(self.bus2._cy_element, connections, False)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        return cls(**data)  # not used anymore

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {
            "id": self.id,
            "phases1": self.phases1,
            "phases2": self.phases2,
            "bus1": self.bus1.id,
            "bus2": self.bus2.id,
        }
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        if include_results:
            currents1, currents2 = self._res_currents_getter(warning=True)
            res["results"] = {
                "currents1": [[i.real, i.imag] for i in currents1],
                "currents2": [[i.real, i.imag] for i in currents2],
            }
        return res
