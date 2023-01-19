import logging
from typing import Any

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict

logger = logging.getLogger(__name__)


class Ground(Element):
    """This element defines the ground.

    Only buses and lines that have shunt components can be connected to a ground.

    1. Connecting to a bus:

       To connect a ground to a bus on a given phase, use the :meth:`Ground.connect` method.
       This method lets you specify the bus to connect to as well as the phase of the connection.
       If the bus has a neutral and the phase is not specified, the ground will be connected to the
       neutral, otherwise, an error will be raised because the phase is needed.

    2. Connecting to a line with shunt components:

       To connect a ground to a line with shunt components, pass the ground object to the
       :class:`Line` constructor. Note that the ground connection is mandatory for shunt lines.
    """

    allowed_phases = frozenset({"a", "b", "c", "n"})

    def __init__(self, id: Id, **kwargs: Any) -> None:
        """Ground constructor.

        Args:
            id:
                A unique ID of the ground in the network grounds.
        """
        super().__init__(id, **kwargs)
        self._bus_phases: dict[Id, str] = {}
        """A map of bus id to phase connected to this ground."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    def connect(self, bus: Bus, phase: str = "n") -> None:
        """Connect the ground to a bus on the given phase.

        Args:
            bus:
                The bus to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the bus phases. Defaults to ``"n"``.
        """
        self._check_phases(self.id, phases=phase)
        if phase not in bus.phases:
            msg = f"Cannot connect a ground to phase {phase!r} of bus {bus.id!r} that has phases {bus.phases!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        self._connect(bus)
        self._bus_phases[bus.id] = phase

    @classmethod
    def from_dict(cls, data: JsonDict) -> "Ground":
        self = cls(data["id"])
        self._bus_phases = data["buses"]
        return self

    def to_dict(self) -> JsonDict:
        # Shunt lines and potential references will have the ground in their dict not here.
        return {
            "id": self.id,
            "buses": [{"id": bus_id, "phase": phase} for bus_id, phase in self._bus_phases.items()],
        }
