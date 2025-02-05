import logging
from abc import ABC

from roseau.load_flow import SQRT3
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_single.models.core import Element, _CyE_co

logger = logging.getLogger(__name__)


class AbstractTerminal(Element[_CyE_co], ABC):
    """A base class for all the terminals (buses, load, sources, etc.) of the network."""

    def __init__(self, id: Id) -> None:
        """AbstractTerminal constructor.

        Args:
            id:
                A unique ID of the terminal in its dictionary of the network.
        """
        if type(self) is AbstractTerminal:
            raise TypeError("Can't instantiate abstract class AbstractTerminal")
        super().__init__(id)
        self._n = 2
        self._res_voltage: complex | None = None

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_voltage = self._cy_element.get_potentials(self._n)[0] * SQRT3

    def _res_voltage_getter(self, warning: bool) -> complex:
        self._refresh_results()
        return self._res_getter(value=self._res_voltage, warning=warning)

    @property
    @ureg_wraps("V", (None,))
    def res_voltage(self) -> Q_[complex]:
        """The load flow result of the element's voltage (V)."""
        return self._res_voltage_getter(warning=True)

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            self._res_voltage = complex(*data["results"]["voltage"])
            self._fetch_results = False
            self._no_results = False

    def _to_dict(self, include_results: bool) -> JsonDict:
        data: JsonDict = {"id": self.id}
        if include_results:
            voltage = self._res_voltage_getter(warning=True)
            data["results"] = {"voltage": [voltage.real, voltage.imag]}
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        voltage = self._res_voltage_getter(warning)
        results: JsonDict = {"id": self.id, "voltage": [voltage.real, voltage.imag]}
        return results
