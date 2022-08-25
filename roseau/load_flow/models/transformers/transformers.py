import logging
from abc import ABC
from typing import Any, Optional

from shapely.geometry import Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import AbstractBus
from roseau.load_flow.models.core import AbstractBranch
from roseau.load_flow.models.transformers.transformers_characteristics import TransformerCharacteristics
from roseau.load_flow.utils import BranchType, TransformerType

logger = logging.getLogger(__name__)


class AbstractTransformer(AbstractBranch, ABC):
    branch_type = BranchType.TRANSFORMER
    dd_class: Optional[type["DeltaDeltaTransformer"]] = None
    dy_class: Optional[type["DeltaWyeTransformer"]] = None
    dz_class: Optional[type["DeltaZigzagTransformer"]] = None
    yd_class: Optional[type["WyeDeltaTransformer"]] = None
    yy_class: Optional[type["WyeWyeTransformer"]] = None
    yz_class: Optional[type["WyeZigzagTransformer"]] = None

    def __init__(
        self,
        id: Any,
        n1: int,
        n2: int,
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
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)

        if tap > 1.1:
            logger.warning(f"The provided tap {tap:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if tap < 0.9:
            logger.warning(f"The provided tap {tap:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")

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
    ) -> "AbstractTransformer":
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
        winding1, winding2, phase_displacement = TransformerType.extract_windings(transformer_characteristics.windings)
        if "Y" in winding1 and "y" in winding2:
            return cls.yy_class(
                id=id,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "D" in winding1 and "y" in winding2:
            return cls.dy_class(
                id=id,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "D" in winding1 and "z" in winding2:
            return cls.dz_class(
                id=id,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "D" in winding1 and "d" in winding2:
            return cls.dd_class(
                id=id,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "Y" in winding1 and "d" in winding2:
            return cls.yd_class(
                id=id,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        elif "Y" in winding1 and "z" in winding2:
            return cls.yz_class(
                id=id,
                bus1=bus1,
                bus2=bus2,
                transformer_characteristics=transformer_characteristics,
                tap=tap,
                geometry=geometry,
            )
        else:
            msg = f"Transformer {transformer_characteristics.windings} is not implemented yet..."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)

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
            msg = f"The updated windings changed for transformer {self.id!r}: {windings1} to {windings2}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
        if tap > 1.1:
            logger.warning(f"The provided tap {tap:.2f} is higher than 1.1. A good value is between 0.9 and 1.1.")
        if tap < 0.9:
            logger.warning(f"The provided tap {tap:.2f} is lower than 0.9. A good value is between 0.9 and 1.1.")

        self.transformer_characteristics = transformer_characteristics
        self.tap = tap


class WyeWyeTransformer(AbstractTransformer):
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
        """WyeWyeTransformer constructor

        Args:
            id:
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
            id=id,
            n1=4,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
            **kwargs,
        )
        if transformer_characteristics.winding1[0] != "Y" or transformer_characteristics.winding2[0] != "y":
            msg = f"Bad windings for WyeWyeTransformer {self.id!r}: {transformer_characteristics.windings}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)


class DeltaWyeTransformer(AbstractTransformer):
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
        """DeltaWyeTransformer constructor

        Args:
            id:
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
            id=id,
            n1=3,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
            **kwargs,
        )
        if transformer_characteristics.winding1[0] != "D" or transformer_characteristics.winding2[0] != "y":
            msg = f"Bad windings for DeltaWyeTransformer {self.id!r}: {transformer_characteristics.windings}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)


class DeltaDeltaTransformer(AbstractTransformer):
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
        """DeltaDeltaTransformer constructor

        Args:
            id:
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
            id=id,
            n1=3,
            n2=3,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
            **kwargs,
        )
        if transformer_characteristics.winding1[0] != "D" or transformer_characteristics.winding2[0] != "d":
            msg = f"Bad windings for DeltaDeltaTransformer {self.id!r}: {transformer_characteristics.windings}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)


class WyeDeltaTransformer(AbstractTransformer):
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
        """WyeDeltaTransformer

        Args:
            id:
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
            id=id,
            n1=4,
            n2=3,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
            **kwargs,
        )
        if transformer_characteristics.winding1[0] != "Y" or transformer_characteristics.winding2[0] != "d":
            msg = f"Bad windings for WyeDeltaTransformer {self.id!r}: {transformer_characteristics.windings}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)


class WyeZigzagTransformer(AbstractTransformer):
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
        """WyeZigzagTransformer constructor

        Args:
            id:
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
            id=id,
            n1=4,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
            **kwargs,
        )
        if transformer_characteristics.winding1[0] != "Y" or transformer_characteristics.winding2[0] != "z":
            msg = f"Bad windings for WyeZigzagTransformer {self.id!r}: {transformer_characteristics.windings}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)


class DeltaZigzagTransformer(AbstractTransformer):
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
        """DeltaZigzagTransformer constructor

        Args:
            id:
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
            id=id,
            n1=3,
            n2=4,
            bus1=bus1,
            bus2=bus2,
            transformer_characteristics=transformer_characteristics,
            tap=tap,
            geometry=geometry,
            **kwargs,
        )
        if transformer_characteristics.winding1[0] != "D" or transformer_characteristics.winding2[0] != "z":
            msg = f"Bad windings for DeltaZigzagTransformer {self.id!r}: {transformer_characteristics.windings}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)


AbstractTransformer.dd_class = DeltaDeltaTransformer
AbstractTransformer.dy_class = DeltaWyeTransformer
AbstractTransformer.dz_class = DeltaZigzagTransformer
AbstractTransformer.yd_class = WyeDeltaTransformer
AbstractTransformer.yy_class = WyeWyeTransformer
AbstractTransformer.yz_class = WyeZigzagTransformer
