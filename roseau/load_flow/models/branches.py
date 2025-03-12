import logging
import warnings
from functools import cached_property

import numpy as np
from shapely.geometry.base import BaseGeometry
from typing_extensions import Self, TypeVar

from roseau.load_flow.converters import _calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import find_stack_level, one_or_more_repr
from roseau.load_flow_engine.cy_engine import CyBranch

logger = logging.getLogger(__name__)

_CyB_co = TypeVar("_CyB_co", bound=CyBranch, default=CyBranch, covariant=True)


class AbstractBranch(Element[_CyB_co]):
    """Base class of all the branches (lines, switches and transformers) of the network.

    See Also:
        :doc:`Line models documentation </models/Line/index>`,
        :doc:`Transformer models documentation </models/Transformer/index>` and
        :doc:`Switch model documentation </models/Switch>`
    """

    def __init__(
        self, id: Id, bus1: Bus, bus2: Bus, *, phases1: str, phases2: str, geometry: BaseGeometry | None = None
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
        if type(self) is AbstractBranch:
            raise TypeError("Can't instantiate abstract class AbstractBranch")
        super().__init__(id)
        self._check_phases(id=id, phases1=phases1)
        self._check_phases(id=id, phases2=phases2)
        self._n1 = len(phases1)
        self._n2 = len(phases2)
        self._phases1 = phases1
        self._phases2 = phases2
        self._bus1 = bus1
        self._bus2 = bus2
        self.geometry = geometry
        self._connect(bus1, bus2)
        self._res_currents: tuple[ComplexArray, ComplexArray] | None = None
        self._res_potentials: tuple[ComplexArray, ComplexArray] | None = None
        self._sides_suffixes = ("_hv", "_lv") if self.element_type == "transformer" else ("1", "2")

    def __repr__(self) -> str:
        s1, s2 = self._sides_suffixes
        return (
            f"<{type(self).__name__}: id={self.id!r}, bus{s1}={self.bus1.id!r}, bus{s2}={self.bus2.id!r}, "
            f"phases{s1}={self.phases1!r}, phases{s2}={self.phases2!r}>"
        )

    @property
    def phases1(self) -> str:
        """The phases of the branch at the first bus."""
        return self._phases1

    @property
    def phases2(self) -> str:
        """The phases of the branch at the second bus."""
        return self._phases2

    @cached_property
    def _all_phases(self) -> str:
        return "".join(sorted(set(self._phases1) | set(self._phases2)))

    @property
    def bus1(self) -> Bus:
        """The first bus of the branch."""
        return self._bus1

    @property
    def bus2(self) -> Bus:
        """The second bus of the branch."""
        return self._bus2

    def _cy_connect(self) -> None:
        """Connect the Cython elements of the buses and the branch"""
        connections = []
        for i, phase in enumerate(self.phases1):
            if phase in self.bus1.phases:
                j = self.bus1.phases.index(phase)
                connections.append((i, j))
        self._cy_element.connect(self.bus1._cy_element, connections, True)

        connections = []
        for i, phase in enumerate(self.phases2):
            if phase in self.bus2.phases:
                j = self.bus2.phases.index(phase)
                connections.append((i, j))
        self._cy_element.connect(self.bus2._cy_element, connections, False)

    def _check_phases_common(self, id: Id, bus1: Bus, bus2: Bus, phases: str | None) -> str:
        """Check the common phases between the buses and the branch (for lines and switches)."""
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
            and not np.isclose(self.bus1._nominal_voltage, self.bus2._nominal_voltage)
        ):
            warnings.warn(
                (
                    f"{self.element_type.capitalize()} {self.id!r} connects buses with different "
                    f"nominal voltages: {self.bus1._nominal_voltage} V and {self.bus2._nominal_voltage} V."
                ),
                stacklevel=find_stack_level(),
            )

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_currents = self._cy_element.get_currents(self._n1, self._n2)
            self._res_potentials = self._cy_element.get_potentials(self._n1, self._n2)

    def _res_currents_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        self._refresh_results()
        return self._res_getter(value=self._res_currents, warning=warning)

    def _res_potentials_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        self._refresh_results()
        return self._res_getter(value=self._res_potentials, warning=warning)

    def _res_voltages_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        potentials1, potentials2 = self._res_potentials_getter(warning)
        return (
            _calculate_voltages(potentials=potentials1, phases=self.phases1),
            _calculate_voltages(potentials=potentials2, phases=self.phases2),
        )

    def _res_powers_getter(self, warning: bool) -> tuple[ComplexArray, ComplexArray]:
        currents1, currents2 = self._res_currents_getter(warning)
        potentials1, potentials2 = self._res_potentials_getter(warning=False)  # warn only once
        powers1 = potentials1 * currents1.conjugate()
        powers2 = potentials2 * currents2.conjugate()
        return powers1, powers2

    @property
    @ureg_wraps(("A", "A"), (None,))
    def res_currents(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch currents (A)."""
        return self._res_currents_getter(warning=True)

    @property
    @ureg_wraps(("VA", "VA"), (None,))
    def res_powers(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch powers (VA)."""
        return self._res_powers_getter(warning=True)

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_potentials(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch potentials (V)."""
        return self._res_potentials_getter(warning=True)

    @property
    @ureg_wraps(("V", "V"), (None,))
    def res_voltages(self) -> tuple[Q_[ComplexArray], Q_[ComplexArray]]:
        """The load flow result of the branch voltages (V)."""
        return self._res_voltages_getter(warning=True)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        data["geometry"] = cls._parse_geometry(data.pop("geometry", None))
        results = data.pop("results", None)
        self = cls(**data)
        if include_results and results:
            s1, s2 = self._sides_suffixes
            currents1 = np.array([complex(*i) for i in results[f"currents{s1}"]], dtype=np.complex128)
            currents2 = np.array([complex(*i) for i in results[f"currents{s2}"]], dtype=np.complex128)
            potentials1 = np.array([complex(*v) for v in results[f"potentials{s1}"]], dtype=np.complex128)
            potentials2 = np.array([complex(*v) for v in results[f"potentials{s2}"]], dtype=np.complex128)
            self._res_currents = (currents1, currents2)
            self._res_potentials = (potentials1, potentials2)
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        s1, s2 = self._sides_suffixes
        data: JsonDict = {"id": self.id}
        if self.element_type == "transformer":
            data[f"phases{s1}"] = self.phases1
            data[f"phases{s2}"] = self.phases2
        else:
            data["phases"] = self.phases1
        data[f"bus{s1}"] = self.bus1.id
        data[f"bus{s2}"] = self.bus2.id
        if self.geometry is not None:
            data["geometry"] = self.geometry.__geo_interface__
        if include_results:
            currents1, currents2 = self._res_currents_getter(warning=True)
            potentials1, potentials2 = self._res_potentials_getter(warning=False)  # warn only once
            data["results"] = {
                f"currents{s1}": [[i.real, i.imag] for i in currents1],
                f"currents{s2}": [[i.real, i.imag] for i in currents2],
                f"potentials{s1}": [[i.real, i.imag] for i in potentials1],
                f"potentials{s2}": [[i.real, i.imag] for i in potentials2],
            }
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        currents1, currents2 = self._res_currents_getter(warning)
        potentials1, potentials2 = self._res_potentials_getter(warning=False)  # warn only once
        s1, s2 = self._sides_suffixes
        results: JsonDict = {"id": self.id}
        if self.element_type == "transformer":
            results[f"phases{s1}"] = self.phases1
            results[f"phases{s2}"] = self.phases2
        else:
            results["phases"] = self.phases1
        results[f"currents{s1}"] = [[i.real, i.imag] for i in currents1]
        results[f"currents{s2}"] = [[i.real, i.imag] for i in currents2]
        results[f"potentials{s1}"] = [[v.real, v.imag] for v in potentials1]
        results[f"potentials{s2}"] = [[v.real, v.imag] for v in potentials2]
        if full:
            powers1 = potentials1 * currents1.conjugate()
            powers2 = potentials2 * currents2.conjugate()
            voltages1 = _calculate_voltages(potentials=potentials1, phases=self.phases1)
            voltages2 = _calculate_voltages(potentials=potentials2, phases=self.phases2)
            results[f"powers{s1}"] = [[s.real, s.imag] for s in powers1]
            results[f"powers{s2}"] = [[s.real, s.imag] for s in powers2]
            results[f"voltages{s1}"] = [[v.real, v.imag] for v in voltages1]
            results[f"voltages{s2}"] = [[v.real, v.imag] for v in voltages2]
        return results
