import logging
import math
import warnings
from abc import abstractmethod
from typing import Self

from shapely.geometry.base import BaseGeometry
from typing_extensions import TypeVar

from roseau.load_flow import SQRT3
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_engine.cy_engine import CyBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.line_parameters import LineParameters
from roseau.load_flow_single.models.transformer_parameters import TransformerParameters

logger = logging.getLogger(__name__)

_CyB_co = TypeVar("_CyB_co", bound=CyBranch, default=CyBranch, covariant=True)

_Parameters = LineParameters | TransformerParameters


class AbstractBranch(Element[_CyB_co]):
    """Base class of all the branches (lines, switches and transformers) of the network.

    See Also:
        :doc:`Line models documentation </models/Line/index>`,
        :doc:`Transformer models documentation </models/Transformer/index>` and
        :doc:`Switch model documentation </models/Switch>`
    """

    @abstractmethod
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
        super().__init__(id)
        self._bus1 = bus1
        self._bus2 = bus2
        self._n = n
        self.geometry = self._check_geometry(geometry)
        self._res_currents: tuple[complex, complex] | None = None
        self._res_voltages: tuple[complex, complex] | None = None
        self._sides_suffixes = ("_hv", "_lv") if self.element_type == "transformer" else ("1", "2")

    def __repr__(self) -> str:
        s1, s2 = self._sides_suffixes
        return f"<{type(self).__name__}: id={self.id!r}, bus{s1}={self.bus1.id!r}, bus{s2}={self.bus2.id!r}>"

    @property
    def bus1(self) -> Bus:
        """The first bus of the branch."""
        return self._bus1

    @property
    def bus2(self) -> Bus:
        """The second bus of the branch."""
        return self._bus2

    def _cy_connect(self) -> None:
        """Connect the Cython elements of the buses and the branch"""
        connections = [(i, i) for i in range(self._n)]
        self._cy_element.connect_side(self.bus1._cy_element, connections, True)
        self._cy_element.connect_side(self.bus2._cy_element, connections, False)

    def _check_same_voltage_level(self) -> None:
        if (
            self.bus1._nominal_voltage is not None
            and self.bus2._nominal_voltage is not None
            and not math.isclose(self.bus1._nominal_voltage, self.bus2._nominal_voltage)
        ):
            warnings.warn(
                (
                    f"{self.element_type.capitalize()} {self.id!r} connects buses with different "
                    f"nominal voltages: {self.bus1._nominal_voltage} V and {self.bus2._nominal_voltage} V."
                ),
                stacklevel=find_stack_level(),
            )

    def _update_network_parameters(self, old_parameters: _Parameters | None, new_parameters: _Parameters) -> None:
        if old_parameters is not None and old_parameters is not new_parameters:
            old_parameters._elements.discard(self)
            if not old_parameters._elements and self._network is not None:
                # This was the only element using the old parameters, remove them from the network
                self._network._remove_parameters(self.element_type, old_parameters.id)
        if self not in new_parameters._elements:
            new_parameters._elements.add(self)
            if self._network is not None:
                self._network._add_parameters(self.element_type, new_parameters)

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_currents = (
                self._cy_element.get_port_current(0),
                self._cy_element.get_port_current(self._n),
            )
            self._res_voltages = (
                self._cy_element.get_port_potential(0) * SQRT3,
                self._cy_element.get_port_potential(self._n) * SQRT3,
            )

    def _res_currents_getter(self, warning: bool) -> tuple[complex, complex]:
        self._refresh_results()
        return self._res_getter(value=self._res_currents, warning=warning)

    def _res_voltages_getter(self, warning: bool) -> tuple[complex, complex]:
        self._refresh_results()
        return self._res_getter(value=self._res_voltages, warning=warning)

    def _res_powers_getter(self, warning: bool) -> tuple[complex, complex]:
        current1, current2 = self._res_currents_getter(warning=warning)
        voltage1, voltage2 = self._res_voltages_getter(warning=False)  # warn only once
        power1 = voltage1 * current1.conjugate() * SQRT3
        power2 = voltage2 * current2.conjugate() * SQRT3
        return power1, power2

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_currents(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch currents (A)."""
        return self._res_currents_getter(warning=True)

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_voltages(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch voltages (V)."""
        return self._res_voltages_getter(warning=True)

    @property
    @ureg_wraps(("VA", "VA"), (None,))
    def res_powers(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch powers (VA)."""
        return self._res_powers_getter(warning=True)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        data["geometry"] = cls._parse_geometry(data.pop("geometry", None))
        results = data.pop("results", None)
        self = cls(**data)
        if include_results and results:
            s1, s2 = self._sides_suffixes
            current1 = complex(*results[f"current{s1}"])
            current2 = complex(*results[f"current{s2}"])
            voltage1 = complex(*results[f"voltage{s1}"])
            voltage2 = complex(*results[f"voltage{s2}"])
            self._res_currents = (current1, current2)
            self._res_voltages = (voltage1, voltage2)
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        s1, s2 = self._sides_suffixes
        data: JsonDict = {
            "id": self.id,
            f"bus{s1}": self.bus1.id,
            f"bus{s2}": self.bus2.id,
        }
        if self.geometry is not None:
            data["geometry"] = self.geometry.__geo_interface__
        if include_results:
            current1, current2 = self._res_currents_getter(warning=True)
            voltage1, voltage2 = self._res_voltages_getter(warning=False)  # warn only once
            data["results"] = {
                f"current{s1}": [current1.real, current1.imag],
                f"current{s2}": [current2.real, current2.imag],
                f"voltage{s1}": [voltage1.real, voltage1.imag],
                f"voltage{s2}": [voltage2.real, voltage2.imag],
            }
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current1, current2 = self._res_currents_getter(warning)
        voltage1, voltage2 = self._res_voltages_getter(warning=False)  # warn only once
        s1, s2 = self._sides_suffixes
        results: JsonDict = {
            "id": self.id,
            f"current{s1}": [current1.real, current1.imag],
            f"current{s2}": [current2.real, current2.imag],
            f"voltage{s1}": [voltage1.real, voltage1.imag],
            f"voltage{s2}": [voltage2.real, voltage2.imag],
        }
        if full:
            power1 = voltage1 * current1.conjugate() * SQRT3
            power2 = voltage2 * current2.conjugate() * SQRT3
            results[f"power{s1}"] = [power1.real, power1.imag]
            results[f"power{s2}"] = [power2.real, power2.imag]
        return results
