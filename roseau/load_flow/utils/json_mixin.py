from abc import ABCMeta, abstractmethod
from typing import Any


class JsonMixin(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def from_dict(*args):
        """Create an element from a dictionary."""
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Return the element information as a dictionary format."""
        raise NotImplementedError
