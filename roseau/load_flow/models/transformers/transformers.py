import logging
from typing import Any, Optional

from shapely.geometry import Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import AbstractBus
from roseau.load_flow.models.core import AbstractBranch
from roseau.load_flow.models.transformers.transformers_characteristics import TransformerCharacteristics
from roseau.load_flow.utils import BranchType

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch):
    """A generic transformer model.

    The model parameters and windings type are defined in the ``transformer_characteristics``.
    """

    branch_type = BranchType.TRANSFORMER

    def __init__(
        self,
        id: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
        **kwargs,
    ) -> None:
        """Transformer constructor.

        Args:
            id:
                The identifier of the transformer.

            bus1:
                Bus to connect the first extremity of the transformer.

            bus2:
                Bus to connect the first extremity of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            transformer_characteristics:
                The characteristics of the transformer.

            geometry:
                The geometry of the transformer.
        """
        if geometry is not None and not isinstance(geometry, Point):
            msg = f"The geometry for a {type(self)} must be a point: {geometry.geom_type} provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)

        if tap > 1.1:
            logger.warning(f"The provided tap {tap:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if tap < 0.9:
            logger.warning(f"The provided tap {tap:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")

        # Compute the number of ports
        n1 = 3 if transformer_characteristics.winding1.lower().startswith("d") else 4
        n2 = 3 if transformer_characteristics.winding2.lower().startswith("d") else 4
        super().__init__(n1=n1, n2=n2, bus1=bus1, bus2=bus2, id=id, geometry=geometry, **kwargs)
        self.transformer_characteristics = transformer_characteristics
        self.tap = tap

    @classmethod
    def from_dict(
        cls,
        id: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        type_name: str,
        transformer_types: dict[str, TransformerCharacteristics],
        tap: float = 1.0,
        geometry: Optional[Point] = None,
        *args,
    ) -> "Transformer":
        """Transformer constructor from dict.

        Args:
            transformer_types:
                A dictionary of transformer characteristics by type name.

            type_name:
                The name of the transformer type.

            id:
                The identifier of the transformer.

            bus1:
                Bus to connect to the transformer.

            bus2:
                Bus to connect to the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.

        Returns:
            The constructed transformer.
        """
        transformer_characteristics = transformer_types[type_name]
        return cls(
            id=id,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )

    def to_dict(self) -> dict[str, Any]:
        res = super().to_dict()
        res.update(
            {
                "type_name": self.transformer_characteristics.type_name,
                "tap": self.tap,
                "type": "transformer",
            }
        )
        return res

    def update_characteristics(self, transformer_characteristics: TransformerCharacteristics, tap: float = 1.0) -> None:
        """Change the transformer parameters

        Args:
            transformer_characteristics:
                The new transformer characteristics.

            tap:
                The tap of the transformer, for example 1.02.
        """
        windings1 = self.transformer_characteristics.windings
        windings2 = transformer_characteristics.windings
        if windings1 != windings2:
            msg = f"The updated windings changed for transformer {self.id!r}: {windings1} to {windings2}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
        if tap > 1.1:
            logger.warning(f"The provided tap {tap:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if tap < 0.9:
            logger.warning(f"The provided tap {tap:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")

        self.transformer_characteristics = transformer_characteristics
        self.tap = tap
