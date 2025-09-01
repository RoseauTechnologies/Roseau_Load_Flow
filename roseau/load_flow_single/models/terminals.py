import logging
from abc import ABC, abstractmethod

from roseau.load_flow import SQRT3
from roseau.load_flow.typing import Id, JsonDict, Side
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import SIDE_DESC, SIDE_INDEX, SIDE_SUFFIX
from roseau.load_flow_single.models.core import Element, _CyE_co

logger = logging.getLogger(__name__)


class AbstractTerminal(Element[_CyE_co], ABC):
    """A base class for all the terminals (buses, load, sources, etc.) of the network."""

    @abstractmethod
    def __init__(self, id: Id, *, n: int, side: Side | None = None) -> None:
        """AbstractTerminal constructor.

        Args:
            id:
                A unique ID of the terminal in its dictionary of the network.

            n:
                The number of ports of the element.

            side:
                For branches, this is the side of the branch associated with to be connected to the
                bus. It can be ``"HV"`` or ``"LV"`` for transformers or ``1`` or ``2`` for lines and
                switches. This is ``None`` for other elements.
        """
        super().__init__(id)
        self._n = n
        self._side_value: Side | None = side
        self._side_index = SIDE_INDEX[side]
        self._side_suffix = SIDE_SUFFIX[side]
        self._side_desc = SIDE_DESC[side]
        self._res_voltage: complex | None = None

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_voltage = self._cy_element.get_port_potential(0) * SQRT3

    def _res_voltage_getter(self, warning: bool) -> complex:
        self._refresh_results()
        return self._res_getter(self._res_voltage, warning)

    @property
    @ureg_wraps("V", (None,))
    def res_voltage(self) -> Q_[complex]:
        """The load flow result of the element's voltage (V)."""
        return self._res_voltage_getter(warning=True)  # type: ignore

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            self._res_voltage = complex(*data["results"][f"voltage{self._side_suffix}"])
            self._fetch_results = False
            self._no_results = False

    def _to_dict(self, include_results: bool) -> JsonDict:
        data: JsonDict = {"id": self.id}
        if include_results:
            voltage = self._res_voltage_getter(warning=True)
            data["results"] = {f"voltage{self._side_suffix}": [voltage.real, voltage.imag]}
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        voltage = self._res_voltage_getter(warning)
        results: JsonDict = {"id": self.id, f"voltage{self._side_suffix}": [voltage.real, voltage.imag]}
        return results
