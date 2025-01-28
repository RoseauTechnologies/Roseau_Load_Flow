import logging

from shapely.geometry.base import BaseGeometry

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow_engine.cy_engine import CySwitch
from roseau.load_flow_single.models.branches import AbstractBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.sources import VoltageSource

logger = logging.getLogger(__name__)


class Switch(AbstractBranch[CySwitch]):
    """A general purpose switch branch."""

    def __init__(self, id: Id, bus1: Bus, bus2: Bus, *, geometry: BaseGeometry | None = None) -> None:
        """Switch constructor.

        Args:
            id:
                A unique ID of the switch in the network switches.

            bus1:
                First bus to connect to the switch.

            bus2:
                Second bus to connect to the switch.

            geometry:
                The geometry of the switch.
        """
        super().__init__(id=id, bus1=bus1, bus2=bus2, n=1, geometry=geometry)
        self._check_elements()
        self._check_loop()
        self._cy_element = CySwitch(1)
        self._cy_connect()

    def _check_loop(self) -> None:
        """Check that there are no switch loops, raise an exception if it is the case."""
        visited_1: set[Element] = set()
        elements: list[Element] = [self.bus1]
        while elements:
            element = elements.pop(-1)
            visited_1.add(element)
            for e in element._connected_elements:
                if e not in visited_1 and (isinstance(e, (Bus, Switch))) and e != self:
                    elements.append(e)
        visited_2: set[Element] = set()
        elements = [self.bus2]
        while elements:
            element = elements.pop(-1)
            visited_2.add(element)
            for e in element._connected_elements:
                if e not in visited_2 and (isinstance(e, (Bus, Switch))) and e != self:
                    elements.append(e)
        if visited_1.intersection(visited_2):
            msg = (
                f"Connecting switch {self.id!r} between buses {self.bus1.id!r} and {self.bus2.id!r} "
                f"creates a switch loop. Current flow in several switch-only branches between buses "
                f"cannot be computed."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.SWITCHES_LOOP)

    def _check_elements(self) -> None:
        """Check that we can connect both elements."""
        if any(isinstance(e, VoltageSource) for e in self.bus1._connected_elements) and any(
            isinstance(e, VoltageSource) for e in self.bus2._connected_elements
        ):
            msg = (
                f"Connecting switch {self.id!r} between buses {self.bus1.id!r} and {self.bus2.id!r} "
                f"that both have a voltage source is not allowed."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION)

    #
    # Json Mixin interface
    #
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

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current1, current2 = self._res_currents_getter(warning)
        results = {
            "id": self.id,
            "current1": [current1.real, current1.imag],
            "current2": [current2.real, current2.imag],
        }
        if full:
            voltage1, voltage2 = self._res_voltages_getter(warning=False)
            results["voltage1"] = [voltage1.real, voltage1.imag]
            results["voltage2"] = [voltage2.real, voltage2.imag]
            power1, power2 = self._res_powers_getter(
                warning=False,
                voltage1=voltage1,
                voltage2=voltage2,
                current1=current1,
                current2=current2,
            )
            results["power1"] = [power1.real, power1.imag]
            results["power2"] = [power2.real, power2.imag]
        return results
