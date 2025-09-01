from pathlib import Path

import pytest

import roseau.load_flow_single
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
    yield from patch_engine_impl(request, extra_dir=Path(roseau.load_flow_single.__file__).parent)
