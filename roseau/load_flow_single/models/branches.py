import logging
from typing import TypeVar

from shapely.geometry.base import BaseGeometry
from typing_extensions import Self

from roseau.load_flow import SQRT3
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element

logger = logging.getLogger(__name__)

_CyB = TypeVar("_CyB", bound=CyBranch)


class AbstractBranch(Element[_CyB]):
    """Base class of all the branches (lines, switches and transformers) of the network.

    See Also:
        :doc:`Line models documentation </models/Line/index>`,
        :doc:`Transformer models documentation </models/Transformer/index>` and
        :doc:`Switch model documentation </models/Switch>`
    """

    def __init__(self, id: Id, bus1: Bus, bus2: Bus, n: int, *, geometry: BaseGeometry | None = None) -> None:
        """AbstractBranch constructor.

        Args:
            id:
                A unique ID of the branch in the network branches.

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
        self._bus1 = bus1
        self._bus2 = bus2
        self._n = n
        self.geometry = geometry
        self._connect(bus1, bus2)
        self._res_currents: tuple[complex, complex] | None = None

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: id={self.id!r}, bus1={self.bus1.id!r}, bus2={self.bus2.id!r}>"

    @property
    def bus1(self) -> Bus:
        """The first bus of the branch."""
        return self._bus1

    @property
    def bus2(self) -> Bus:
        """The second bus of the branch."""
        return self._bus2

    def _res_currents_getter(self, warning: bool) -> tuple[complex, complex]:
        if self._fetch_results:
            cur1, cur2 = self._cy_element.get_currents(1, 1)
            self._res_currents = cur1[0], cur2[0]
        return self._res_getter(value=self._res_currents, warning=warning)

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_currents(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch currents (A)."""
        return self._res_currents_getter(warning=True)

    def _res_powers_getter(
        self,
        warning: bool,
        voltage1: complex | None = None,
        voltage2: complex | None = None,
        current1: complex | None = None,
        current2: complex | None = None,
    ) -> tuple[complex, complex]:
        if current1 is None or current2 is None:
            current1, current2 = self._res_currents_getter(warning)
        if voltage1 is None or voltage2 is None:
            voltage1, voltage2 = self._res_voltages_getter(warning=False)  # we warn on the previous line
        power1 = voltage1 * current1.conjugate() * SQRT3
        power2 = voltage2 * current2.conjugate() * SQRT3
        return power1, power2

    @property
    @ureg_wraps(("VA", "VA"), (None,))
    def res_powers(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch powers (VA)."""
        return self._res_powers_getter(warning=True)

    def _res_voltages_getter(self, warning: bool) -> tuple[complex, complex]:
        voltage1 = self.bus1._res_voltage_getter(warning=warning)
        voltage2 = self.bus2._res_voltage_getter(warning=False)  # we warn on the previous line
        return voltage1, voltage2

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_voltages(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch voltages (V)."""
        return self._res_voltages_getter(warning=True)

    def _cy_connect(self) -> None:
        """Connect the Cython elements of the buses and the branch"""
        connections = [(i, i) for i in range(self._n)]
        self._cy_element.connect(self.bus1._cy_element, connections, True)
        self._cy_element.connect(self.bus2._cy_element, connections, False)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        return cls(**data)  # not used anymore

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id, "bus1": self.bus1.id, "bus2": self.bus2.id}
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        if include_results:
            current1, current2 = self._res_currents_getter(warning=True)
            res["results"] = {
                "current1": [current1.real, current1.imag],
                "current2": [current2.real, current2.imag],
            }
        return res
