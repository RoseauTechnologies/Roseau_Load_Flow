import logging
from abc import ABC, abstractmethod
from typing import ClassVar

from roseau.load_flow import SQRT3
from roseau.load_flow.typing import Id, JsonDict, Side
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import abstractattrs
from roseau.load_flow_engine.cy_engine import CyBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import _CyE_co
from roseau.load_flow_single.models.terminals import AbstractTerminal

logger = logging.getLogger(__name__)


class AbstractConnectable(AbstractTerminal[_CyE_co], ABC):
    """A base class for elements connected to a bus."""

    @abstractmethod
    def __init__(self, id: Id, bus: Bus, *, n: int, side: Side | None = None) -> None:
        """AbstractConnectable constructor.

        Args:
            id:
                A unique ID of the element in its dictionary in the network.

            n:
                The number of ports of the element.

            bus:
                The bus to connect the element to.

            side:
                For branches, this is the side of the branch associated with to be connected to the
                bus. It can be ``"HV"`` or ``"LV"`` for transformers or ``1`` or ``2`` for lines and
                switches. This is ``None`` for other elements.
        """
        super().__init__(id, n=n, side=side)
        self._check_compatible_phase_tech(bus)
        self._connect(bus)
        self._bus = bus
        self._res_current: complex | None = None

    def __repr__(self) -> str:
        args = [f"id={self.id!r}", f"bus={self._bus.id!r}"]
        side = f"-{self._side_value}" if self._side_value is not None else ""
        return f"<{type(self).__name__}{side}: {', '.join(args)}>"

    @property
    def bus(self) -> Bus:
        """The bus of the element."""
        return self._bus

    def _cy_connect(self) -> None:
        connections = [(i, i) for i in range(self._n)]
        if isinstance(self._cy_element, CyBranch):
            self._cy_element.connect_side(self.bus._cy_element, connections, beginning=self._side_index == 0)
        else:
            self.bus._cy_element.connect(self._cy_element, connections)

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            super()._refresh_results()
            self._res_current = self._cy_element.get_port_current(0)

    def _res_current_getter(self, warning: bool) -> complex:
        self._refresh_results()
        return self._res_getter(self._res_current, warning)

    def _res_power_getter(self, warning: bool) -> complex:
        current = self._res_current_getter(warning)
        voltage = self._res_voltage_getter(warning=False)  # warn only once
        return voltage * current.conjugate() * SQRT3

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The load flow result of the element's current (A)."""
        return self._res_current_getter(warning=True)  # type: ignore

    @property
    @ureg_wraps("VA", (None,))
    def res_power(self) -> Q_[complex]:
        """The load flow result of the element's power (VA)."""
        return self._res_power_getter(warning=True)  # type: ignore

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            super()._parse_results_from_dict(data, include_results=include_results)
            self._res_current = complex(*data["results"][f"current{self._side_suffix}"])

    def _to_dict(self, include_results: bool) -> JsonDict:
        data: JsonDict = {"id": self.id, f"bus{self._side_suffix}": self.bus.id}
        if include_results:
            current = self._res_current_getter(warning=True)
            voltage = self._res_voltage_getter(warning=False)  # warn only once
            data["results"] = {
                f"current{self._side_suffix}": [current.real, current.imag],
                f"voltage{self._side_suffix}": [voltage.real, voltage.imag],
            }
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current = self._res_current_getter(warning)
        voltage = self._res_voltage_getter(warning=False)  # warn only once
        results: JsonDict = {
            "id": self.id,
            f"current{self._side_suffix}": [current.real, current.imag],
            f"voltage{self._side_suffix}": [voltage.real, voltage.imag],
        }
        if full:
            power = voltage * current.conjugate() * SQRT3
            results[f"power{self._side_suffix}"] = [power.real, power.imag]
        return results


@abstractattrs("type")
class AbstractDisconnectable(AbstractConnectable[_CyE_co], ABC):
    """A base class for disconnectable elements in the network (loads, sources, etc.)."""

    type: ClassVar[str]

    def __repr__(self) -> str:
        s = super().__repr__()
        if self._is_disconnected:
            return f"{s} (disconnected)"
        return s

    @property
    def is_disconnected(self) -> bool:
        """Is this element disconnected from the network?"""
        return self._is_disconnected

    def disconnect(self) -> None:
        """Disconnect this element from the network. It cannot be used afterwards."""
        self._disconnect()

    def _refresh_results(self) -> None:
        self._raise_disconnected_error()
        super()._refresh_results()

    def _to_dict(self, include_results: bool) -> JsonDict:
        self._raise_disconnected_error()
        results = super()._to_dict(include_results=include_results)
        results["type"] = self.type
        return results

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning, full=full)
        results["type"] = self.type
        return results
