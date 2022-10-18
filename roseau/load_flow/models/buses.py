import logging
from abc import ABC
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


class AbstractBus(Element, JsonMixin, ABC):
    """This is an abstract class for all different types of buses."""

    _voltage_source_class: Optional[type["VoltageSource"]] = None
    _bus_class: Optional[type["Bus"]] = None

    def __init__(
        self,
        id: Any,
        n: int,
        potentials: Optional[Sequence[complex]] = None,
        geometry: Optional[Point] = None,
        **kwargs,
    ) -> None:
        """Abstract bus constructor.

        Args:
            id:
                The identifier of the bus.

            n:
                Number of ports ie number of phases.

            potentials:
                List of initial potentials of each phase.

            geometry:
                The geometry of the bus.
        """
        super().__init__(**kwargs)
        self.id = id
        self.n = n

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

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data, ground):
        if "geometry" not in data:
            geometry = None
        elif isinstance(data["geometry"], str):
            geometry = shapely.wkt.loads(data["geometry"])
        else:
            geometry = shape(data["geometry"])

        potentials = data["potentials"] if "potentials" in data else None
        if data["type"] == "slack":
            v = data["voltages"]
            voltages = [v["va"][0] + 1j * v["va"][1], v["vb"][0] + 1j * v["vb"][1], v["vc"][0] + 1j * v["vc"][1]]
            return cls._voltage_source_class(
                id=data["id"], n=4, ground=ground, source_voltages=voltages, potentials=potentials, geometry=geometry
            )
        else:
            if data["type"] not in ["bus", "bus_neutral"]:
                msg = f"Bad bus type for bus {data['id']}: {data['type']}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_BUS_TYPE)
            if "neutral" in data["type"]:
                bus = cls._bus_class(id=data["id"], n=4, potentials=potentials, geometry=geometry)
            else:
                bus = cls._bus_class(id=data["id"], n=3, potentials=potentials, geometry=geometry)
            return bus


class VoltageSource(AbstractBus):
    """A VoltageSource bus.

    The equations are the following:

    .. math::
        \\left(V_{\\mathrm{a}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{a}} \\\\
        \\left(V_{\\mathrm{b}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{b}} \\\\
        \\left(V_{\\mathrm{c}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{c}}
    """

    def __init__(
        self,
        id: Any,
        n: int,
        ground: Optional[Ground],
        source_voltages: Sequence[complex],
        potentials: Optional[Sequence[complex]] = None,
        geometry: Optional[Point] = None,
        **kwargs,
    ):
        """VoltageSource constructor.

        Args:
            id:
                The identifier of the bus.

            n:
                Number of ports.

            ground:
                The ground to connect the neutral to.

            source_voltages:
                List of the voltages of the source (V).

            potentials:
                List of initial potentials of each phase (V).

            geometry:
                The geometry of the bus.
        """
        super().__init__(
            id=id, n=n, ground=ground, voltages=source_voltages, potentials=potentials, geometry=geometry, **kwargs
        )
        if len(source_voltages) != n - 1:
            msg = f"Incorrect number of voltages: {len(source_voltages)} instead of {n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)

        if isinstance(source_voltages, Quantity):
            source_voltages = source_voltages.m_as("V")

        if ground is not None:
            ground.connected_elements.append(self)
            self.connected_elements.append(ground)

        self.source_voltages = source_voltages

    @ureg.wraps(None, (None, "V"), strict=False)
    def update_source_voltages(self, source_voltages: Sequence[complex]) -> None:
        """Change the voltages of the source

        Args:
            source_voltages:
                The new voltages.
        """
        if len(source_voltages) != self.n - 1:
            msg = f"Incorrect number of voltages: {len(source_voltages)} instead of {self.n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)

        self.source_voltages = source_voltages

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        va = self.source_voltages[0]
        vb = self.source_voltages[1]
        vc = self.source_voltages[2]
        res = {
            "id": self.id,
            "type": "slack",
            "loads": [],
            "voltages": {
                "va": [va.real, va.imag],
                "vb": [vb.real, vb.imag],
                "vc": [vc.real, vc.imag],
            },
        }
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res


class Bus(AbstractBus):
    """This class is used for a general purpose bus."""

    def __init__(
        self,
        id: Any,
        n: int,
        potentials: Optional[Sequence[complex]] = None,
        geometry: Optional[Point] = None,
        **kwargs,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                The identifier of the bus.

            n:
                Number of ports.

            potentials:
                List of initial potentials of each phase (V)

            geometry:
                The geometry of the bus.
        """
        super().__init__(id=id, n=n, potentials=potentials, geometry=geometry, **kwargs)

    #
    # Json Mixin interface
    #
    def to_dict(self) -> dict[str, Any]:
        bus_type = "bus" if self.n == 3 else "bus_neutral"
        res = {"id": self.id, "type": bus_type, "loads": []}
        if self.geometry is not None:
            res["geometry"] = self.geometry.__geo_interface__
        return res


AbstractBus._voltage_source_class = VoltageSource
AbstractBus._bus_class = Bus
