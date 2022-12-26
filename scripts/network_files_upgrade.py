from pathlib import Path

from roseau.load_flow import ElectricalNetwork

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "roseau" / "load_flow" / "tests" / "data"


for network_dir in ("networks", "benchmark"):
    for path in (DATA_DIR / network_dir).glob("**/network*.json"):
        # print(path.relative_to(PROJECT_ROOT))
        net = ElectricalNetwork.from_json(path)
        net.to_json(path)
