import logging
from abc import ABC
from typing import ClassVar, TypeVar

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import JsonMixin
from roseau.load_flow.utils.mixins import NetworkElement

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class Element(ABC, NetworkElement, JsonMixin):
    """An abstract class of an element in an Electrical network."""

    allowed_phases: ClassVar[frozenset[str]]  # frozenset for immutability and uniqueness
    """The allowed phases for this element type.

    It is a frozen set of strings like ``"abc"`` or ``"an"`` etc. The order of the phases is
    important. For a full list of supported phases, use ``print(<Element class>.allowed_phases)``.
    """

    def __init__(self, id: Id) -> None:
        """Element constructor.

        Args:
            id:
                A unique ID of the element in the network. Two elements of the same type cannot
                have the same ID.
        """
        if type(self) is Element:
            raise TypeError("Can't instantiate abstract class Element")
        super().__init__(id)

    @classmethod
    def _check_phases(cls, id: Id, allowed_phases: frozenset[str] | None = None, **kwargs: str) -> None:
        if allowed_phases is None:
            allowed_phases = cls.allowed_phases
        name, phases = kwargs.popitem()  # phases, phases1 or phases2
        if phases not in allowed_phases:
            msg = (
                f"{cls.__name__} of id {id!r} got invalid {name} {phases!r}, allowed values are: "
                f"{sorted(allowed_phases)}"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg, RoseauLoadFlowExceptionCode.BAD_PHASE)
