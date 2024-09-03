import logging

from roseau.load_flow.models.loads import PowerLoad as TriPowerLoad
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.single.buses import Bus
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


class PowerLoad(TriPowerLoad):
    """A constant power load."""

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        powers: complex,
        flexible_params: FlexibleParameter | None = None,
    ) -> None:
        """PowerLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            powers:
                An array-like of the powers for each phase component. Either complex values (VA)
                or a :class:`Quantity <roseau.load_flow.units.Q_>` of complex values.

            flexible_params:
                A list of :class:`FlexibleParameters` object, one for each phase. When provided,
                the load is considered as flexible (or controllable) and the parameters are used
                to compute the flexible power of the load.
        """
        flexible_params = [flexible_params] if flexible_params is not None else None
        super().__init__(id=id, bus=bus, powers=[powers], flexible_params=flexible_params)
