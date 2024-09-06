import logging

from shapely.geometry.base import BaseGeometry

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.single.branches import AbstractBranch
from roseau.load_flow.single.buses import Bus
from roseau.load_flow.single.core import Element
from roseau.load_flow.single.sources import VoltageSource
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow_engine.cy_engine import CySwitch

logger = logging.getLogger(__name__)


class Switch(AbstractBranch):
    """A general purpose switch branch."""

    def __init__(self, id: Id, bus1: Bus, bus2: Bus, *, geometry: BaseGeometry | None = None) -> None:
        """Switch constructor.

        Args:
            id:
                A unique ID of the switch in the network branches.

            bus1:
                Bus to connect to the switch.

            bus2:
                Bus to connect to the switch.

            geometry:
                The geometry of the switch.
        """
        super().__init__(id=id, bus1=bus1, bus2=bus2, geometry=geometry)
        self._check_elements()
        self._check_loop()
        self._cy_element = CySwitch(self._n1)
        self._cy_connect()

    def _check_loop(self) -> None:
        """Check that there are no switch loop, raise an exception if it is the case"""
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
            msg = f"There is a loop of switch involving the switch {self.id!r}. It is not allowed."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.SWITCHES_LOOP)

    def _check_elements(self) -> None:
        """Check that we can connect both elements."""
        if any(isinstance(e, VoltageSource) for e in self.bus1._connected_elements) and any(
            isinstance(e, VoltageSource) for e in self.bus2._connected_elements
        ):
            msg = (
                f"The buses {self.bus1.id!r} and {self.bus2.id!r} both have a voltage source and "
                f"are connected with the switch {self.id!r}. It is not allowed."
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
            currents1, currents2 = self._res_currents_getter(warning=True)
            res["results"] = {
                "currents1": [[i.real, i.imag] for i in currents1],
                "currents2": [[i.real, i.imag] for i in currents2],
            }
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents1, currents2 = self._res_currents_getter(warning)
        results = {
            "id": self.id,
            "currents1": [[i.real, i.imag] for i in currents1],
            "currents2": [[i.real, i.imag] for i in currents2],
        }
        if full:
            potentials1, potentials2 = self._res_potentials_getter(warning=False)
            results["potentials1"] = [[v.real, v.imag] for v in potentials1]
            results["potentials2"] = [[v.real, v.imag] for v in potentials2]
            powers1, powers2 = self._res_powers_getter(
                warning=False,
                potentials1=potentials1,
                potentials2=potentials2,
                currents1=currents1,
                currents2=currents2,
            )
            results["powers1"] = [[s.real, s.imag] for s in powers1]
            results["powers2"] = [[s.real, s.imag] for s in powers2]
            voltages1, voltages2 = self._res_voltages_getter(
                warning=False, potentials1=potentials1, potentials2=potentials2
            )
            results["voltages1"] = [[v.real, v.imag] for v in voltages1]
            results["voltages2"] = [[v.real, v.imag] for v in voltages2]
        return results
