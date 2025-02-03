import logging
import warnings
from typing import TYPE_CHECKING, Final, Literal, TypedDict

from typing_extensions import Self, deprecated

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_engine.cy_engine import CyGround

if TYPE_CHECKING:
    from roseau.load_flow.models.buses import Bus

logger = logging.getLogger(__name__)


class GroundConnection(TypedDict):
    element: Element
    phase: str
    side: Literal["HV", "LV", ""]
    # impedance: complex  # TODO


class Ground(Element[CyGround]):
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

    element_type: Final = "ground"
    allowed_phases: Final = frozenset({"a", "b", "c", "n"})

    def __init__(self, id: Id) -> None:
        """Ground constructor.

        Args:
            id:
                A unique ID of the ground in the network grounds.
        """
        super().__init__(id)
        self._connections: list[GroundConnection] = []
        self._res_potential: complex | None = None
        self._cy_element = CyGround()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    @property
    def connections(self) -> list[GroundConnection]:
        """The connections of the ground."""
        return self._connections[:]  # copy to avoid modification

    @property
    @deprecated("`Ground.connected_buses` is deprecated, use `Ground.connections` instead.")
    def connected_buses(self) -> dict[Id, str]:
        """The bus ID and phase of the buses connected to this ground.

        .. deprecated:: 0.12.0
            Use :attr:`Ground.connections` instead.
        """
        return {c["element"].id: c["phase"] for c in self._connections if c["element"].element_type == "bus"}

    @deprecated("`Ground.connect` is deprecated, use `Bus.connect_ground` instead.")
    def connect(self, bus: "Bus", phase: str = "n") -> None:
        """Connect the ground to a bus on the given phase.

        .. deprecated:: 0.12.0
            Use the :meth:`Bus.connect_ground` method instead.

        Args:
            bus:
                The bus to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the bus phases. Defaults to ``"n"``.
        """
        bus.connect_ground(ground=self, phase=phase)

    def _connect_common(
        self,
        element: Element,
        *,
        phase: str,
        on_connected: Literal["warn", "raise", "ignore"],
        element_phases: str,
        side: Literal["HV", "LV", ""],
    ) -> None:
        """Connect the ground to an element on the given phase.

        Args:
            element:
                The element to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the element's phases. Defaults to ``"n"``.

            on_connected:
                The action to take if this ground is already connected to *other phases* of this
                element. If ``"raise"`` (default), raise an error. If ``"warn"``, issue a warning.
                If ``"ignore"``, do nothing. An error is always raised if this ground is already
                connected to the *same phase*.

            phases_attr:
                The attribute of the element that contains the phases.

            side:
                The side of the connection. It must be one of ``"HV"``, ``"LV"`` or an empty string.
        """
        if on_connected not in {"warn", "raise", "ignore"}:
            raise ValueError(
                f"Invalid value {on_connected!r} for `on_connected`, must be one of 'warn', 'raise', 'ignore'."
            )
        pretty_phase = (side.upper() + " " if side else "") + "phase"  # "HV phase", etc.

        # Check the phase
        self._check_phases(self.id, phases=phase)
        if phase not in element_phases:
            msg = f"Phase {phase!r} is not present in the {pretty_phase}s of {element._element_info}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

        # Check if the element is already connected to the ground
        connected_phases = [gc["phase"] for gc in self._connections if gc["element"] is element and gc["side"] == side]
        if connected_phases:
            if phase in connected_phases:
                msg = f"Ground {self.id!r} is already connected to {pretty_phase} {phase!r} of {element._element_info}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
            if on_connected != "ignore":
                connections = (
                    f"{pretty_phase} {connected_phases[0]!r}"
                    if len(connected_phases) == 1
                    else f"{pretty_phase}s {connected_phases}"
                )
                msg = f"Ground {self.id!r} is already connected to {connections} of {element._element_info}."
                if on_connected == "raise":
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GROUND_ID)
                else:
                    warnings.warn(msg, stacklevel=find_stack_level())
        else:
            element._connect(self)
        self._connections.append({"element": element, "phase": phase, "side": side})

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_potential = self._cy_element.get_potentials(1)[0]

    def _res_potential_getter(self, warning: bool) -> complex:
        self._refresh_results()
        return self._res_getter(self._res_potential, warning)

    @property
    @ureg_wraps("V", (None,))
    def res_potential(self) -> Q_[complex]:
        """The load flow result of the ground potential (V)."""
        return self._res_potential_getter(warning=True)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        self = cls(data["id"])
        if include_results and "results" in data:
            self._res_potential = complex(*data["results"]["potential"])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        # Shunt lines and potential references will have the ground in their dict not here.
        data = {
            "id": self.id,
            "connections": [
                {
                    "element_type": conn["element"].element_type,
                    "element_id": conn["element"].id,
                    "phase": conn["phase"],
                    "side": conn["side"],
                }
                for conn in self._connections
            ],
        }
        if include_results:
            v = self._res_potential_getter(warning=True)
            data["results"] = {"potential": [v.real, v.imag]}
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        v = self._res_potential_getter(warning)
        return {"id": self.id, "potential": [v.real, v.imag]}
