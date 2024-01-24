from typing import Literal

from roseau.load_flow_engine.cy_engine import cy_set_logging_config


def set_logging_config(verbosity: Literal["trace", "debug", "info", "warning", "error", "critical"]) -> None:
    """Configure the logging level of the solver.

    Args:
        verbosity:
            A valid verbosity level to set for the solver.
            Can be one of: `{"trace", "debug", "info", "warning", "error", "critical"}`
    """
    assert verbosity in {"trace", "debug", "info", "warning", "error", "critical"}
    # Define the logger at C++ level
    cy_set_logging_config(verbosity)
