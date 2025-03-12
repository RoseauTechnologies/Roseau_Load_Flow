import logging
from typing import Final

from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.grounds import Ground
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import deprecate_renamed_parameter, one_or_more_repr
from roseau.load_flow_engine.cy_engine import CyDeltaPotentialRef, CyPotentialRef

logger = logging.getLogger(__name__)


class PotentialRef(Element[CyPotentialRef | CyDeltaPotentialRef]):
    """A potential reference.

    This element sets the reference for the potentials in a network. Only one potential reference
    per galvanically isolated section of the network can be set.

    When passed a ground, the potential of the ground is set to 0V. When passed a bus, if the bus
    has a neutral, the potential of the neutral is set to 0V. If the bus does not have a neutral,
    the sum of the potentials of the bus phases is set to 0V. If the phases are specified for a
    bus, the sum of the potentials of the specified phases is set to 0V.
    """

    element_type: Final = "potential reference"
    allowed_phases: Final = frozenset({"a", "b", "c", "n"} | Bus.allowed_phases)

    @deprecate_renamed_parameter(old_name="phase", new_name="phases", version="0.10.0", category=DeprecationWarning)
    def __init__(self, id: Id, element: Bus | Ground, *, phases: str | None = None) -> None:
        """PotentialRef constructor.

        Args:
            id:
                A unique ID of the potential reference in the network references.

            element:
                The bus or ground element to set as a potential reference.

            phases:
                The phases of the bus to set as a potential reference. Cannot be used with a ground.
                For the most part, you do not need to set the bus phases manually.

                If a single phase is passed, the potential of that phase will be set as a reference
                (0V fixed at that phase). If multiple phases are passed, the potential reference is
                determined by setting the sum of the bus's potentials at these phases to zero.

                If not set, the default is to set the neutral phase as the reference for buses with
                a neutral, otherwise, the sum of the potentials of the bus phases is set to zero.
        """
        super().__init__(id)
        self._original_phases = phases  # kept for serialization
        if isinstance(element, Bus):
            if phases is None:
                phases = "n" if "n" in element.phases else element.phases
            else:
                self._check_phases(id, phases=phases)
                # Also check they are in the bus phases
                phases_not_in_bus = set(phases) - set(element.phases)
                if phases_not_in_bus:
                    ph, be = one_or_more_repr(sorted(phases_not_in_bus), "Phase")
                    msg = (
                        f"{ph} of potential reference {id!r} {be} not in phases {element.phases!r} "
                        f"of bus {element.id!r}."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        elif isinstance(element, Ground):
            if phases is not None:
                msg = f"Potential reference {id!r} connected to a ground cannot have phases."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            msg = f"Potential reference {id!r} cannot be connected to a {element.element_type}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        self._phases = phases
        self.element = element
        self._connect(element)
        self._res_current: complex | None = None
        if isinstance(element, Bus):
            assert phases is not None, "Phases should be set for a bus"
            n = len(phases)
            if n == 1:
                self._cy_element = CyPotentialRef()
                p = element.phases.index(phases)
                element._cy_element.connect(self._cy_element, [(p, 0)])
            else:
                self._cy_element = CyDeltaPotentialRef(n)
                indices = (element.phases.index(p) for p in phases)
                element._cy_element.connect(self._cy_element, [(p, i) for i, p in enumerate(indices)])
        else:
            self._cy_element = CyPotentialRef()
            element._cy_element.connect(self._cy_element, [(0, 0)])

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, element={self.element!r}, phases={self.phases!r})"

    @property
    def phases(self) -> str | None:
        """The phases of the bus set as a potential reference, or None if used with a ground.

        The sum of the potentials of the specified phases is set to 0V.
        """
        return self._phases

    #
    # Results
    #
    def _refresh_results(self) -> None:
        if self._fetch_results:
            self._res_current = self._cy_element.get_current()

    def _res_current_getter(self, warning: bool) -> complex:
        self._refresh_results()
        return self._res_getter(self._res_current, warning)

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The sum of the currents (A) of the connection associated to the potential reference.

        This sum should be equal to 0 after the load flow.
        """
        return self._res_current_getter(warning=True)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        self = cls(id=data["id"], element=data["element"], phases=data.get("phases"))
        if include_results and "results" in data:
            self._res_current = complex(*data["results"]["current"])
            self._fetch_results = False
            self._no_results = False
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        res: JsonDict = {"id": self.id}
        e = self.element
        if isinstance(e, Bus):
            res["bus"] = e.id
            res["phases"] = self._original_phases
        elif isinstance(e, Ground):
            res["ground"] = e.id
        else:
            raise AssertionError(f"Unexpected element type {type(e).__name__}")
        if include_results:
            i = self._res_current_getter(warning=True)
            res["results"] = {"current": [i.real, i.imag]}
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        i = self._res_current_getter(warning)
        return {"id": self.id, "current": [i.real, i.imag]}
