import pytest

from roseau.load_flow_single.network import ElectricalNetwork


# Do not set scope to "session", otherwise the `patch_engine` fixture will not be called
@pytest.fixture
def network_with_results(test_networks_path) -> ElectricalNetwork:
    return ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=True)
