import logging
from typing import Any, Optional

from shapely import Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.transformers.parameters import TransformerParameters
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import BranchType

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch):
    """A generic transformer model.

    The model parameters are defined in the ``parameters``.
    """

    branch_type = BranchType.TRANSFORMER

    allowed_phases = Bus.allowed_phases
    """The allowed phases for a transformer are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"`` (three-phase transformer)
    - P-P or P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"an"``, ``"bn"``, ``"cn"`` (single-phase
      transformer or primary of split-phase transformer)
    - P-P-N: ``"abn"``, ``"bcn"``, ``"can"`` (secondary of split-phase transformer)
    """
    _allowed_phases_three = frozenset({"abc", "abcn"})
    _allowed_phases_single = frozenset({"ab", "bc", "ca", "an", "bn", "cn"})
    _allowed_phases_split_secondary = frozenset({"abn", "bcn", "can"})

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
                in the connected bus. By default determined from the transformer type.

            phases2:
                The phases of the second extremity of the transformer. See ``phases1``.

            geometry:
                The geometry of the transformer.
        """
        if geometry is not None and not isinstance(geometry, Point):
            msg = f"The geometry for a {type(self)} must be a point: {geometry.geom_type} provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_GEOMETRY_TYPE)

        if parameters.type == "single":
            phases1, phases2 = self._compute_phases_single(
                id=id, bus1=bus1, bus2=bus2, phases1=phases1, phases2=phases2
            )
        elif parameters.type == "split":
            phases1, phases2 = self._compute_phases_split(id=id, bus1=bus1, bus2=bus2, phases1=phases1, phases2=phases2)
        else:
            phases1, phases2 = self._compute_phases_three(
                id=id, bus1=bus1, bus2=bus2, parameters=parameters, phases1=phases1, phases2=phases2
            )

        super().__init__(id, bus1, bus2, phases1=phases1, phases2=phases2, geometry=geometry, **kwargs)
        self.tap = tap
        self._parameters = parameters

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
        self._invalidate_network_results()

    @property
    def parameters(self) -> TransformerParameters:
        """The parameters of the transformer."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: TransformerParameters) -> None:
        type1 = self._parameters.type
        type2 = value.type
        if type1 != type2:
            msg = f"The updated type changed for transformer {self.id!r}: {type1} to {type2}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE)
        self._parameters = value
        self._invalidate_network_results()

    def to_dict(self) -> JsonDict:
        return {**super().to_dict(), "params_id": self.parameters.id, "tap": self.tap}

    def _compute_phases_three(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        parameters: TransformerParameters,
        phases1: Optional[str],
        phases2: Optional[str],
    ) -> tuple[str, str]:
        w1_has_neutral = "y" in parameters.winding1.lower() or "z" in parameters.winding1.lower()
        w2_has_neutral = "y" in parameters.winding2.lower() or "z" in parameters.winding2.lower()
        if phases1 is None:
            phases1 = "abcn" if w1_has_neutral else "abc"
            phases1 = "".join(p for p in bus1.phases if p in phases1)
            self._check_phases(id, allowed_phases=self._allowed_phases_three, phases1=phases1)
        else:
            self._check_phases(id, allowed_phases=self._allowed_phases_three, phases1=phases1)
            self._check_bus_phases(id, bus1, phases1=phases1)
            transformer_phases = "abcn" if w1_has_neutral else "abc"
            phases_not_in_transformer = set(phases1) - set(transformer_phases)
            if phases_not_in_transformer:
                msg = (
                    f"Phases (1) {phases1!r} of transformer {id!r} are not compatible with its "
                    f"winding {parameters.winding1!r}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

        if phases2 is None:
            phases2 = "abcn" if w2_has_neutral else "abc"
            phases2 = "".join(p for p in bus2.phases if p in phases2)
            self._check_phases(id, allowed_phases=self._allowed_phases_three, phases2=phases2)
        else:
            self._check_phases(id, allowed_phases=self._allowed_phases_three, phases2=phases2)
            self._check_bus_phases(id, bus2, phases2=phases2)
            transformer_phases = "abcn" if w2_has_neutral else "abc"
            phases_not_in_transformer = set(phases2) - set(transformer_phases)
            if phases_not_in_transformer:
                msg = (
                    f"Phases (2) {phases2!r} of transformer {id!r} are not compatible with its "
                    f"winding {parameters.winding2!r}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

        return phases1, phases2

    def _compute_phases_single(
        self, id: Id, bus1: Bus, bus2: Bus, phases1: Optional[str], phases2: Optional[str]
    ) -> tuple[str, str]:
        if phases1 is None:
            phases1 = "".join(p for p in bus1.phases if p in bus2.phases)  # can't use set because order is important
            phases1 = phases1.replace("ac", "ca")
            if phases1 not in self._allowed_phases_single:
                msg = f"Phases (1) of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id, allowed_phases=self._allowed_phases_single, phases1=phases1)
            self._check_bus_phases(id, bus1, phases1=phases1)

        if phases2 is None:
            phases2 = "".join(p for p in bus1.phases if p in bus2.phases)  # can't use set because order is important
            phases2 = phases2.replace("ac", "ca")
            if phases2 not in self._allowed_phases_single:
                msg = f"Phases (2) of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id, allowed_phases=self._allowed_phases_single, phases2=phases2)
            self._check_bus_phases(id, bus2, phases2=phases2)

        return phases1, phases2

    def _compute_phases_split(
        self, id: Id, bus1: Bus, bus2: Bus, phases1: Optional[str], phases2: Optional[str]
    ) -> tuple[str, str]:
        if phases1 is None:
            phases1 = "".join(p for p in bus2.phases if p in bus1.phases and p != "n")
            phases1 = phases1.replace("ac", "ca")
            if phases1 not in self._allowed_phases_single:
                msg = f"Phases (1) of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id, allowed_phases=self._allowed_phases_single, phases1=phases1)
            self._check_bus_phases(id, bus1, phases1=phases1)

        if phases2 is None:
            phases2 = "".join(p for p in bus2.phases if p in bus1.phases or p == "n")
            if phases2 not in self._allowed_phases_split_secondary:
                msg = f"Phases (2) of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id, allowed_phases=self._allowed_phases_split_secondary, phases2=phases2)
            self._check_bus_phases(id, bus2, phases2=phases2)

        return phases1, phases2

    @staticmethod
    def _check_bus_phases(id: Id, bus: Bus, **kwargs: str) -> None:
        name, phases = kwargs.popitem()  # phases1 or phases2
        name = "Phases (1)" if name == "phases1" else "Phases (2)"
        phases_not_in_bus = set(phases) - set(bus.phases)
        if phases_not_in_bus:
            msg = (
                f"{name} {sorted(phases_not_in_bus)} of transformer {id!r} are not in phases "
                f"{bus.phases!r} of bus {bus.id!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
