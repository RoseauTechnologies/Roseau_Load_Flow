import logging

from shapely.geometry.base import BaseGeometry

from roseau.load_flow import Bus as TriBus
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_, ureg_wraps

logger = logging.getLogger(__name__)


class Bus(TriBus):
    """A multi-phase electrical bus."""

    def __init__(
        self,
        id: Id,
        *,
        geometry: BaseGeometry | None = None,
        potentials: complex | None = None,
        min_voltage: float | None = None,
        max_voltage: float | None = None,
    ) -> None:
        """Bus constructor.

        Args:
            id:
                A unique ID of the bus in the network buses.

            geometry:
                An optional geometry of the bus; a :class:`~shapely.Geometry` that represents the
                x-y coordinates of the bus.

            potentials:
                An optional initial potential of the bus. If given,
                these potentials are used as the starting point of the load flow computation.
                Either complex values (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

            min_voltage:
                An optional minimum voltage of the bus (V). It is not used in the load flow.
                It must be a phase-neutral voltage if the bus has a neutral, phase-phase otherwise.
                Either a float (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.

            max_voltage:
                An optional maximum voltage of the bus (V). It is not used in the load flow.
                It must be a phase-neutral voltage if the bus has a neutral, phase-phase otherwise.
                Either a float (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of float.
        """
        super().__init__(
            id=id,
            phases="an",
            geometry=geometry,
            potentials=[potentials] if potentials is not None else None,
            min_voltage=min_voltage,
            max_voltage=max_voltage,
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"

    @property
    @ureg_wraps("V", (None,))
    def res_potentials(self) -> Q_[complex]:
        """The load flow result of the bus potentials (V)."""
        return self._res_potentials_getter(warning=True)[0]
