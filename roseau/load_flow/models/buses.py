import logging
from collections.abc import Sequence
from typing import Any, Optional

import numpy as np
import shapely.wkt
from pint import Quantity
from shapely.geometry import Point, shape

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils.units import ureg

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
        n = len(phases)
        if potentials is None:
            potentials = np.zeros(n, dtype=complex)
            self.initialized = False
        else:
            if len(potentials) != n:
                msg = f"Incorrect number of potentials: {len(potentials)} instead of {n}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_POTENTIALS_SIZE)
            if isinstance(potentials, Quantity):
                potentials = potentials.m_as("V")
            self.initialized = True
        self.initial_potentials = np.asarray(potentials)
        self.geometry = geometry
        self._potentials = None

    def __repr__(self) -> str:
        s = f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r}"
        if self._potentials is not None:
            s += f", potentials={self.potentials!r}"
        if self.geometry is not None:
            s += f", geometry={self.geometry}"
        s += ")"
        return s

    @property
    @ureg.wraps("V", None, strict=False)
    def potentials(self) -> np.ndarray:
        """The potentials results of the bus (Only available after a load flow)."""
        # TODO add a check to see if the load flow has been run (if self._potentials is None raise)
        return self._potentials

    @potentials.setter
    def potentials(self, value: np.ndarray) -> None:
        self._potentials = value

    @property
    @ureg.wraps("V", None, strict=False)
    def voltages(self) -> np.ndarray:
        """An array of the voltage results of the bus.

        If the bus has a neutral, the voltages are phase-neutral voltages for existing phases in
        the order ``[Van, Vbn, Vcn]``. If the bus does not have a neutral, phase-phase voltages
        are returned in the order ``[Vab, Vbc, Vca]``.
        """
        potentials = np.asarray(self._potentials)
        if "n" in self.phases:  # Van, Vbn, Vcn
            # we know "n" is the last phase
            return potentials[:-1] - potentials[-1]
        else:  # Vab, Vbc, Vca
            # np.roll(["a", "b", "c"], -1) -> ["b", "c", "a"]  # also works with single or double phase
            return np.roll(potentials, -1) - potentials

    @property
    def voltage_phases(self) -> list[str]:
        """The phases of the voltages."""
        if "n" in self.phases:  # "an", "bn", "cn"
            return [p + "n" for p in self.phases[:-1]]
        else:  # "ab", "bc", "ca"
            return [p1 + p2 for p1, p2 in zip(self.phases, np.roll(list(self.phases), -1))]

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> "Bus":
        if "geometry" not in data:
            geometry = None
        elif isinstance(data["geometry"], str):
            geometry = shapely.wkt.loads(data["geometry"])
        else:
            geometry = shape(data["geometry"])

        return cls(id=data["id"], phases=data["phases"], geometry=geometry, potentials=data.get("potentials"))

    def to_dict(self) -> JsonDict:
        res = {"id": self.id, "phases": self.phases, "loads": [], "sources": []}
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res
