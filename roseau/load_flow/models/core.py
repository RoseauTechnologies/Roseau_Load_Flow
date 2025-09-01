import logging
from typing import TYPE_CHECKING, ClassVar, Final

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import abstractattrs
from roseau.load_flow.utils.mixins import AbstractElement
from roseau.load_flow.utils.mixins import _CyE_co as _CyE_co  # Reexported for easier use

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork  # noqa: F401

logger = logging.getLogger(__name__)


@abstractattrs("allowed_phases")
class Element(AbstractElement["ElectricalNetwork", _CyE_co]):
    is_multi_phase: Final = True

    allowed_phases: ClassVar[frozenset[str]]  # frozenset for immutability and uniqueness
    """The allowed phases for this element type.

    It is a frozen set of strings like ``"abc"`` or ``"an"`` etc. The order of the phases is
    important. For a full list of supported phases, use ``print(<Element class>.allowed_phases)``.
    """

    _connected_elements: list["Element"]

    @classmethod
    def _check_phases(cls, id: Id, allowed_phases: frozenset[str] | None = None, **kwargs: str) -> None:
        if allowed_phases is None:
            allowed_phases = cls.allowed_phases
        name, phases = kwargs.popitem()  # phases, phases1, phases2, phases_hv, phases_lv, etc.
        if phases not in allowed_phases:
            msg = (
                f"{cls.__name__} of id {id!r} got invalid {name} {phases!r}, allowed values are: "
                f"{sorted(allowed_phases)}"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
