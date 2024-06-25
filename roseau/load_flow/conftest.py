import importlib
import inspect
import os
from pathlib import Path

import numpy as np
import pytest
from _pytest.monkeypatch import MonkeyPatch
from pandas.testing import assert_frame_equal

import roseau

# Variable to test the network
HERE = Path(__file__).parent.expanduser().absolute()
TEST_ALL_NETWORKS_DATA_FOLDER = HERE / "tests" / "data" / "networks"
TEST_ALL_NETWORKS_DATA_PARAMS = [x for x in TEST_ALL_NETWORKS_DATA_FOLDER.glob("*") if x.is_dir()]
TEST_ALL_NETWORKS_DATA_IDS = [x.name for x in TEST_ALL_NETWORKS_DATA_PARAMS]
TEST_DGS_NETWORKS = list((HERE / "tests" / "data" / "dgs").rglob("*.json"))
TEST_DGS_NETWORKS_IDS = [x.stem for x in TEST_DGS_NETWORKS]
TEST_DGS_SPECIAL_NETWORKS_DIR = HERE / "tests" / "data" / "dgs" / "special"

TEST_SOME_NETWORKS_NAMES_SET = {
    "mv_network_12_buses",
    "lv_network_12_buses",
    "mv_lv_network_24_buses",
    "network_6_buses",
    "mv_lv_transformers",
    "feeder_die",
    "switch",
}
TEST_SOME_NETWORKS_DATA_PARAMS = [
    x for x in TEST_ALL_NETWORKS_DATA_FOLDER.glob("*") if x.is_dir() if x.name in TEST_SOME_NETWORKS_NAMES_SET
]
TEST_SOME_NETWORKS_DATA_IDS = [x.name for x in TEST_SOME_NETWORKS_DATA_PARAMS]

TEST_COMPARISON_DATA_FOLDER = HERE / "tests" / "data" / "comparison"
TEST_COMPARISON_DATA_PARAMS = [x for x in TEST_COMPARISON_DATA_FOLDER.glob("*") if x.is_dir()]
TEST_COMPARISON_DATA_IDS = [x.name for x in TEST_COMPARISON_DATA_PARAMS]


@pytest.fixture(scope="session", autouse=True)
def patch_engine():
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

    def bar(*args, **kwargs):
        pass

    # Get all roseau.load_flow submodules
    mpatch = MonkeyPatch()
    rlf_directory_path = Path(roseau.load_flow.__file__).parent
    rlf_engine_prefix = "roseau.load_flow_engine."
    relative_to = Path(roseau.load_flow.__file__).parents[2]
    for dirpath, _, filenames in os.walk(rlf_directory_path):  # TODO In Python 3.12 use rlf_directory_path.walk()
        dirpath = Path(dirpath)  # TODO Useless in Python 3.12
        for p in dirpath.parts:
            if p in {"tests", "__pycache__", "data"}:
                break
        else:
            base_module = str(dirpath.relative_to(relative_to)).replace("/", ".")
            for f in filenames:
                if not f.endswith(".py"):
                    continue
                module = importlib.import_module(f"{base_module}.{f.removesuffix('.py')}")
                for _, klass in inspect.getmembers(
                    module,
                    lambda member: inspect.isclass(member)
                    and member.__module__.startswith(rlf_engine_prefix)
                    and member.__name__.startswith("Cy"),
                ):
                    mpatch.setattr(f"{module.__name__}.{klass.__name__}", Foo)

    # Also patch the activate license function of the _solvers module
    mpatch.setattr("roseau.load_flow.license.cy_activate_license", bar)
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="module")
def rg() -> np.random.Generator:
    return np.random.default_rng(seed=42)


@pytest.fixture(params=["impedance", "power"], ids=["impedance", "power"])
def network_load_data_name(request) -> str:
    return request.param


@pytest.fixture(params=TEST_ALL_NETWORKS_DATA_PARAMS, ids=TEST_ALL_NETWORKS_DATA_IDS)
def all_network_folder(request) -> Path:
    return request.param


@pytest.fixture()
def all_network_path(all_network_folder, network_load_data_name) -> Path:
    _check_folders(all_network_folder, network_load_data_name)
    return all_network_folder / f"network_{network_load_data_name}.json"


@pytest.fixture()
def all_network_result(all_network_folder, network_load_data_name) -> Path:
    return all_network_folder / "results_linear_method.csv"


@pytest.fixture(params=TEST_SOME_NETWORKS_DATA_PARAMS, ids=TEST_SOME_NETWORKS_DATA_IDS)
def some_network_folder(request) -> Path:
    return request.param


@pytest.fixture()
def some_network_path(some_network_folder, network_load_data_name) -> Path:
    _check_folders(some_network_folder, network_load_data_name)
    return some_network_folder / f"network_{network_load_data_name}.json"


@pytest.fixture()
def some_network_result(some_network_folder, network_load_data_name) -> Path:
    return some_network_folder / "results_linear_method.csv"


@pytest.fixture(params=TEST_DGS_NETWORKS, ids=TEST_DGS_NETWORKS_IDS)
def dgs_network_path(request) -> Path:
    return request.param


@pytest.fixture()
def dgs_special_network_dir() -> Path:
    return TEST_DGS_SPECIAL_NETWORKS_DIR


@pytest.fixture()
def test_networks_path() -> Path:
    return TEST_ALL_NETWORKS_DATA_FOLDER


#
# Utils
#
def _check_folders(network_folder, network_load_data_name):
    if "mv_network_12_buses" in str(network_folder) and network_load_data_name == "power":
        pytest.skip("Need additional investigations!")

    if "mv_lv_network_24_buses" in str(network_folder) and network_load_data_name == "power":
        pytest.skip("Need additional investigations!")


def assert_frame_not_equal(*args, **kwargs):
    try:
        assert_frame_equal(*args, **kwargs)
    except AssertionError:
        # frames are not equal
        pass
    else:
        # frames are equal
        raise AssertionError
