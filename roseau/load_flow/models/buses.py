import logging
from collections.abc import Sequence
from typing import Any, Optional

import numpy as np
from shapely.geometry import Point

from roseau.load_flow.converters import calculate_voltage_phases, calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict, Self
from roseau.load_flow.units import ureg

logger = logging.getLogger(__name__)


class Bus(Element):
    """An electrical bus."""

    allowed_phases = frozenset({"ab", "bc", "ca", "an", "bn", "cn", "abn", "bcn", "can", "abc", "abcn"})

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
                The geometry of the bus.

            potentials:
                List of initial potentials of each phase.

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

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r})"

    @property
    def potentials(self) -> np.ndarray:
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
    def res_potentials(self) -> np.ndarray:
        """The load flow result of the bus potentials (V)."""
        return self._res_potentials_getter(warning=True)

    def _res_voltages_getter(self, warning: bool) -> np.ndarray:
        potentials = np.asarray(self._res_potentials_getter(warning=warning))
        return calculate_voltages(potentials, self.phases)

    @property
    def res_voltages(self) -> np.ndarray:
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
        return cls(id=data["id"], phases=data["phases"], geometry=geometry, potentials=potentials)

    def to_dict(self) -> JsonDict:
        res = {"id": self.id, "phases": self.phases}
        if not np.allclose(self.potentials, 0):
            res["potentials"] = [[v.real, v.imag] for v in self.potentials]
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res
