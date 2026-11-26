from pathlib import Path

import pytest

import roseau.load_flow as rlf

HERE = Path(__file__).parent.expanduser().absolute()
TEST_ALL_NETWORKS_DATA_FOLDER = HERE / "tests" / "data" / "networks"

TEST_DGS_NETWORKS_DIR = HERE / "tests" / "data" / "dgs"
TEST_DGS_REGULATORS_NETWORKS_DIR = TEST_DGS_NETWORKS_DIR / "regulators"  # Tested separately
TEST_DGS_NETWORKS = [
    p for p in TEST_DGS_NETWORKS_DIR.rglob("*.json") if not p.is_relative_to(TEST_DGS_REGULATORS_NETWORKS_DIR)
]
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
def dgs_regulators_networks_dir() -> Path:
    return TEST_DGS_REGULATORS_NETWORKS_DIR


@pytest.fixture(scope="session")
def test_networks_path() -> Path:
    return TEST_ALL_NETWORKS_DATA_FOLDER


# The following networks are generated using the scripts/generate_test_networks.py script
@pytest.fixture
def all_elements_network(test_networks_path) -> rlf.ElectricalNetwork:
    # Load the network from the JSON file (without results)
    return rlf.ElectricalNetwork.from_json(path=test_networks_path / "all_elements_network.json", include_results=False)


@pytest.fixture
def all_elements_network_with_results(test_networks_path) -> rlf.ElectricalNetwork:
    # Load the network from the JSON file (with results, no need to invoke the solver)
    return rlf.ElectricalNetwork.from_json(path=test_networks_path / "all_elements_network.json", include_results=True)


@pytest.fixture
def small_network(test_networks_path) -> rlf.ElectricalNetwork:
    # Load the network from the JSON file (without results)
    return rlf.ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=False)


@pytest.fixture
def small_network_with_results(test_networks_path) -> rlf.ElectricalNetwork:
    # Load the network from the JSON file (with results, no need to invoke the solver)
    return rlf.ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=True)


@pytest.fixture
def single_phase_network(test_networks_path) -> rlf.ElectricalNetwork:
    return rlf.ElectricalNetwork.from_json(path=test_networks_path / "single_phase_network.json", include_results=True)
