import inspect
import os
from pathlib import Path

import numpy as np
import pytest
import setuptools
from _pytest.monkeypatch import MonkeyPatch
from pandas.testing import assert_frame_equal

import roseau

# Variable to test the network
HERE = Path(__file__).parent.expanduser().absolute()
TEST_ALL_NETWORKS_DATA_FOLDER = HERE / "tests" / "data" / "networks"
TEST_ALL_NETWORKS_DATA_PARAMS = [x for x in TEST_ALL_NETWORKS_DATA_FOLDER.glob("*") if x.is_dir()]
TEST_ALL_NETWORKS_DATA_IDS = [x.name for x in TEST_ALL_NETWORKS_DATA_PARAMS]
TEST_DGS_NETWORKS = list((HERE / "tests" / "data" / "dgs").glob("*"))
TEST_DGS_NETWORKS_IDS = [x.stem for x in TEST_DGS_NETWORKS]

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

    # Get all roseau.load_flow submodules
    package_names = [
        f"{roseau.load_flow.__name__}.{x}" for x in setuptools.find_packages(os.path.dirname(roseau.load_flow.__file__))
    ]
    modules = [roseau.load_flow]
    final_modules = []
    while modules:
        module = modules.pop(-1)
        new_modules = [m[1] for m in inspect.getmembers(module, predicate=inspect.ismodule)]
        final_modules.extend(new_modules)
        for m in new_modules:
            if m.__name__ in package_names:
                modules.append(m)
    # Patch all cython classes
    mpatch = MonkeyPatch()
    for module in final_modules:
        classes = inspect.getmembers(module, predicate=inspect.isclass)
        for class_name, _class in classes:
            if class_name.startswith("Cy"):
                mpatch.setattr(f"{module.__name__}.{_class.__name__}", Foo)
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
