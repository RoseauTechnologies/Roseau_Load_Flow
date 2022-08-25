import logging
import sys

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

# Human logging levels
log_levels = {
    "trace": logging.DEBUG,  # No deeper log value for Python
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}
CLICKVERBOSITY = click.Choice(list(log_levels.keys()))

# Rich console
console = Console()


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
