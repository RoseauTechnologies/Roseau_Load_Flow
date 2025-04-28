from pathlib import Path

import pytest

from roseau.load_flow_single.network import ElectricalNetwork

HERE = Path(__file__).parent.expanduser().resolve()
DATA_FOLDER = HERE / "data"
NETWORK_FILES = list(DATA_FOLDER.glob("*_network.json"))


# Do not set scope to "session", otherwise the `patch_engine` fixture will not be called
@pytest.fixture(params=NETWORK_FILES, ids=[x.stem for x in NETWORK_FILES])
def network_with_results(request) -> ElectricalNetwork:
    return ElectricalNetwork.from_json(path=request.param, include_results=True)
