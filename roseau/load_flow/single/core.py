import logging
from abc import ABC
from typing import TypeVar

from roseau.load_flow.typing import Id
from roseau.load_flow.utils import JsonMixin
from roseau.load_flow.utils.mixins import NetworkElement

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class Element(ABC, NetworkElement, JsonMixin):
    """An abstract class of a single element in an Electrical network."""

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
