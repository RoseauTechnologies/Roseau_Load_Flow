import logging
from typing import TYPE_CHECKING, Final

from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyGround

if TYPE_CHECKING:
    from roseau.load_flow.models.buses import Bus

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

    allowed_phases: Final = frozenset({"a", "b", "c", "n"})

    def __init__(self, id: Id) -> None:
        """Ground constructor.

        Args:
            id:
                A unique ID of the ground in the network grounds.
        """
        super().__init__(id)
        # A map of bus id to phase connected to this ground.
        self._connected_buses: dict[Id, str] = {}
        self._res_potential: complex | None = None
        self._cy_element = CyGround()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    def _res_potential_getter(self, warning: bool) -> complex:
        if self._fetch_results:
            self._res_potential = self._cy_element.get_potentials(1)[0]
        return self._res_getter(self._res_potential, warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potential(self) -> Q_[complex]:
        """The load flow result of the ground potential (V)."""
        return self._res_potential_getter(warning=True)

    @property
    def connected_buses(self) -> dict[Id, str]:
        """The bus ID and phase of the buses connected to this ground."""
        return self._connected_buses.copy()  # copy so that the user does not change it

    def connect(self, bus: "Bus", phase: str = "n") -> None:
        """Connect the ground to a bus on the given phase.

        Args:
            bus:
                The bus to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the bus phases. Defaults to ``"n"``.
        """
        if bus.id in self._connected_buses:
            msg = f"Ground {self.id!r} is already connected to bus {bus.id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_BUS_ID)
        self._check_phases(self.id, phases=phase)
        if phase not in bus.phases:
            msg = f"Cannot connect a ground to phase {phase!r} of bus {bus.id!r} that has phases {bus.phases!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        self._connect(bus)
        self._connected_buses[bus.id] = phase
        p = bus.phases.index(phase)
        bus._cy_element.connect(self._cy_element, [(p, 0)])

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        self = cls(data["id"])
        for bus_data in data["buses"]:
            self.connect(bus=bus_data["bus"], phase=bus_data["phase"])
        if include_results and "results" in data:
            self._res_potential = complex(*data["results"]["potential"])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        # Shunt lines and potential references will have the ground in their dict not here.
        res = {
            "id": self.id,
            "buses": [{"id": bus_id, "phase": phase} for bus_id, phase in self._connected_buses.items()],
        }
        if include_results:
            v = self._res_potential_getter(warning=True)
            res["results"] = {"potential": [v.real, v.imag]}
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        v = self._res_potential_getter(warning)
        return {"id": self.id, "potential": [v.real, v.imag]}
