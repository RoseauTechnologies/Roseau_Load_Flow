import logging

from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.sources import VoltageSource as TriVoltageSource
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


class VoltageSource(TriVoltageSource):
    """A voltage source."""

    def __init__(self, id: Id, bus: Bus, *, voltages: complex) -> None:
        """Voltage source constructor.

        Args:
            id:
                A unique ID of the voltage source in the network sources.

            bus:
                The bus of the voltage source.

            voltages:
                An array-like of the voltages of the source. They will be set on the connected bus.
                If the source has a neutral connection, the voltages are considered phase-to-neutral
                voltages, otherwise they are the phase-to-phase voltages. Either complex values (V)
                or a :class:`Quantity <roseau.load_flow.units.Q_>` of complex values.
        """
        super().__init__(id=id, bus=bus, voltages=[voltages])
