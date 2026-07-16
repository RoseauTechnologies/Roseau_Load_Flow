from pathlib import Path

import pytest

HERE = Path(__file__).parent.expanduser().absolute()
TEST_ALL_NETWORKS_DATA_FOLDER = HERE / "tests" / "data" / "networks"

TEST_DGS_NETWORKS_DIR = HERE / "tests" / "data" / "dgs"
TEST_DGS_NETWORKS = list(TEST_DGS_NETWORKS_DIR.rglob("*.json"))
TEST_DGS_NETWORKS_IDS = [x.stem for x in TEST_DGS_NETWORKS]
TEST_DGS_SPECIAL_NETWORKS_DIR = TEST_DGS_NETWORKS_DIR / "special"


@pytest.fixture(params=["impedance", "power"], ids=["impedance", "power"])
def network_load_data_name(request) -> str:
    return request.param


@pytest.fixture(params=TEST_DGS_NETWORKS, ids=TEST_DGS_NETWORKS_IDS)
def dgs_network_path(request) -> Path:
    return request.param


@pytest.fixture(scope="session")
def dgs_networks_dir() -> Path:
    return TEST_DGS_NETWORKS_DIR


@pytest.fixture(scope="session")
def dgs_special_networks_dir() -> Path:
    return TEST_DGS_SPECIAL_NETWORKS_DIR


@pytest.fixture(scope="session")
def test_networks_path() -> Path:
    return TEST_ALL_NETWORKS_DATA_FOLDER
