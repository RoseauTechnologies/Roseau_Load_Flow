import json
from pathlib import Path

import pytest

from roseau.load_flow.network import ElectricalNetwork

HERE = Path(__file__).parent.expanduser().resolve()
DATA_FOLDER = HERE / "data"
NETWORK_FILES = list(DATA_FOLDER.glob("Network_*.json"))


@pytest.fixture(scope="session", params=NETWORK_FILES, ids=[x.stem for x in NETWORK_FILES])
def network_with_results(request) -> ElectricalNetwork:
    with open(request.param) as f:
        data = json.load(f)
    net = ElectricalNetwork.from_dict(data["network"])
    net.results_from_dict(data["results"])
    return net
