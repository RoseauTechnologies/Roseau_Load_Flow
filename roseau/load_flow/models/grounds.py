import logging
import warnings
from typing import TYPE_CHECKING, Final, Literal

import numpy as np
from typing_extensions import Self, deprecated

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Complex, Id, JsonDict, Side
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level, one_or_more_repr
from roseau.load_flow_engine.cy_engine import CyBranch, CyGround, CySimplifiedLine, CySwitch

if TYPE_CHECKING:
    from roseau.load_flow.models.buses import Bus

logger = logging.getLogger(__name__)


class Ground(Element[CyGround]):
    """A ground element represents the earth in the network.

    The ground itself is modeled as an ideal infinite plane. The ground potential is NOT assumed to
    be zero unless explicitly set with a :class:`PotentialRef` element.

    Grounds have two main usages:

    1. To connect shunt components of a line. A line with shunt components requires a ground element
       to be passed to its constructor.
    2. To connect terminal elements (buses, sources and loads) and branch elements (lines, switches
       and transformers) via a :class:`GroundConnection`. These connections can be ideal (zero
       impedance) or impedant (non-zero impedance).
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
    def connections(self) -> list["GroundConnection"]:
        """The connections to the ground."""
        return self._connections[:]

    @property
    @deprecated("`Ground.connected_buses` is deprecated, use `Ground.connections` instead.")
    def connected_buses(self) -> dict[Id, str]:
        """The bus ID and phase of the buses connected to this ground.

        .. deprecated:: 0.12.0
            Use the more flexible :attr:`Ground.connections` attribute instead.
        """
        return {gc.element.id: gc.phase for gc in self._connections if gc.element.element_type == "bus"}

    @deprecated("`Ground.connect` is deprecated, use the `GroundConnection` class instead.")
    def connect(self, bus: "Bus", phase: str = "n") -> None:
        """Connect the ground to a bus on the given phase.

        .. deprecated:: 0.12.0
            Use the :class:`GroundConnection` class instead. It is more flexible and provides more
            features including non-ideal (impedant) connections.

        Args:
            bus:
                The bus to connect to.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}`` and must be
                present in the bus phases. Defaults to ``"n"``.
        """
        connected_buses = {gc.element.id for gc in self._connections if gc.element.element_type == "bus"}
        if bus.id in connected_buses:
            msg = f"Ground {self.id!r} is already connected to bus {bus.id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_BUS_ID)
        GroundConnection(ground=self, element=bus, phase=phase)

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
        return self._res_potential_getter(warning=True)  # type: ignore

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        results = data.pop("results", None)
        self = cls(**data)
        if include_results and results:
            self._res_potential = complex(*results["potential"])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data: JsonDict = {"id": self.id}
        if include_results:
            v = self._res_potential_getter(warning=True)
            data["results"] = {"potential": [v.real, v.imag]}
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        v = self._res_potential_getter(warning)
        return {"id": self.id, "potential": [v.real, v.imag]}


class GroundConnection(Element[CySimplifiedLine | CySwitch]):
    """An ideal or impedant connection to the ground."""

    element_type: Final = "ground_connection"
    allowed_phases: Final = frozenset({"a", "b", "c", "n"})

    def __init__(
        self,
        id: Id | None = None,
        *,
        ground: Ground,
        element: Element,
        impedance: Complex | Q_[Complex] = 0j,
        phase: str = "n",
        side: Side = None,
        on_connected: Literal["raise", "warn", "ignore"] = "raise",
    ) -> None:
        """Ground connection constructor.

        Args:
            id:
                A unique ID of the ground connection in the network. If not provided, it will be
                generated roughly as `{element.id} {(side) or ''} phase {phase} to {ground.id}`.

            ground:
                The ground object to connect to.

            element:
                The branch or terminal element to connect to the ground.

            impedance:
                The impedance of the connection to the ground (ohm). Defaults to 0.

            phase:
                The phase of the connection. It must be one of ``{"a", "b", "c", "n"}``. Defaults to
                ``"n"``.

            side:
                The side of the branch element to connect to. If the element is a transformer, this
                must be either ``'HV'`` or ``'LV'``. If the element is a line or a switch, this must
                be either ``1`` or ``2``. For other elements, this must be ``None``.

            on_connected:
                The action to take if *other phases* of the element are already connected to this
                ground. If ``"raise"`` (default), raise an error. If ``"warn"``, issue a warning. If
                ``"ignore"``, do nothing. An error is always raised if the passed phase of the
                element is already connected to this ground.
        """
        if on_connected not in {"warn", "raise", "ignore"}:
            raise ValueError(f"Invalid value for `on_connected`: {on_connected!r}")

        # Check the element type and the side.
        if element.element_type in {"transformer", "line", "switch"}:
            if side not in (1, 2, "HV", "LV"):
                side_status = "Side is missing" if side is None else f"Invalid side {side!r}"
                expected_sides = ("HV", "LV") if element.element_type == "transformer" else (1, 2)
                msg = f"{side_status} for {element._element_info}, expected one of {expected_sides}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_BRANCH_SIDE)
        elif element.element_type in {"bus", "source", "load"}:
            if side is not None:
                msg = f"Side cannot be used with {element.element_type} elements, only with branches."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_BRANCH_SIDE)
        else:
            msg = f"Cannot connect {element._element_info} to the ground."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)

        if id is None:
            side_phase = f"{phase!r}" if side is None else f"({side}) {phase!r}"
            id = f"{element.element_type} {element.id!r} phase {side_phase!r} to ground {ground.id!r}"
        # Check the phase is valid.
        self._check_phases(id, phases=phase)

        # Check the phase is present in the element phases.
        self._element_phases_attr = "phases" + {1: "1", 2: "2", "HV": "1", "LV": "2", None: ""}[side]
        self._element_phases: str = getattr(element, self._element_phases_attr)
        pretty_phases = f"{side} phases" if side in ("HV", "LV") else f"phases {side}" if side in (1, 2) else "phases"
        if phase not in self._element_phases:
            msg = (
                f"Phase {phase!r} is not present in {pretty_phases} {self._element_phases!r} of "
                f"{element._element_info}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)

        # Check if the element is already connected to this ground
        connected_phases = [gc._phase for gc in ground._connections if gc._element is element and gc._side == side]
        if connected_phases:
            pretty_phase = pretty_phases.replace("phases", "phase")
            if phase in connected_phases:
                msg = (
                    f"Ground {ground.id!r} is already connected to {pretty_phase} {phase!r} of {element._element_info}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
            if on_connected != "ignore":
                connections, _ = one_or_more_repr(connected_phases, pretty_phase, pretty_phases)
                msg = f"Ground {ground.id!r} is already connected to {connections} of {element._element_info}."
                if on_connected == "raise":
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GROUND_ID)
                else:
                    warnings.warn(msg, stacklevel=find_stack_level())

        super().__init__(id)
        self._connect(ground, element)
        self._ground = ground
        self._element = element
        self._phase = phase
        self._side: Side = side
        self.on_connected: Literal["raise", "warn", "ignore"] = on_connected
        self.impedance = impedance
        ground._connections.append(self)

        self._res_current: complex | None = None

    def __repr__(self) -> str:
        parts = [
            f"id={self.id!r}",
            f"ground={self._ground.id!r}",
            f"element={self._element.id!r}",
            f"impedance={self._impedance!r}",
            f"phase={self._phase!r}",
        ]
        if self._side is not None:
            parts.append(f"side={self._side!r}")
        parts.append(f"on_connected={self.on_connected!r}")
        return f"<{type(self).__name__}: {', '.join(parts)}>"

    @property
    def phase(self) -> str:
        """The phase of the connection to the ground."""
        return self._phase

    @property
    def side(self) -> Side:
        """The side of the element to connect to."""
        return self._side

    @property
    @ureg_wraps("ohm", (None,))
    def impedance(self) -> Q_[complex]:
        """The impedance of the connection to the ground (ohm)."""
        return self._impedance  # type: ignore

    @impedance.setter
    @ureg_wraps(None, (None, "ohm"))
    def impedance(self, value: Complex | Q_[Complex]) -> None:
        self._impedance = complex(value)
        self._invalidate_network_results()
        if np.isclose(self._impedance, 0):
            if not isinstance(self._cy_element, CySwitch):
                if self._cy_element is not None:
                    self._cy_element.disconnect()
                self._cy_element = CySwitch(n=1)
                self._cy_connect()
            else:
                pass  # do nothing
        else:
            z_line = np.array([[self._impedance]], dtype=np.complex128)
            if not isinstance(self._cy_element, CySimplifiedLine):
                if self._cy_element is not None:
                    self._cy_element.disconnect()
                self._cy_element = CySimplifiedLine(n=1, z_line=z_line)
                self._cy_connect()
            else:
                self._cy_element.update_line_parameters(z_line=z_line)

    @property
    def ground(self) -> Ground:
        """The ground connected to."""
        return self._ground

    @property
    def element(self) -> Element:
        """The element connected to the ground."""
        return self._element

    def _cy_connect(self) -> None:
        assert self._cy_element is not None
        assert self._ground._cy_element is not None, "Ground cannot be disconnected."
        i = self._element_phases.index(self._phase)
        if self._side is None:
            self._element._cy_element.connect(self._cy_element, [(i, 0)])
        else:
            assert isinstance(self._element._cy_element, CyBranch)
            beginning = self._side in (1, "HV")
            self._element._cy_element.connect(self._cy_element, [(i, 0)], beginning=beginning)
        self._cy_element.connect(self._ground._cy_element, [(0, 0)], beginning=False)

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_current = self._cy_element.get_currents(n1=1, n2=1)[0][0]

    def _res_current_getter(self, warning: bool) -> complex:
        self._refresh_results()
        return self._res_getter(value=self._res_current, warning=warning)

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The load flow result of the current flowing through this connection to the ground (A)."""
        return self._res_current_getter(warning=True)  # type: ignore

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        results = data.pop("results", None)
        data["impedance"] = complex(*data.pop("impedance"))
        self = cls(**data)
        if include_results and results:
            current = complex(*results["current"])
            self._res_current = current
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data: JsonDict = {
            "id": self.id,
            "ground": self._ground.id,
            "element": {"id": self._element.id, "type": self._element.element_type},
            "phase": self._phase,
            "impedance": [self._impedance.real, self._impedance.imag],
            "side": self._side,
            "on_connected": self.on_connected,
        }
        if include_results:
            current = self._res_current_getter(warning=True)
            data["results"] = {"current": [current.real, current.imag]}
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        current = self._res_current_getter(warning)
        results: JsonDict = {"id": self.id, "current": [current.real, current.imag]}
        return results
