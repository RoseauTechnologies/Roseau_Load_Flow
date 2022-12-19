import logging
from collections.abc import Sequence
from typing import Any, Optional

import numpy as np
import shapely.wkt
from pint import Quantity
from shapely.geometry import Point, shape

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element, Ground
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class Bus(Element, JsonMixin):
    """An electrical bus."""

    allowed_phases = frozenset({"ab", "bc", "ca", "an", "bn", "cn", "abn", "bcn", "can", "abc", "abcn"})

    def __init__(
        self,
        id: Any,
        *,
        phases: str,
        geometry: Optional[Point] = None,
        potentials: Optional[Sequence[complex]] = None,
        ground: Optional[Ground] = None,
        **kwargs,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                The identifier of the bus.

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
        self._check_phases(id, phases=phases)
        super().__init__(**kwargs)
        self.id = id
        self.phases = phases
        if ground is not None:
            ground.connected_elements.append(self)
            self.connected_elements.append(ground)

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

    def __str__(self) -> str:
        return f"id={self.id!r} - phases={self.phases!r}"

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
        """The voltage results of the bus (Only available after a load flow).

        For a "Star Bus", the voltages are ``[Van, Vbn, Vcn]``, for a "Delta Bus", they are
        ``[Vab, Vbc, Vca]``.

        Returns:
            An array of the voltages.
        """
        # TODO use self.potentials with the check
        if "n" in self.phases:
            return self._potentials[:-1] - self._potentials[-1]  # an, bn, cn
        else:
            return np.asarray(
                self._potentials[1] - self._potentials[0],  # ab
                self._potentials[2] - self._potentials[1],  # bc
                self._potentials[0] - self._potentials[2],  # ca
            )

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any], ground: Optional[Ground]) -> "Bus":
        if "geometry" not in data:
            geometry = None
        elif isinstance(data["geometry"], str):
            geometry = shapely.wkt.loads(data["geometry"])
        else:
            geometry = shape(data["geometry"])

        return cls(
            id=data["id"],
            phases=data["phases"],
            geometry=geometry,
            potentials=data.get("potentials"),
            ground=ground,
        )

    def to_dict(self) -> dict[str, Any]:
        res = {"id": self.id, "phases": self.phases, "loads": [], "sources": []}
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res
