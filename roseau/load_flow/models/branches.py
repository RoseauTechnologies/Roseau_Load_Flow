import logging
import math
import warnings
from abc import abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Generic, Self

from shapely.geometry.base import BaseGeometry
from typing_extensions import TypeVar

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.connectables import AbstractConnectable
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import ComplexArray, Id, JsonDict, Side
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level, one_or_more_repr
from roseau.load_flow_engine.cy_engine import CyBranch

if TYPE_CHECKING:
    from roseau.load_flow.models.lines.parameters import LineParameters
    from roseau.load_flow.models.transformers.parameters import TransformerParameters

    _Parameters = LineParameters | TransformerParameters

logger = logging.getLogger(__name__)

_CyB_co = TypeVar("_CyB_co", bound=CyBranch, default=CyBranch, covariant=True)
_Side_co = TypeVar("_Side_co", bound="AbstractBranchSide", default="AbstractBranchSide", covariant=True)


class AbstractBranchSide(AbstractConnectable[_CyB_co]):
    """Accessor class to a branch side."""

    def __init__(
        self,
        *,
        branch: "AbstractBranch[AbstractBranchSide, _CyB_co]",
        side: Side,
        bus: Bus,
        phases: str | None,
        connect_neutral: bool | None,
    ) -> None:
        """AbstractBranchSide constructor.

        Args:
            branch:
                The branch element.

            side:
                The side of the branch to access. It can be ``"HV"`` or ``"LV"`` for transformers or
                ``1`` or ``2`` for lines and switches.

            bus:
                The bus to connect the branch side to.

            phases:
                The phases of the branch side. A string like ``"abc"`` or ``"an"`` etc. The bus
                phases are used by default. The order of the phases is important. For a full list of
                supported phases, see the class attribute :attr:`allowed_phases`. All phases of the
                element must be present in the phases of the connected bus. Multiphase elements are
                allowed to be connected to buses that don't have a neutral if ``connect_neutral`` is
                not set to ``True``.

            connect_neutral:
                Specifies whether the element's neutral should be connected to the bus's neutral or
                left floating. By default, the elements's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the element's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        self._branch = branch
        super().__init__(id=branch.id, bus=bus, phases=phases, connect_neutral=connect_neutral, side=side)
        if branch._cy_initialized:
            self._cy_element = branch._cy_element

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: branch={self._branch.id!r}, side={self._side_value}, phases={self._phases!r}>"

    @classmethod
    def from_dict(cls, data, *, include_results=True) -> Self:
        raise NotImplementedError("Cannot create a branch side from a dict.")

    def _connect(self, *elements) -> None:
        # Connections are done in the branch
        pass

    def _refresh_results(self) -> None:
        # Results are stored in the branch
        return self._branch._refresh_results()


class AbstractBranch(Element[_CyB_co], Generic[_Side_co, _CyB_co]):
    """Base class of all the branches (lines, switches and transformers) of the network.

    See Also:
        :doc:`Line models documentation </models/Line/index>`,
        :doc:`Transformer models documentation </models/Transformer/index>` and
        :doc:`Switch model documentation </models/Switch>`
    """

    @abstractmethod
    def __init__(
        self, id: Id, bus1: Bus, bus2: Bus, *, phases1: str, phases2: str, geometry: BaseGeometry | None
    ) -> None:
        """AbstractBranch constructor.

        Args:
            id:
                A unique ID of the branch in the network branches.

            phases1:
                The phases of the first extremity of the branch.

            phases2:
                The phases of the second extremity of the branch.

            bus1:
                The bus to connect the first extremity of the branch to.

            bus2:
                The bus to connect the second extremity of the branch to.

            geometry:
                The geometry of the branch.
        """
        super().__init__(id)
        self.geometry = geometry
        self._side1: _Side_co
        self._side2: _Side_co

    def __repr__(self) -> str:
        s1, s2 = self._side1._side_suffix, self._side2._side_suffix
        return (
            f"<{type(self).__name__}: id={self.id!r}, bus{s1}={self.bus1.id!r}, bus{s2}={self.bus2.id!r}, "
            f"phases{s1}={self.phases1!r}, phases{s2}={self.phases2!r}>"
        )

    @property
    def side1(self) -> _Side_co:
        """The first side of the branch."""
        return self._side1

    @property
    def side2(self) -> _Side_co:
        """The second side of the branch."""
        return self._side2

    @property
    def phases1(self) -> str:
        """The phases of the branch at the first bus."""
        return self._side1._phases

    @property
    def phases2(self) -> str:
        """The phases of the branch at the second bus."""
        return self._side2._phases

    @cached_property
    def _all_phases(self) -> str:
        return "".join(sorted(set(self.phases1) | set(self.phases2)))

    @property
    def bus1(self) -> Bus:
        """The first bus of the branch."""
        return self._side1._bus

    @property
    def bus2(self) -> Bus:
        """The second bus of the branch."""
        return self._side2._bus

    def _set_self_network(self, value) -> None:
        self._network = value
        self._side1._network = value
        self._side2._network = value

    def _cy_connect(self) -> None:
        """Connect the Cython elements of the buses and the branch"""
        self._side1._cy_element = self._cy_element
        self._side2._cy_element = self._cy_element
        self._side1._cy_connect()
        self._side2._cy_connect()

    def _check_phases_common(self, id: Id, bus1: Bus, bus2: Bus, phases: str | None) -> str:
        """Check the common phases between the buses and the branch (for lines and switches)."""
        self._check_compatible_phase_tech(bus1, id=id)
        self._check_compatible_phase_tech(bus2, id=id)
        buses_phases = set(bus1.phases) & set(bus2.phases)
        if phases is None:
            phases = "".join(sorted(buses_phases)).replace("ac", "ca")
        else:
            # Also check they are in the intersection of buses phases
            self._check_phases(id, phases=phases)
            phases_not_in_buses = set(phases) - buses_phases
            if phases_not_in_buses:
                ph, be = one_or_more_repr(sorted(phases_not_in_buses), "Phase")
                ph_common = "".join(sorted(buses_phases)).replace("ac", "ca")
                msg = (
                    f"{ph} of {self.element_type} {id!r} {be} not in the common phases {ph_common!r} "
                    f"of its buses {bus1.id!r} and {bus2.id!r}."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        return phases

    def _check_same_voltage_level(self) -> None:
        if (
            self.bus1._nominal_voltage is not None
            and self.bus2._nominal_voltage is not None
            and not math.isclose(self.bus1._nominal_voltage, self.bus2._nominal_voltage)
        ):
            warnings.warn(
                (
                    f"{self.element_type.capitalize()} {self.id!r} connects buses with different "
                    f"nominal voltages: {self.bus1._nominal_voltage} V and {self.bus2._nominal_voltage} V."
                ),
                stacklevel=find_stack_level(),
            )

    def _update_network_parameters(self, old_parameters: "_Parameters | None", new_parameters: "_Parameters") -> None:
        if old_parameters is not None and old_parameters is not new_parameters:
            old_parameters._elements.discard(self)
            if not old_parameters._elements and self._network is not None:
                # This was the only element using the old parameters, remove them from the network
                self._network._remove_parameters(self.element_type, old_parameters.id)
        if self not in new_parameters._elements:
            new_parameters._elements.add(self)
            if self._network is not None:
                self._network._add_parameters(self.element_type, new_parameters)

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._side1._res_currents, self._side2._res_currents = self._cy_element.get_side_currents(
                self._side1._n, self._side2._n
            )
            self._side1._res_potentials, self._side2._res_potentials = self._cy_element.get_side_potentials(
                self._side1._n, self._side2._n
            )

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_currents(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch currents (A)."""
        return (
            self._side1._res_currents_getter(warning=True),
            self._side2._res_currents_getter(warning=False),  # warn only once
        )  # type: ignore

    @property
    @ureg_wraps(("VA", "VA"), (None,))
    def res_powers(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch powers (VA)."""
        return (
            self._side1._res_powers_getter(warning=True),
            self._side2._res_powers_getter(warning=False),  # warn only once
        )  # type: ignore

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_potentials(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch potentials (V)."""
        return (
            self._side1._res_potentials_getter(warning=True),
            self._side2._res_potentials_getter(warning=False),  # warn only once
        )  # type: ignore

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_voltages(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch voltages (V)."""
        return (
            self._side1._res_voltages_getter(warning=True),
            self._side2._res_voltages_getter(warning=False),  # warn only once
        )  # type: ignore

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        data["geometry"] = cls._parse_geometry(data.pop("geometry", None))
        results = data.pop("results", None)
        self = cls(**data)
        if include_results and results:
            results_data = {"results": results}
            self._side1._parse_results_from_dict(data=results_data, include_results=include_results)
            self._side2._parse_results_from_dict(data=results_data, include_results=include_results)
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data1 = self._side1._to_dict(include_results=include_results)
        data2 = self._side2._to_dict(include_results=include_results)
        data: JsonDict = {}
        results1 = data1.pop("results", {})
        results2 = data2.pop("results", {})
        for k1, k2 in zip(data1, data2, strict=True):
            data[k1] = data1[k1]
            data[k2] = data2[k2]
            if self.element_type != "transformer":
                if k1 == "phases1" and k2 == "phases2":
                    data["phases"] = data.pop(k1)
                    assert data["phases"] == data.pop(k2)
                elif k1 == "connect_neutral1" and k2 == "connect_neutral2":
                    del data[k1], data[k2]
        if self.geometry is not None:
            data["geometry"] = self.geometry.__geo_interface__
        if include_results:
            data["results"] = {}
            for k1, k2 in zip(results1, results2, strict=True):
                data["results"][k1] = results1[k1]
                data["results"][k2] = results2[k2]
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results1 = self._side1._results_to_dict(warning=warning, full=full)
        results2 = self._side2._results_to_dict(warning=False, full=full)  # warn only once
        results: JsonDict = {}
        for k1, k2 in zip(results1, results2, strict=True):
            results[k1] = results1[k1]
            results[k2] = results2[k2]
            if k1 == f"phases{self._side1._side_suffix}" and self.element_type != "transformer":
                results["phases"] = results.pop(k1)
                assert results["phases"] == results.pop(k2)
        return results
