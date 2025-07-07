import logging
import math
import warnings
from abc import abstractmethod
from typing import Generic, Self

from shapely.geometry.base import BaseGeometry
from typing_extensions import TypeVar

from roseau.load_flow import SQRT3
from roseau.load_flow.typing import Id, JsonDict, Side
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_engine.cy_engine import CyBranch
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.connectables import AbstractConnectable
from roseau.load_flow_single.models.core import Element
from roseau.load_flow_single.models.line_parameters import LineParameters
from roseau.load_flow_single.models.transformer_parameters import TransformerParameters

logger = logging.getLogger(__name__)

_Parameters = LineParameters | TransformerParameters
_CyB_co = TypeVar("_CyB_co", bound=CyBranch, default=CyBranch, covariant=True)
_Side_co = TypeVar("_Side_co", bound="AbstractBranchSide", default="AbstractBranchSide", covariant=True)


class AbstractBranchSide(AbstractConnectable[_CyB_co]):
    """Accessor class to a branch side."""

    def __init__(self, *, branch: "AbstractBranch[AbstractBranchSide, _CyB_co]", side: Side, bus: Bus) -> None:
        """AbstractBranchSide constructor.

        Args:
            branch:
                The branch element.

            side:
                The side of the branch to access. It can be ``"HV"`` or ``"LV"`` for transformers or
                ``1`` or ``2`` for lines and switches.

            bus:
                The bus to connect the side to.
        """
        self._branch = branch
        super().__init__(id=branch.id, n=branch._n, bus=bus, side=side)
        if branch._cy_initialized:
            self._cy_element = branch._cy_element

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: branch={self._branch.id!r}, side={self._side_value}>"

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
    def __init__(self, id: Id, bus1: Bus, bus2: Bus, n: int, *, geometry: BaseGeometry | None = None) -> None:
        """AbstractBranch constructor.

        Args:
            id:
                A unique ID of the branch in the network branches.

            bus1:
                The bus to connect the first extremity of the branch to.

            bus2:
                The bus to connect the second extremity of the branch to.

            geometry:
                The geometry of the branch.
        """
        super().__init__(id)
        self._n = n
        self.geometry = self._check_geometry(geometry)
        self._side1: _Side_co
        self._side2: _Side_co

    def __repr__(self) -> str:
        s1, s2 = self._side1._side_suffix, self._side2._side_suffix
        return f"<{type(self).__name__}: id={self.id!r}, bus{s1}={self.bus1.id!r}, bus{s2}={self.bus2.id!r}>"

    @property
    def side1(self) -> _Side_co:
        """The first side of the branch."""
        return self._side1

    @property
    def side2(self) -> _Side_co:
        """The second side of the branch."""
        return self._side2

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
        """Connect the Cython elements of the buses and the branch."""
        self._side1._cy_element = self._cy_element
        self._side2._cy_element = self._cy_element
        self._side1._cy_connect()
        self._side2._cy_connect()

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

    def _update_network_parameters(self, old_parameters: _Parameters | None, new_parameters: _Parameters) -> None:
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
            self._side1._res_current = self._cy_element.get_port_current(0)
            self._side1._res_voltage = self._cy_element.get_port_potential(0) * SQRT3
            self._side2._res_current = self._cy_element.get_port_current(self._n)
            self._side2._res_voltage = self._cy_element.get_port_potential(self._n) * SQRT3

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_currents(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch currents (A)."""
        return (
            self._side1._res_current_getter(warning=True),
            self._side2._res_current_getter(warning=False),  # warn only once
        )  # type: ignore

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_voltages(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch voltages (V)."""
        return (
            self._side1._res_voltage_getter(warning=True),
            self._side2._res_voltage_getter(warning=False),  # warn only once
        )  # type: ignore

    @property
    @ureg_wraps(("VA", "VA"), (None,))
    def res_powers(self) -> tuple[Q_[complex], Q_[complex]]:
        """The load flow result of the branch powers (VA)."""
        return (
            self._side1._res_power_getter(warning=True),
            self._side2._res_power_getter(warning=False),  # warn only once
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
        if self.geometry is not None:
            data["geometry"] = self.geometry.__geo_interface__
        if include_results:
            data["results"] = {}
            for k1, k2 in zip(results1, results2, strict=True):
                data["results"][k1] = results1[k1]
                data["results"][k2] = results2[k2]
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results1 = self._side1._results_to_dict(warning, full=full)
        results2 = self._side2._results_to_dict(warning=False, full=full)  # warn only once
        results: JsonDict = {}
        for k1, k2 in zip(results1, results2, strict=True):
            results[k1] = results1[k1]
            results[k2] = results2[k2]
        return results
