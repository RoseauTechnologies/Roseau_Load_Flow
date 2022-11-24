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
    """An electrical bus.

    The voltage equations are the following:

    .. math::
        \\left(V_{\\mathrm{a}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{a}} \\\\
        \\left(V_{\\mathrm{b}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{b}} \\\\
        \\left(V_{\\mathrm{c}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{c}}

    Where $U$ is the voltage and $V$ is the node potential.
    """

    def __init__(
        self,
        id: Any,
        n: int,
        geometry: Optional[Point] = None,
        potentials: Optional[Sequence[complex]] = None,
        ground: Optional[Ground] = None,
        source_voltages: Optional[Sequence[complex]] = None,
        **kwargs,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                The identifier of the bus.

            n:
                Number of ports ie number of phases.

            geometry:
                The geometry of the bus.

            potentials:
                List of initial potentials of each phase.

            ground:
                The ground of the bus.

            source_voltages:
                The source voltages of the bus. If provided, it is used to fix the bus voltages.
                In other terms, the bus becomes a slack bus which by definition a bus with a known
                voltage. A non-slack bus must not set a source_voltages.
        """
        super().__init__(**kwargs)
        self.id = id
        self.n = n
        if source_voltages is None:
            # The bus is a normal bus (non slack): PV bus or PQ bus.
            self.type = "bus" if n < 4 else "bus_neutral"
        else:
            # The bus is a slack bus: The voltage is known and fixed.
            self.type = "slack"
            if len(source_voltages) != n - 1:
                msg = f"Incorrect number of voltages: {len(source_voltages)} instead of {n - 1}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)

            if isinstance(source_voltages, Quantity):
                source_voltages = source_voltages.m_as("V")

            if ground is not None:
                ground.connected_elements.append(self)
                self.connected_elements.append(ground)

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
        self.source_voltages = source_voltages
        self.geometry = geometry
        self._potentials = None

    def __repr__(self) -> str:
        s = f"{type(self).__name__}(id={self.id!r}, n={self.n}"
        if self._potentials is not None:
            s += f", potentials={self.potentials!r}"
        if self.geometry is not None:
            s += f", geometry={self.geometry})"
        return s

    def __str__(self) -> str:
        return f"id={self.id} - n={self.n}"

    @property
    @ureg.wraps("V", None, strict=False)
    def potentials(self) -> np.ndarray:
        """Return the potentials of the element.

        Returns:
            An array of the potentials.
        """
        return self._potentials

    @potentials.setter
    def potentials(self, value: np.ndarray):
        self._potentials = value

    @property
    @ureg.wraps("V", None, strict=False)
    def voltages(self) -> np.ndarray:
        """Return the voltages of the element, as [Van, Vbn, Vcn] for a wye bus, or [Vab, Vbc, Vca] for a delta bus.

        Returns:
            An array of the voltages.
        """
        if self.n == 3:
            return np.asarray(
                self._potentials[1] - self._potentials[0],  # ab
                self._potentials[2] - self._potentials[1],  # bc
                self._potentials[0] - self._potentials[2],  # ca
            )
        else:
            return self._potentials[: self.n - 1] - self._potentials[self.n - 1]  # an, bn, cn

    @ureg.wraps(None, (None, "V"), strict=False)
    def update_source_voltages(self, source_voltages: Sequence[complex]) -> None:
        """Change the voltages of the source; only possible with a slack bus.

        Args:
            source_voltages:
                The new voltages.
        """
        if self.type != "slack":
            msg = "Cannot update the source voltages of a non-slack bus"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION)
        if len(source_voltages) != self.n - 1:
            msg = f"Incorrect number of voltages: {len(source_voltages)} instead of {self.n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)

        self.source_voltages = source_voltages

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

        potentials = data.get("potentials")

        if data["type"] == "slack":
            n = 4
            v = data["voltages"]
            voltages = [complex(*v["va"]), complex(*v["vb"]), complex(*v["vc"])]
        elif data["type"] not in ("bus", "bus_neutral"):
            n = 4 if "neutral" in data["type"] else 3
            voltages = None
        else:
            msg = f"Bad bus type for bus {data['id']}: {data['type']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BUS_TYPE)

        return cls(
            id=data["id"],
            n=n,
            ground=ground,
            potentials=potentials,
            geometry=geometry,
            source_voltages=voltages,
        )

    def to_dict(self) -> dict[str, Any]:
        res = {"id": self.id, "type": self.type, "loads": []}
        if self.type == "slack":
            assert self.source_voltages is not None
            va = self.source_voltages[0]
            vb = self.source_voltages[1]
            vc = self.source_voltages[2]
            res["voltages"] = (
                {
                    "va": [va.real, va.imag],
                    "vb": [vb.real, vb.imag],
                    "vc": [vc.real, vc.imag],
                },
            )
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res
