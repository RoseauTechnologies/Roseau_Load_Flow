import importlib
import inspect
import os
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

import roseau.load_flow
import roseau.load_flow_single
from roseau.load_flow.utils.log import set_logging_config

HERE = Path(__file__).parent.expanduser().absolute()
TEST_ALL_NETWORKS_DATA_FOLDER = HERE / "tests" / "data" / "networks"

TEST_DGS_NETWORK_DIR = HERE.parent / "load_flow" / "tests" / "data" / "dgs"
TEST_DGS_NETWORKS = list(TEST_DGS_NETWORK_DIR.rglob("*.json"))
TEST_DGS_NETWORKS_IDS = [x.stem for x in TEST_DGS_NETWORKS]
TEST_DGS_SPECIAL_NETWORKS_DIR = TEST_DGS_NETWORK_DIR / "special"

THREE_PHASES_TRANSFORMER_TYPES = [
    "Dd0",
    "Dd6",
    "Dyn11",
    "Dyn5",
    "Dzn0",
    "Dzn6",
    "Yd11",
    "Yd5",
    "Yyn0",
    "Yyn6",
    "Yzn11",
    "Yzn5",
]


@pytest.fixture(params=["impedance", "power"], ids=["impedance", "power"])
def network_load_data_name(request) -> str:
    return request.param


@pytest.fixture(params=TEST_DGS_NETWORKS, ids=TEST_DGS_NETWORKS_IDS)
def dgs_network_path(request) -> Path:
    return request.param


@pytest.fixture
def dgs_special_network_dir() -> Path:
    return TEST_DGS_SPECIAL_NETWORKS_DIR


@pytest.fixture
def test_networks_path() -> Path:
    return TEST_ALL_NETWORKS_DATA_FOLDER


@pytest.fixture(params=THREE_PHASES_TRANSFORMER_TYPES, ids=THREE_PHASES_TRANSFORMER_TYPES)
def three_phases_transformer_type(request) -> str:
    return request.param


@pytest.fixture(autouse=True)
def patch_engine(request):  # noqa: C901
    mpatch = MonkeyPatch()

    if "no_patch_engine" in request.keywords:
        # A load flow must be solved in the test
        # Skip if no license key in the environment
        if os.getenv("ROSEAU_LOAD_FLOW_LICENSE_KEY") is None:  # pragma: no-cover
            pytest.skip(
                reason="This test requires a license key. Please set ROSEAU_LOAD_FLOW_LICENSE_KEY in your environment."
            )

        # Activate logging
        set_logging_config("debug")
    else:
        # Patch the engine

        class Foo:
            def __init__(self, *args, **kwargs):  # Accept all constructor parameters
                pass

            def __getattr__(self, attr):  # Accept all methods
                if attr.startswith("__array"):  # Let numpy interface
                    return object.__getattr__(self, attr)
                else:
                    return self.foo

            def foo(self, *args, **kwargs):
                pass

        def bar(*args, **kwargs):  # pragma: no-cover
            pass

        # Get all roseau.load_flow_single and roseau.load_flow submodules
        for dp in (Path(roseau.load_flow_single.__file__).parent, Path(roseau.load_flow.__file__).parent):
            relative_to = dp.parents[1]
            for dirpath, _, filenames in os.walk(dp):  # TODO In Python 3.12 use rlf_directory_path.walk()
                dirpath = Path(dirpath)  # TODO Useless in Python 3.12
                for p in dirpath.parts:
                    if p in {"tests", "__pycache__", "data"}:
                        break
                else:
                    base_module = str(dirpath.relative_to(relative_to)).replace("/", ".")
                    for f in filenames:
                        if not f.endswith(".py"):
                            continue
                        if f in ("constants.py", "types.py") and base_module == "roseau.load_flow.utils":
                            continue  # TODO Remove when these deprecated files are removed
                        module = importlib.import_module(f"{base_module}.{f.removesuffix('.py')}")
                        for _, klass in inspect.getmembers(
                            module,
                            lambda member: inspect.isclass(member)
                            and "load_flow_engine." in member.__module__
                            and member.__name__.startswith("Cy")
                            and member.__name__ != "CyLicense",  # Test of the static methods of this class
                        ):
                            mpatch.setattr(f"{module.__name__}.{klass.__name__}", Foo)

        # Also patch the activate license function of the _solvers module
        mpatch.setattr("roseau.load_flow.license.cy_activate_license", bar)

    yield mpatch
    mpatch.undo()
