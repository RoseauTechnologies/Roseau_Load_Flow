import logging
from typing import Any

from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.grounds import Ground
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyDeltaPotentialRef, CyPotentialRef

logger = logging.getLogger(__name__)


class PotentialRef(Element):
    """A potential reference.

    This element will set the reference of the potentials in a network. Only one potential
    reference per galvanically isolated section of the network can be set. The potential reference
    can be set on any bus or ground elements. If set on a bus with no neutral and without
    specifying the phase, the reference will be set as ``Va + Vb + Vc = 0``. For other buses, the
    default is ``Vn = 0``.
    """

    allowed_phases = frozenset({"a", "b", "c", "n"})

    def __init__(self, id: Id, element: Bus | Ground, *, phase: str | None = None, **kwargs: Any) -> None:
        """PotentialRef constructor.

        Args:
            id:
                A unique ID of the potential reference in the network references.

            element:
                The bus or ground element to set as a potential reference.

            phase:
                The phase of the bus to set as a potential reference. Cannot be used with a ground.
                If the element passed is a bus and the phase is not given, the neutral will be used
                if the bus has a neutral otherwise the equation ``Va + Vb + Vc = 0`` of the bus
                sets the potential reference.
        """
        super().__init__(id, **kwargs)
        if isinstance(element, Bus):
            if phase is None:
                phase = "n" if "n" in element.phases else None
            else:
                self._check_phases(id, phases=phase)
        elif isinstance(element, Ground):
            if phase is not None:
                msg = f"Potential reference {self.id!r} connected to the ground cannot have a phase."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            msg = f"Potential reference {self.id!r} is connected to {element!r} which is not a ground nor a bus."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        self._phase = phase
        self.element = element
        self._connect(element)
        self._res_current: complex | None = None
        if isinstance(element, Bus) and self.phase is None:
            n = len(element.phases)
            self._cy_element = CyDeltaPotentialRef(n)
            connections = [(i, i) for i in range(n)]
            element._cy_element.connect(self._cy_element, connections)
        else:
            self._cy_element = CyPotentialRef()
            if isinstance(element, Ground):
                element._cy_element.connect(self._cy_element, [(0, 0)])
            else:
                p = element.phases.find(self.phase)
                element._cy_element.connect(self._cy_element, [(p, 0)])

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, element={self.element!r}, phase={self.phase!r})"

    @property
    def phase(self) -> str | None:
        """The phase of the bus set as a potential reference."""
        return self._phase

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
        self = cls(data["id"], data["element"], phase=data.get("phases"))
        if include_results and "results" in data:
            self._res_current = complex(*data["results"]["current"])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id}
        e = self.element
        if isinstance(e, Bus):
            res["bus"] = e.id
            res["phases"] = self.phase
        elif isinstance(e, Ground):
            res["ground"] = e.id
        else:
            raise AssertionError(f"Unexpected element type {type(e).__name__}")
        if include_results:
            i = self._res_current_getter(warning=True)
            res["results"] = {"current": [i.real, i.imag]}
        return res

    def _results_from_dict(self, data: JsonDict) -> None:
        self._res_current = complex(*data["current"])
        self._fetch_results = False
        self._no_results = False

    def _results_to_dict(self, warning: bool) -> JsonDict:
        i = self._res_current_getter(warning)
        return {"id": self.id, "current": [i.real, i.imag]}
