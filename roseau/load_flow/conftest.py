from pathlib import Path

import numpy as np
import pytest
from pandas.testing import assert_frame_equal

from roseau.load_flow.utils.log import set_logging_config

# Variable to test the network
HERE = Path(__file__).parent.expanduser().absolute()
TEST_ALL_NETWORKS_DATA_FOLDER = HERE / "tests" / "data" / "networks"
TEST_ALL_NETWORKS_DATA_PARAMS = [x for x in TEST_ALL_NETWORKS_DATA_FOLDER.glob("*") if x.is_dir()]
TEST_ALL_NETWORKS_DATA_IDS = [x.name for x in TEST_ALL_NETWORKS_DATA_PARAMS]
TEST_DGS_NETWORKS = [x for x in (HERE / "tests" / "data" / "dgs").glob("*")]
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


@pytest.fixture(scope="function", autouse=True)
def log_setup():
    """A basic fixture (automatically used) to set the log level"""
    set_logging_config(verbosity="debug")


@pytest.fixture(scope="module")
def rg() -> np.random.Generator:
    return np.random.default_rng(seed=42)


@pytest.fixture(scope="function", params=["impedance", "power"], ids=["impedance", "power"])
def network_load_data_name(request) -> str:
    return request.param


@pytest.fixture(scope="function", params=TEST_ALL_NETWORKS_DATA_PARAMS, ids=TEST_ALL_NETWORKS_DATA_IDS)
def all_network_folder(request) -> Path:
    return request.param


@pytest.fixture(scope="function")
def all_network_path(all_network_folder, network_load_data_name) -> Path:
    _check_folders(all_network_folder, network_load_data_name)
    return all_network_folder / f"network_{network_load_data_name}.json"


@pytest.fixture(scope="function")
def all_network_result(all_network_folder, network_load_data_name) -> Path:
    return all_network_folder / "results_linear_method.csv"


@pytest.fixture(scope="function", params=TEST_SOME_NETWORKS_DATA_PARAMS, ids=TEST_SOME_NETWORKS_DATA_IDS)
def some_network_folder(request) -> Path:
    return request.param


@pytest.fixture(scope="function")
def some_network_path(some_network_folder, network_load_data_name) -> Path:
    _check_folders(some_network_folder, network_load_data_name)
    return some_network_folder / f"network_{network_load_data_name}.json"


@pytest.fixture(scope="function")
def some_network_result(some_network_folder, network_load_data_name) -> Path:
    return some_network_folder / "results_linear_method.csv"


@pytest.fixture(scope="function", params=TEST_DGS_NETWORKS, ids=TEST_DGS_NETWORKS_IDS)
def dgs_network_path(request) -> Path:
    return request.param


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
