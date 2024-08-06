import logging
import warnings
from typing import Final

from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.models.grounds import Ground
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyDeltaPotentialRef, CyPotentialRef

logger = logging.getLogger(__name__)


class PotentialRef(Element):
    """A potential reference.

    This element sets the reference for the potentials in a network. Only one potential reference
    per galvanically isolated section of the network can be set.

    When passed a ground, the potential of the ground is set to 0V. When passed a bus, if the bus
    has a neutral, the potential of the neutral is set to 0V. If the bus does not have a neutral,
    the sum of the potentials of the bus phases is set to 0V. If the phases are specified for a
    bus, the sum of the potentials of the specified phases is set to 0V.
    """

    allowed_phases: Final = frozenset({"a", "b", "c", "n"} | Bus.allowed_phases)

    def __init__(self, id: Id, element: Bus | Ground, *, phases: str | None = None, **deprecated_kw) -> None:
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
        if "phase" in deprecated_kw and phases is None:
            warnings.warn("The 'phase' argument is deprecated, use 'phases' instead.", DeprecationWarning, stacklevel=2)
            phases = deprecated_kw.pop("phase")
        if deprecated_kw:
            raise TypeError(
                f"PotentialRef.__init__() got an unexpected keyword argument: '{next(iter(deprecated_kw))}'"
            )
        super().__init__(id)
        original_phases = phases
        if isinstance(element, Bus):
            if phases is None:
                phases = "n" if "n" in element.phases else element.phases
            else:
                self._check_phases(id, phases=phases)
                # Also check they are in the bus phases
                phases_not_in_bus = set(phases) - set(element.phases)
                if phases_not_in_bus:
                    msg = (
                        f"Phases {sorted(phases_not_in_bus)} of potential reference {id!r} are not in bus "
                        f"{element.id!r} phases {element.phases!r}"
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        elif isinstance(element, Ground):
            if phases is not None:
                msg = f"Potential reference {self.id!r} connected to the ground cannot have a phase."
                logger.error(msg)
                raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
        else:
            msg = f"Potential reference {self.id!r} is connected to {element!r} which is not a ground nor a bus."
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT)
        self._phases = phases
        self._original_phases = original_phases  # kept for serialization
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
                element._cy_element.connect(self._cy_element, [(i, i) for i in indices])
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

    def _res_current_getter(self, warning: bool) -> complex:
        if self._fetch_results:
            self._res_current = self._cy_element.get_current()
        return self._res_getter(self._res_current, warning)

    @property
    @ureg_wraps("A", (None,))
    def res_current(self) -> Q_[complex]:
        """The sum of the currents (A) of the connection associated to the potential reference.

        This sum should be equal to 0 after the load flow.
        """
        return self._res_current_getter(warning=True)

    #
    # Jso Mixin interface
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
