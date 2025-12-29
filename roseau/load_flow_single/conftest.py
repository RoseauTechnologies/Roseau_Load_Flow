from pathlib import Path

import pytest

import roseau.load_flow_single as rlfs
from roseau.load_flow.conftest import patch_engine_impl

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
def patch_engine(request):
    assert rlfs.__file__ is not None
    yield from patch_engine_impl(request, extra_dir=Path(rlfs.__file__).parent)


@pytest.fixture(scope="session", autouse=True)
def patch_warn_external():
    # Exclude test files from skipped files in warn_external
    from roseau.load_flow.utils import helpers

    assert rlfs.__file__ is not None
    paths = tuple(
        str(p) for p in Path(rlfs.__file__).resolve().parent.parent.rglob("**/*.py") if "tests" not in p.parts
    )
    helpers._get_skip_file_prefixes = lambda: paths


# The following networks are generated using the scripts/generate_test_networks.py script
@pytest.fixture
def all_elements_network_path(test_networks_path) -> Path:
    return test_networks_path / "all_elements_network.json"


@pytest.fixture
def all_elements_network(all_elements_network_path) -> rlfs.ElectricalNetwork:
    """Load the network from the JSON file (without results)."""
    return rlfs.ElectricalNetwork.from_json(path=all_elements_network_path, include_results=False)


@pytest.fixture
def all_elements_network_with_results(all_elements_network_path) -> rlfs.ElectricalNetwork:
    """Load the network from the JSON file (with results, no need to invoke the solver)."""
    return rlfs.ElectricalNetwork.from_json(path=all_elements_network_path, include_results=True)


@pytest.fixture
def small_network(test_networks_path) -> rlfs.ElectricalNetwork:
    """Load the network from the JSON file (without results)."""
    return rlfs.ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=False)


@pytest.fixture
def small_network_with_results(test_networks_path) -> rlfs.ElectricalNetwork:
    """Load the network from the JSON file (with results, no need to invoke the solver)."""
    return rlfs.ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=True)
