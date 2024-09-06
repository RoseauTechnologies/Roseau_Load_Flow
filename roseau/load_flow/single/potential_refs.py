import logging

from typing_extensions import Self

from roseau.load_flow.single.core import Element
from roseau.load_flow.single.grounds import Ground
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyPotentialRef

logger = logging.getLogger(__name__)


class PotentialRef(Element):
    """A potential reference.

    This element sets the reference for the potentials in a network. Only one potential reference
    per galvanically isolated section of the network can be set.

    When passed a ground, the potential of the ground is set to 0V. When passed a bus, if the bus
    has a neutral, the potential of the neutral is set to 0V. If the bus does not have a neutral,
    the sum of the potentials of the bus phases is set to 0V. If the phases are specified for a
    bus, the sum of the potentials of the specified phases is set to 0V.
    """

    def __init__(self, id: Id, element: Ground) -> None:
        """PotentialRef constructor.

        Args:
            id:
                A unique ID of the potential reference in the network references.

            element:
                The ground element to set as a potential reference.
        """
        super().__init__(id)
        self.element = element
        self._connect(element)
        self._res_current: complex | None = None
        self._cy_element = CyPotentialRef()
        element._cy_element.connect(self._cy_element, [(0, 0)])

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, element={self.element!r})"

    def _res_current_getter(self, warning: bool) -> complex:
        if self._fetch_results:
            self._res_current = self._cy_element.get_current()
        return self._res_getter(self._res_current, warning)

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The sum of the currents (A) of the connection associated to the potential reference.

        This sum should be equal to 0 after the load flow.
        """
        return self._res_current_getter(warning=True)

    #
    # Jso Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        self = cls(id=data["id"], element=data["element"])
        if include_results and "results" in data:
            self._res_current = complex(*data["results"]["current"])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        res: JsonDict = {"id": self.id}
        e = self.element
        if isinstance(e, Ground):
            res["ground"] = e.id
        else:
            raise AssertionError(f"Unexpected element type {type(e).__name__}")
        if include_results:
            i = self._res_current_getter(warning=True)
            res["results"] = {"current": [i.real, i.imag]}
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        i = self._res_current_getter(warning)
        return {"id": self.id, "current": [i.real, i.imag]}
