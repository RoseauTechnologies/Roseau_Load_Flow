import logging
from abc import ABCMeta, abstractmethod
from typing import Any

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict, Self

logger = logging.getLogger(__name__)


class Identifiable(metaclass=ABCMeta):
    """An identifiable object."""

    def __init__(self, id: Id) -> None:
        if not isinstance(id, (int, str)):
            msg = f"{type(self).__name__} expected id to be int or str, got {type(id)}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_ID_TYPE)
        self.id = id


class JsonMixin(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def from_dict(cls, data: JsonDict, *args: Any) -> Self:
        """Create an element from a dictionary."""
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> JsonDict:
        """Return the element information as a dictionary format."""
        raise NotImplementedError
