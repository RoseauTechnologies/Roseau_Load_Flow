import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

from roseau.load_flow_engine.cy_engine import cy_set_logging_config

# Human logging levels
log_levels = {
    "trace": logging.DEBUG,  # No deeper log value for Python
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

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


def set_logging_config(verbosity: str):
    """A function to define the configuration of the logging module

    Args:
        verbosity:
            A valid verbosity level as defined in `log_levels`
    """
    level = log_levels[verbosity]
    rich_handler_kwargs = {
        "show_time": True,
        "show_level": True,
        "rich_tracebacks": True,
        "tracebacks_show_locals": True,
        "locals_max_string": None,
    }
    if verbosity in ("debug", "trace"):
        rich_handler_kwargs["show_path"] = True
        log_time_format = "%x %X"
    else:
        rich_handler_kwargs["show_path"] = False
        log_time_format = "%x %X"

    # Rich traceback color formatter
    error_console = Console(file=sys.stderr, log_time_format=log_time_format)
    install(console=error_console, width=None)

    # A first handler on the main console to have output synchronized with progress bar (which are also printed on the
    # main console)
    handlers = [RichHandler(level=level, console=console, **rich_handler_kwargs)]

    # Define the basic config
    logging.basicConfig(
        level=log_levels[verbosity], handlers=handlers, datefmt=log_time_format, format="{message}", style="{"
    )

    # Capture the warnings
    logging.captureWarnings(True)

    # Define the logger at C++ level
    cy_set_logging_config(verbosity)
