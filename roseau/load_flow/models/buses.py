import logging
from collections.abc import Sequence
from typing import Any, Optional

import numpy as np
from shapely import Point
from typing_extensions import Self

from roseau.load_flow.converters import calculate_voltage_phases, calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg

logger = logging.getLogger(__name__)


class Bus(Element):
    """An electrical bus."""

    allowed_phases = frozenset({"ab", "bc", "ca", "an", "bn", "cn", "abn", "bcn", "can", "abc", "abcn"})
    """The allowed phases for a bus are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"``
    - P-P or P-P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"abn"``, ``"bcn"``, ``"can"``
    - P-N: ``"an"``, ``"bn"``, ``"cn"``
    """

    def __init__(
        self,
        id: Id,
        *,
        phases: str,
        geometry: Optional[Point] = None,
        potentials: Optional[Sequence[complex]] = None,
        **kwargs: Any,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                A unique ID of the bus in the network buses.

            phases:
                The phases of the bus. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`Bus.allowed_phases`.

            geometry:
                An optional geometry of the bus; a :class:`~shapely.Point` that represents the
                x-y coordinates of the bus.

            potentials:
                An optional list of initial potentials of each phase of the bus.

            ground:
                The ground of the bus.
        """
        super().__init__(id, **kwargs)
        self._check_phases(id, phases=phases)
        self.phases = phases
        if potentials is None:
            potentials = [0] * len(phases)
        self.potentials = potentials
        self.geometry = geometry

        self._res_potentials: Optional[np.ndarray] = None
        self._short_circuit: Optional[tuple] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r})"

    @property
    @ureg.wraps("V", (None,), strict=False)
    def potentials(self) -> Q_:
        """The potentials of the bus (V)."""
        return self._potentials

    @potentials.setter
    @ureg.wraps(None, (None, "V"), strict=False)
    def potentials(self, value: Sequence[complex]) -> None:
        if len(value) != len(self.phases):
            msg = f"Incorrect number of potentials: {len(value)} instead of {len(self.phases)}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_POTENTIALS_SIZE)
        self._potentials = np.asarray(value, dtype=complex)
        self._invalidate_network_results()

    def _res_potentials_getter(self, warning: bool) -> np.ndarray:
        return self._res_getter(value=self._res_potentials, warning=warning)

    @property
    @ureg.wraps("V", (None,), strict=False)
    def res_potentials(self) -> Q_:
        """The load flow result of the bus potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(self, warning: bool) -> np.ndarray:
        potentials = np.asarray(self._res_potentials_getter(warning=warning))
        return calculate_voltages(potentials, self.phases)

    @property
    @ureg.wraps("V", (None,), strict=False)
    def res_voltages(self) -> Q_:
        """The load flow result of the bus voltages (V).

        If the bus has a neutral, the voltages are phase-neutral voltages for existing phases in
        the order ``[Van, Vbn, Vcn]``. If the bus does not have a neutral, phase-phase voltages
        are returned in the order ``[Vab, Vbc, Vca]``.
        """
        return self._res_voltages_getter(warning=True)

    @property
    def voltage_phases(self) -> list[str]:
        """The phases of the voltages."""
        return calculate_voltage_phases(self.phases)

    def _get_potentials_of(self, phases: str, warning: bool) -> np.ndarray:
        """Get the potentials of the given phases."""
        potentials = self._res_potentials_getter(warning)
        return np.array([potentials[self.phases.index(p)] for p in phases])

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        geometry = cls._parse_geometry(data.get("geometry"))
        potentials = data.get("potentials")
        if potentials is not None:
            potentials = [complex(v[0], v[1]) for v in potentials]
        res = cls(id=data["id"], phases=data["phases"], geometry=geometry, potentials=potentials)

        # Add short circuits
        short_circuit = data.get("short_circuits")
        if short_circuit is not None:
            res.short_circuit(*short_circuit)

        return res

    def to_dict(self) -> JsonDict:
        res = {"id": self.id, "phases": self.phases}
        if not np.allclose(self.potentials, 0):
            res["potentials"] = [[v.real, v.imag] for v in self._potentials]
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        if self._short_circuit is not None:
            res["short_circuits"] = list(self._short_circuit)
        return res

    def results_from_dict(self, data: JsonDict) -> None:
        self._res_potentials = np.array([complex(v[0], v[1]) for v in data["potentials"]], dtype=complex)

    def _results_to_dict(self, warning: bool) -> JsonDict:
        return {
            "id": self.id,
            "phases": self.phases,
            "potentials": [[v.real, v.imag] for v in self._res_potentials_getter(warning)],
        }

    def short_circuit(self, *phases: str) -> None:
        """Make a short-circuit by connecting multiple phases together.

        Args:
            phases:
                The phases to connect.
        """
        for phase in phases:
            if phase not in self.phases:
                msg = f"Phase {phase!r} is not in the phases {set(self.phases)} of bus {self.id!r}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        if self._short_circuit is not None:
            msg = f"A short circuit has already been made on bus {self.id!r} with phases {self._short_circuit}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.MULTIPLE_SHORT_CIRCUITS)

        self._short_circuit = phases

        if self.network is not None:
            self.network._valid = False
