import logging
from typing import Any, Optional, Union

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.grounds import Ground
from roseau.load_flow.typing import Id, JsonDict, Self

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

    def __init__(self, id: Id, element: Union[Bus, Ground], *, phase: Optional[str] = None, **kwargs: Any) -> None:
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
        self.phase = phase
        self.element = element
        self._connect(element)
        self._res_current: Optional[complex] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, element={self.element!r}, phase={self.phase!r})"

    def _res_current_getter(self, warning: bool) -> complex:
        return self._res_getter(self._res_current, warning)

    @property
    def res_current(self) -> complex:
        """The sum of the currents (A) of the connection associated to the potential reference.

        This sum should be equal to 0 after the load flow.
        """
        return self._res_current_getter(warning=True)

    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        return cls(data["id"], data["element"], phase=data.get("phases"))

    def to_dict(self) -> JsonDict:
        res = {"id": self.id}
        e = self.element
        if isinstance(e, Bus):
            res["bus"] = e.id
            res["phases"] = self.phase
        elif isinstance(e, Ground):
            res["ground"] = e.id
        else:
            assert False, f"Unexpected element type {type(e).__name__}"
        return res
