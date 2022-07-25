import logging
from abc import ABCMeta
from typing import Any, Optional, Sequence

import numpy as np
import shapely.wkt
from shapely.geometry import Point

from roseau.load_flow.models.core.core import Element, Ground
from roseau.load_flow.utils.exceptions import ThundersIOError
from roseau.load_flow.utils.json_mixin import JsonMixin

logger = logging.getLogger(__name__)


class AbstractBus(Element, JsonMixin, metaclass=ABCMeta):
    def __init__(
        self, id_: Any, n: int, potentials: Optional[Sequence[complex]] = None, geometry: Optional[Point] = None
    ) -> None:
        """Abstract bus constructor.

        Args:
            id_:
                The identifier of the bus.

            n:
                Number of ports.

            potentials:
                List of initial potentials of each phase

            geometry:
                The geometry of the bus.
        """
        super().__init__()
        self.id = id_
        self.n = n

        if potentials is None:
            potentials = np.zeros(n, dtype=complex)
            self.initialized = False
        else:
            if len(potentials) != n:
                msg = f"Incorrect number of potentials: {len(potentials)} instead of {n}"
                logger.error(msg)
                raise ThundersIOError(msg)
            self.initialized = True
        self.initial_potentials = np.asarray(potentials)

        self.geometry = geometry

    def __str__(self) -> str:
        return f"id={self.id} - n={self.n}"

    @classmethod
    def from_dict(cls, data, ground):
        geometry = shapely.wkt.loads(data["geometry"]) if "geometry" in data else None
        potentials = data["potentials"] if "potentials" in data else None
        if data["type"] == "slack":
            v = data["voltages"]
            voltages = [v["va"][0] + 1j * v["va"][1], v["vb"][0] + 1j * v["vb"][1], v["vc"][0] + 1j * v["vc"][1]]
            return VoltageSource(
                id_=data["id"], n=4, ground=ground, voltages=voltages, potentials=potentials, geometry=geometry
            )
        else:
            if data["type"] not in ["bus", "bus_neutral"]:
                raise ThundersIOError(f"Bad bus type : {data['type']}")
            if "neutral" in data["type"]:
                bus = Bus(id_=data["id"], n=4, potentials=potentials, geometry=geometry)
            else:
                bus = Bus(id_=data["id"], n=3, potentials=potentials, geometry=geometry)
            return bus


class VoltageSource(AbstractBus):
    def __init__(
        self,
        id_: Any,
        n: int,
        ground: Optional[Ground],
        voltages: Sequence[complex],
        potentials: Optional[Sequence[complex]] = None,
        geometry: Optional[Point] = None,
    ):
        """VoltageSource constructor.

        Args:
            id_:
                The identifier of the bus.

            n:
                Number of ports.

            ground:
                The ground to connect the neutral to.

            voltages:
                List of the voltages of the source.

            potentials:
                List of initial potentials of each phase.

            geometry:
                The geometry of the bus.
        """
        super().__init__(id_=id_, n=n, potentials=potentials, geometry=geometry)
        if len(voltages) != n - 1:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {n - 1}"
            logger.error(msg)
            raise ThundersIOError(msg)

        self.voltages = voltages
        if ground is not None:
            ground.connect(self)

    def update_voltages(self, voltages: Sequence[complex]) -> None:
        """Change the voltages of the source

        Args:
            voltages:
                The new voltages.
        """
        if len(voltages) != self.n - 1:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {self.n - 1}"
            logger.error(msg)
            raise ThundersIOError(msg)

        self.voltages = voltages

    def to_dict(self) -> dict[str, Any]:
        va = self.voltages[0]
        vb = self.voltages[1]
        vc = self.voltages[2]
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
            res["geometry"] = str(self.geometry)
        return res


class Bus(AbstractBus):
    def __init__(
        self, id_: Any, n: int, potentials: Optional[Sequence[complex]] = None, geometry: Optional[Point] = None
    ) -> None:
        """Bus constructor.

        Args:
            id_:
                The identifier of the bus.

            n:
                Number of ports.

            potentials:
                List of initial potentials of each phase

            geometry:
                The geometry of the bus.
        """
        super().__init__(id_=id_, n=n, potentials=potentials, geometry=geometry)

    def to_dict(self) -> dict[str, Any]:
        bus_type = "bus" if self.n == 3 else "bus_neutral"
        res = {"id": self.id, "type": bus_type, "loads": []}
        if self.geometry is not None:
            res["geometry"] = str(self.geometry)
        return res
