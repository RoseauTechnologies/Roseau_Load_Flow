import logging
from abc import ABC
from functools import cached_property
from typing import Final

import numpy as np

from roseau.load_flow.converters import _PHASE_SIZES, _calculate_voltages, calculate_voltage_phases
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.core import Element, _CyE_co
from roseau.load_flow.sym import phasor_to_sym
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps

logger = logging.getLogger(__name__)


class AbstractTerminal(Element[_CyE_co], ABC):
    """A base class for all the terminals (buses, load, sources, etc.) of the network."""

    allowed_phases: Final = frozenset({"ab", "bc", "ca", "an", "bn", "cn", "abn", "bcn", "can", "abc", "abcn"})
    """The allowed phases for a terminal element are:

    - P-P-P or P-P-P-N: ``"abc"``, ``"abcn"``
    - P-P or P-P-N: ``"ab"``, ``"bc"``, ``"ca"``, ``"abn"``, ``"bcn"``, ``"can"``
    - P-N: ``"an"``, ``"bn"``, ``"cn"``
    """

    def __init__(self, id: Id, *, phases: str) -> None:
        """AbstractTerminal constructor.

        Args:
            id:
                A unique ID of the terminal in its dictionary of the network.

            phases:
                The phases of the terminal. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`!allowed_phases`.
        """
        if type(self) is AbstractTerminal:
            raise TypeError("Can't instantiate abstract class AbstractTerminal")

        super().__init__(id)
        self._check_phases(id, phases=phases)
        self._phases = phases
        self._n = len(self._phases)
        self._size = _PHASE_SIZES[phases]
        self._res_potentials: ComplexArray | None = None

    @property
    def phases(self) -> str:
        """The phases of the element."""
        return self._phases

    @cached_property
    def voltage_phases(self) -> list[str]:
        """The phases of the voltages of the element."""
        return calculate_voltage_phases(self._phases)

    @cached_property
    def voltage_phases_pp(self) -> list[str]:
        """The phases of the phase-to-phase voltages of the element."""
        phases = self._phases.removesuffix("n")
        if len(phases) == 1:
            msg = f"Phase-to-phase voltages cannot exist for single-phase {self._element_info}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        return calculate_voltage_phases(phases)

    @cached_property
    def voltage_phases_pn(self) -> list[str]:
        """The phases of the phase-to-neutral voltages of the element."""
        if "n" not in self._phases:
            msg = f"Phase-to-neutral voltages cannot exist for {self._element_info} without a neutral."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        return calculate_voltage_phases(self._phases)

    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_potentials = self._cy_element.get_potentials(self._n)

    def _res_potentials_getter(self, warning: bool) -> ComplexArray:
        self._refresh_results()
        return self._res_getter(value=self._res_potentials, warning=warning)

    def _res_voltages_getter(self, warning: bool) -> ComplexArray:
        potentials = self._res_potentials_getter(warning=warning)
        return _calculate_voltages(potentials, self.phases)

    def _res_voltages_pp_getter(self, warning: bool) -> ComplexArray:
        _ = self.voltage_phases_pp  # raises if not enough phases
        phases = self.phases.removesuffix("n")
        potentials = self._res_potentials_getter(warning=warning)
        return _calculate_voltages(potentials[: len(phases)], phases)

    def _res_voltages_pn_getter(self, warning: bool) -> ComplexArray:
        _ = self.voltage_phases_pn  # raises if no neutral
        potentials = self._res_potentials_getter(warning=warning)
        return _calculate_voltages(potentials, self.phases)

    @property
    @ureg_wraps("V", (None,))
    def res_potentials(self) -> Q_[ComplexArray]:
        """The load flow result of the element potentials (V)."""
        return self._res_potentials_getter(warning=True)

    @property
    @ureg_wraps("V", (None,))
    def res_voltages(self) -> Q_[ComplexArray]:
        """The load flow result of the element voltages (V).

        If the element has a neutral, the voltages are phase-to-neutral voltages for existing phases
        in the order ``[Van, Vbn, Vcn]``. If the element does not have a neutral, the voltages are
        phase-to-phase for existing phases in the order ``[Vab, Vbc, Vca]``.

        To always get phase-to-phase voltages, use the property :attr:`.res_voltages_pp`.
        To always get phase-to-neutral voltages, use the property :attr:`.res_voltages_pn`.
        """
        return self._res_voltages_getter(warning=True)

    @property
    @ureg_wraps("V", (None,))
    def res_voltages_pp(self) -> Q_[ComplexArray]:
        """The load flow result of the element's phase-to-phase voltages (V).

        Raises an error if the element has only one phase.
        """
        return self._res_voltages_pp_getter(warning=True)

    @property
    @ureg_wraps("V", (None,))
    def res_voltages_pn(self) -> Q_[ComplexArray]:
        """The load flow result of the element's phase-to-neutral voltages (V).

        Raises an error if the element does not have a neutral.
        """
        return self._res_voltages_pn_getter(warning=True)

    @ureg_wraps("percent", (None,))
    def res_voltage_unbalance(self) -> Q_[float]:
        """Calculate the voltage unbalance factor on this element according to the IEC definition.

        Voltage Unbalance Factor:

        :math:`VUF = \\dfrac{|V_{\\mathrm{n}}|}{|V_{\\mathrm{p}}|} \\times 100 \\, (\\%)`

        Where :math:`V_{\\mathrm{n}}` is the negative-sequence (inverse) voltage
        and :math:`V_{\\mathrm{p}}` is the positive-sequence (direct) voltage.
        """
        if self.phases not in {"abc", "abcn"}:
            msg = (
                f"Voltage unbalance is only available for three-phase elements, {self._element_info} "
                f"has phases {self.phases!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        # We use the potentials here which is equivalent to using the "line to neutral" voltages as
        # defined by the standard. The standard also has this note:
        # NOTE 1 Phase-to-phase voltages may also be used instead of line to neutral voltages.
        # Indeed |Vn_pp| / |Vp_pp_| = |Vn (1-α²)| / |Vp(1-α)| = |Vn| / |Vp|
        potentials = self._res_potentials_getter(warning=True)
        _, vp, vn = phasor_to_sym(potentials[:3])  # (0, +, -)
        return abs(vn) / abs(vp) * 100

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            self._res_potentials = np.array([complex(*v) for v in data["results"]["potentials"]], dtype=np.complex128)
            self._fetch_results = False
            self._no_results = False

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = {"id": self.id, "phases": self.phases}
        if include_results:
            potentials = self._res_potentials_getter(warning=True)
            data["results"] = {"potentials": [[v.real, v.imag] for v in potentials]}
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        potentials = self._res_potentials_getter(warning)
        results = {
            "id": self.id,
            "phases": self.phases,
            "potentials": [[v.real, v.imag] for v in potentials],
        }
        if full:
            voltages = _calculate_voltages(potentials, self.phases)
            results["voltages"] = [[v.real, v.imag] for v in voltages]
        return results
