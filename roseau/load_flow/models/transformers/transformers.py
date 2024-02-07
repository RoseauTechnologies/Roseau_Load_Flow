import logging
from typing import Any

from shapely import Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.branches import AbstractBranch
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.transformers.parameters import TransformerParameters
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_
from roseau.load_flow_engine.cy_engine import (
    CyCenterTransformer,
    CyExtendedTransformer,
    CyReducedTransformer,
    CySingleTransformer,
)

logger = logging.getLogger(__name__)


class Transformer(AbstractBranch):
    """A generic transformer model.

    The model parameters are defined using the ``parameters`` argument.
    """

    branch_type = "transformer"

    allowed_phases = Bus.allowed_phases
    """The allowed phases for a transformer are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"`` (three-phase transformer)
    - P-P or P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"an"``, ``"bn"``, ``"cn"`` (single-phase
      transformer or primary of center-tapped transformer)
    - P-P-N: ``"abn"``, ``"bcn"``, ``"can"`` (secondary of center-tapped transformer)
    """
    _allowed_phases_three = frozenset({"abc", "abcn"})
    _allowed_phases_single = frozenset({"ab", "bc", "ca", "an", "bn", "cn"})
    _allowed_phases_center_secondary = frozenset({"abn", "bcn", "can"})

    def __init__(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        *,
        parameters: TransformerParameters,
        tap: float = 1.0,
        phases1: str | None = None,
        phases2: str | None = None,
        geometry: Point | None = None,
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
                Parameters defining the electrical model of the transformer. This is an instance of
                the :class:`TransformerParameters` class and can be used by multiple transformers.

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
        elif parameters.type == "center":
            phases1, phases2 = self._compute_phases_center(
                id=id, bus1=bus1, bus2=bus2, phases1=phases1, phases2=phases2
            )
        else:
            phases1, phases2 = self._compute_phases_three(
                id=id, bus1=bus1, bus2=bus2, parameters=parameters, phases1=phases1, phases2=phases2
            )

        super().__init__(id, bus1, bus2, phases1=phases1, phases2=phases2, geometry=geometry, **kwargs)
        self.tap = tap
        self._parameters = parameters

        z2, ym, k, orientation = parameters.to_zyk()
        z2 = z2.m_as("ohm")
        ym = ym.m_as("S")
        if parameters.type == "single":
            self._cy_element = CySingleTransformer(z2=z2, ym=ym, k=k * tap)
        elif parameters.type == "center":
            self._cy_element = CyCenterTransformer(z2=z2, ym=ym, k=k * tap)
        else:
            if "Y" in parameters.winding1 and "y" in parameters.winding2:
                self._cy_element = CyReducedTransformer(
                    n1=4, n2=4, prim="Y", sec="y", z2=z2, ym=ym, k=k * tap, orientation=orientation
                )
            elif "D" in parameters.winding1 and "y" in parameters.winding2:
                self._cy_element = CyReducedTransformer(
                    n1=3, n2=4, prim="D", sec="y", z2=z2, ym=ym, k=k * tap, orientation=orientation
                )
            elif "D" in parameters.winding1 and "d" in parameters.winding2:
                self._cy_element = CyReducedTransformer(
                    n1=3, n2=3, prim="D", sec="d", z2=z2, ym=ym, k=k * tap, orientation=orientation
                )
            elif "Y" in parameters.winding1 and "d" in parameters.winding2:
                self._cy_element = CyReducedTransformer(
                    n1=4, n2=3, prim="Y", sec="d", z2=z2, ym=ym, k=k * tap, orientation=orientation
                )
            elif "Y" in parameters.winding1 and "z" in parameters.winding2:
                self._cy_element = CyExtendedTransformer(
                    n1=4, n2=4, prim="Y", sec="z", z2=z2, ym=ym, k=k * tap, orientation=orientation
                )
            elif "D" in parameters.winding1 and "z" in parameters.winding2:
                self._cy_element = CyExtendedTransformer(
                    n1=3, n2=4, prim="D", sec="z", z2=z2, ym=ym, k=k * tap, orientation=orientation
                )
            else:
                msg = f"Transformer {parameters.type} is not implemented yet..."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
        self._cy_connect()

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
        if self._cy_element is not None:
            z2, ym, k, _ = self.parameters.to_zyk()
            self._cy_element.update_transformer_parameters(z2.m_as("ohm"), ym.m_as("S"), k * value)

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
        if self._cy_element is not None:
            z2, ym, k, _ = value.to_zyk()
            self._cy_element.update_transformer_parameters(z2.m_as("ohm"), ym.m_as("S"), k * self.tap)

    @property
    def max_power(self) -> Q_[float] | None:
        """The maximum power loading of the transformer (in VA)."""
        # Do not add a setter. The user must know that if they change the max_power, it changes
        # for all transformers that share the parameters. It is better to set it on the parameters.
        return self.parameters.max_power

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = super()._to_dict(include_results=include_results)
        res["tap"] = self.tap
        res["params_id"] = self.parameters.id
        return res

    def _compute_phases_three(
        self,
        id: Id,
        bus1: Bus,
        bus2: Bus,
        parameters: TransformerParameters,
        phases1: str | None,
        phases2: str | None,
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
        self, id: Id, bus1: Bus, bus2: Bus, phases1: str | None, phases2: str | None
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

    def _compute_phases_center(
        self, id: Id, bus1: Bus, bus2: Bus, phases1: str | None, phases2: str | None
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
            if phases2 not in self._allowed_phases_center_secondary:
                msg = f"Phases (2) of transformer {id!r} cannot be deduced from the buses, they need to be specified."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            self._check_phases(id, allowed_phases=self._allowed_phases_center_secondary, phases2=phases2)
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

    @property
    def res_violated(self) -> bool | None:
        """Whether the transformer power exceeds the maximum power (loading > 100%).

        Returns ``None`` if the maximum power is not set.
        """
        s_max = self.parameters._max_power
        if s_max is None:
            return None
        powers1, powers2 = self._res_powers_getter(warning=True)
        # True if either the primary or secondary is overloaded
        return float(max(abs(sum(powers1)), abs(sum(powers2)))) > s_max
