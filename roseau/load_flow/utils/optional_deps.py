import logging
from typing import TYPE_CHECKING, Any

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

if TYPE_CHECKING:
    import networkx as networkx
    from matplotlib import pyplot as pyplot

logger = logging.getLogger(__name__)

__all__ = ["pyplot", "networkx"]


def __getattr__(name: str) -> Any:
    if name == "pyplot":
        try:
            import matplotlib.pyplot
        except ImportError as e:
            msg = (
                'matplotlib is required for plotting. Install it with the "plot" extra using '
                '`pip install -U "roseau-load-flow[plot]"`'
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.IMPORT_ERROR) from e
        return matplotlib.pyplot
    elif name == "networkx":
        try:
            import networkx
        except ImportError as e:
            msg = (
                'networkx is not installed. Install it with the "graph" extra using '
                '`pip install -U "roseau-load-flow[graph]"`'
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.IMPORT_ERROR) from e
        return networkx
    else:
        raise AttributeError(f"module {__name__} has no attribute {name!r}")
