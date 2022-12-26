import logging
from typing import Any, Optional

from shapely.geometry import Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import AbstractBranch
from roseau.load_flow.models.transformers.parameters import TransformerParameters
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import BranchType

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch):
    """A generic transformer model.

    The model parameters and windings type are defined in the ``parameters``.
    """

    branch_type = BranchType.TRANSFORMER

    allowed_phases = frozenset({"abc", "abcn"})  # Only these for now

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        parameters: TransformerParameters,
        tap: float = 1.0,
        phases1: Optional[str] = None,
        phases2: Optional[str] = None,
        geometry: Optional[Point] = None,
        **kwargs: Any,
    ) -> None:
        """Transformer constructor.

        Args:
            id:
                A unique ID of the transformer in the network branches.

            bus1:
                Bus to connect the first extremity of the transformer.

            bus2:
                Bus to connect the first extremity of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            parameters:
                The parameters of the transformer.

            phases1:
                The phases of the first extremity of the transformer. A string like ``"abc"`` or
                ``"abcn"`` etc. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases must be present
                in the connected bus. By default determined from the transformer windings.

            phases2:
                The phases of the second extremity of the transformer. See ``phases1``.

            geometry:
                The geometry of the transformer.
        """
        if geometry is not None and not isinstance(geometry, Point):
            msg = f"The geometry for a {type(self)} must be a point: {geometry.geom_type} provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)

        self.tap = tap
        # Compute the phases if not provided, check them if provided
        w1_has_neutral = "n" in parameters.winding1.lower()
        w2_has_neutral = "n" in parameters.winding2.lower()
        if phases1 is None:
            phases1 = "abcn" if w1_has_neutral else "abc"
        else:
            self._check_phases(id, phases1=phases1)
            if (w1_has_neutral and "n" not in phases1) or (not w1_has_neutral and "n" in phases1):
                msg = (
                    f"Phases (1) {phases1!r} of transformer {id!r} are not compatible with its "
                    f"winding {parameters.winding1!r}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
        if phases2 is None:
            phases2 = "abcn" if w2_has_neutral else "abc"
        else:
            self._check_phases(id, phases2=phases2)
            if (w2_has_neutral and "n" not in phases2) or (not w2_has_neutral and "n" in phases2):
                msg = (
                    f"Phases (2) {phases2!r} of transformer {id!r} are not compatible with its "
                    f"winding {parameters.winding2!r}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
        # Check that the phases are in the bus (computed or provided)
        phases_not_in_bus1 = set(phases1) - set(bus1.phases)
        if phases_not_in_bus1:
            msg = (
                f"Phases (1) {sorted(phases_not_in_bus1)} of transformer {id!r} are not in phases "
                f"{bus1.phases!r} of bus {bus1.id!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        phases_not_in_bus2 = set(phases2) - set(bus2.phases)
        if phases_not_in_bus2:
            msg = (
                f"Phases (2) {sorted(phases_not_in_bus2)} of transformer {id!r} are not in phases "
                f"{bus2.phases!r} of bus {bus2.id!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        super().__init__(id, bus1, bus2, phases1=phases1, phases2=phases2, geometry=geometry, **kwargs)
        self.parameters = parameters

    @property
    def tap(self) -> float:
        """The tap of the transformer, for example 1.02."""
        return self._tap

    @tap.setter
    def tap(self, value: float) -> None:
        if value > 1.1:
            logger.warning(f"The provided tap {value:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if value < 0.9:
            logger.warning(f"The provided tap {value:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")
        self._tap = value

    @property
    def parameters(self) -> TransformerParameters:
        """The parameters of the transformer."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: TransformerParameters) -> None:
        self._parameters = value
        windings1 = self.parameters.windings
        windings2 = value.windings
        if windings1 != windings2:
            msg = f"The updated windings changed for transformer {self.id!r}: {windings1} to {windings2}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)

    def to_dict(self) -> JsonDict:
        return {**super().to_dict(), "params_id": self.parameters.id, "tap": self.tap}
