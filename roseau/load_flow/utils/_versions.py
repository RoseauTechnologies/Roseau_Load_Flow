import os
import platform
import sys
from importlib.metadata import version

from roseau.load_flow.typing import JsonDict


def _get_sys_info() -> JsonDict:
    """Get system information."""
    return {
        "python": ".".join(map(str, sys.version_info)),
        "os": sys.platform,
        "os_name": os.name,
        "machine": platform.machine(),
    }


def _get_dependency_info() -> JsonDict:
    """Get versions of dependencies."""
    return {
        dist: version(dist)
        for dist in (
            "pandas",
            "numpy",
            "geopandas",
            "shapely",
            "regex",
            "pint",
            "platformdirs",
            "certifi",
            "roseau-load-flow",
            "roseau-load-flow-engine",
        )
    }


def show_versions() -> None:
    """Print system and python environment information."""
    sys_info = _get_sys_info()
    deps = _get_dependency_info()

    print()
    print("System Information")
    print("------------------")
    for k, v in sys_info.items():
        print(f"{k:<25} {v}")

    print()
    print("Installed Dependencies")
    print("----------------------")
    for k, v in deps.items():
        print(f"{k:<25} {v}")
