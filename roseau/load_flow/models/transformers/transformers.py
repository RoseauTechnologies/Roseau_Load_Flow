import logging
from typing import Any, Optional

from shapely.geometry import Point

from roseau.load_flow.models.buses.buses import AbstractBus
from roseau.load_flow.models.core.core import AbstractBranch
from roseau.load_flow.models.transformers.transformers_characteristics import TransformerCharacteristics
from roseau.load_flow.utils import BranchType, TransformerType
from roseau.load_flow.utils.exceptions import ThundersIOError, ThundersValueError

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch):
    type = BranchType.TRANSFORMER

    def __init__(
        self,
        id_: Any,
        n1: int,
        n2: int,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """Transformer constructor.

        Args:
            id_:
                The identifier of the transformer.

            n1:
                The number of port of the first extremity.

            n2:
                The number of port of the second extremity.

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
            raise ThundersValueError(msg)

        if tap > 1.1:
            logger.warning(f"The provided tap {tap:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if tap < 0.9:
            logger.warning(f"The provided tap {tap:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")

        super().__init__(n1=n1, n2=n2, bus1=bus1, bus2=bus2, id_=id_, geometry=geometry)
        self.transformer_characteristics = transformer_characteristics
        self.tap = tap

    @staticmethod
    def from_dict(
        id_: Any,
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

            id_:
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
        winding1, winding2, phase_displacement = TransformerType.extract_windings(transformer_characteristics.windings)
        if "Y" in winding1 and "y" in winding2:
            return WyeWyeTransformer(
                id_=id_,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "D" in winding1 and "y" in winding2:
            return DeltaWyeTransformer(
                id_=id_,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "D" in winding1 and "z" in winding2:
            return DeltaZigzagTransformer(
                id_=id_,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "D" in winding1 and "d" in winding2:
            return DeltaDeltaTransformer(
                id_=id_,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "Y" in winding1 and "d" in winding2:
            return WyeDeltaTransformer(
                id_=id_,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "Y" in winding1 and "z" in winding2:
            return WyeZigzagTransformer(
                id_=id_,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        else:
            msg = f"Transformer {transformer_characteristics.windings} is not implemented yet..."
            logger.error(msg)
            raise ThundersIOError(msg)

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

    def update_transformer_parameters(
        self, transformer_characteristics: TransformerCharacteristics, tap: float = 1.0
    ) -> None:
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
            raise ThundersValueError(
                f"The updated windings changed for transformer {self.id!r}: {windings1} to {windings2}."
            )
        if tap > 1.1:
            logger.warning(f"The provided tap {tap:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if tap < 0.9:
            logger.warning(f"The provided tap {tap:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")

        self.transformer_characteristics = transformer_characteristics
        self.tap = tap


class WyeWyeTransformer(Transformer):
    def __init__(
        self,
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """WyeWyeTransformer constructor

        Args:
            id_:
                The identifier of the transformer.

            bus1:
                bus to connect to the transformer

            bus2:
                bus to connect to the transformer

            transformer_characteristics:
                The characteristics of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(
            id_=id_,
            n1=4,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )
        if transformer_characteristics.winding1[0] != "Y" or transformer_characteristics.winding2[0] != "y":
            raise ThundersValueError(
                f"Bad windings for WyeWyeTransformer {self.id!r}: {transformer_characteristics.windings}"
            )


class DeltaWyeTransformer(Transformer):
    def __init__(
        self,
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """DeltaWyeTransformer constructor

        Args:
            id_:
                The identifier of the transformer.

            bus1:
                bus to connect to the transformer

            bus2:
                bus to connect to the transformer

            transformer_characteristics:
                The characteristics of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(
            id_=id_,
            n1=3,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )
        if transformer_characteristics.winding1[0] != "D" or transformer_characteristics.winding2[0] != "y":
            raise ThundersValueError(
                f"Bad windings for DeltaWyeTransformer {self.id!r}: {transformer_characteristics.windings}"
            )


class DeltaDeltaTransformer(Transformer):
    def __init__(
        self,
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """DeltaWyeTransformer constructor

        Args:
            id_:
                The identifier of the transformer.

            bus1:
                bus to connect to the transformer

            bus2:
                bus to connect to the transformer

            transformer_characteristics:
                The characteristics of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(
            id_=id_,
            n1=3,
            n2=3,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )
        if transformer_characteristics.winding1[0] != "D" or transformer_characteristics.winding2[0] != "d":
            raise ThundersValueError(
                f"Bad windings for DeltaDeltaTransformer {self.id!r}: {transformer_characteristics.windings}"
            )


class WyeDeltaTransformer(Transformer):
    def __init__(
        self,
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """DeltaWyeTransformer constructor

        Args:
            id_:
                The identifier of the transformer.

            bus1:
                bus to connect to the transformer

            bus2:
                bus to connect to the transformer

            transformer_characteristics:
                The characteristics of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(
            id_=id_,
            n1=4,
            n2=3,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )
        if transformer_characteristics.winding1[0] != "Y" or transformer_characteristics.winding2[0] != "d":
            raise ThundersValueError(
                f"Bad windings for WyeDeltaTransformer {self.id!r}: {transformer_characteristics.windings}"
            )


class WyeZigzagTransformer(Transformer):
    def __init__(
        self,
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """DeltaWyeTransformer constructor

        Args:
            id_:
                The identifier of the transformer.

            bus1:
                bus to connect to the transformer

            bus2:
                bus to connect to the transformer

            transformer_characteristics:
                The characteristics of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(
            id_=id_,
            n1=4,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )
        if transformer_characteristics.winding1[0] != "Y" or transformer_characteristics.winding2[0] != "z":
            raise ThundersValueError(
                f"Bad windings for WyeZigzagTransformer {self.id!r}: {transformer_characteristics.windings}"
            )


class DeltaZigzagTransformer(Transformer):
    def __init__(
        self,
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """DeltaWyeTransformer constructor

        Args:
            id_:
                The identifier of the transformer.

            bus1:
                bus to connect to the transformer

            bus2:
                bus to connect to the transformer

            transformer_characteristics:
                The characteristics of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(
            id_=id_,
            n1=3,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )
        if transformer_characteristics.winding1[0] != "D" or transformer_characteristics.winding2[0] != "z":
            raise ThundersValueError(
                f"Bad windings for DeltaZigzagTransformer {self.id!r}: {transformer_characteristics.windings}"
            )


class IdealDeltaWye(Transformer):
    def __init__(
        self,
        id_: Any,
        bus1: AbstractBus,
        bus2: AbstractBus,
        transformer_characteristics: TransformerCharacteristics,
        tap: float = 1.0,
        geometry: Optional[Point] = None,
    ) -> None:
        """DeltaWyeTransformer constructor

        Args:
            id_:
                The identifier of the transformer.

            bus1:
                bus to connect to the transformer

            bus2:
                bus to connect to the transformer

            transformer_characteristics:
                The characteristics of the transformer.

            tap:
                The tap of the transformer, for example 1.02.

            geometry:
                The geometry of the transformer.
        """
        super().__init__(
            id_=id_,
            n1=3,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
        )
        _, _, k, orientation = transformer_characteristics.to_zyk()
