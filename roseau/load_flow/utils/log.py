from typing import Literal

from rich.console import Console

from roseau.load_flow_engine.cy_engine import cy_set_logging_config

# Rich console
console = Console()

palette = [
    "#4c72b0",
    "#dd8452",
    "#55a868",
    "#c44e52",
    "#8172b3",
    "#937860",
    "#da8bc3",
    "#8c8c8c",
    "#ccb974",
    "#64b5cd",
]
"""Color palette for the catalogue tables.

This is seaborn's default color palette. Generated with:
```python
import seaborn as sns
sns.set_theme()
list(sns.color_palette().as_hex())
```
"""


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
