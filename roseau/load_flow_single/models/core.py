import logging
from typing import TYPE_CHECKING, Final

from roseau.load_flow.utils.mixins import AbstractElement
from roseau.load_flow.utils.mixins import _CyE_co as _CyE_co  # Reexported for easier use

if TYPE_CHECKING:
    from roseau.load_flow_single.network import ElectricalNetwork  # noqa: F401

logger = logging.getLogger(__name__)


class Element(AbstractElement["ElectricalNetwork", _CyE_co]):
    is_multi_phase: Final = False
    _connected_elements: list["Element"]
