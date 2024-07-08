import json
from collections.abc import Generator
from pathlib import Path

from roseau.load_flow import ElectricalNetwork, RoseauLoadFlowException

PROJECT_ROOT = Path(__file__).parent.parent
TEST_DATA_DIR = PROJECT_ROOT / "roseau" / "load_flow" / "tests" / "data"
DATA_DIR = PROJECT_ROOT / "roseau" / "load_flow" / "data" / "networks"


def all_network_paths() -> Generator[Path, None, None]:
    # Test networks
    yield from (TEST_DATA_DIR / "networks").glob("**/network*.json")
    # Benchmark networks
    yield from (TEST_DATA_DIR / "benchmark").glob("**/network*.json")
    # Package data
    yield from DATA_DIR.glob("[!Catalogue]*.json")


def upgrade_network(path: Path) -> None:
    net = ElectricalNetwork.from_json(path)
    net.to_json(path)


def update_bad_transformer_id(path: Path) -> None:
    with path.open() as f:
        data = json.load(f)

    if "branches" in data:
        # For versions < 2
        for branch in data["branches"]:
            branch_id = branch["id"]
            if branch["type"] == "transformer" and isinstance(branch_id, str) and branch_id.startswith("line"):
                branch["id"] = "tr" + branch_id.removeprefix("line")
    else:
        # For version >=2
        for transformer in data["transformers"]:
            transformer_id = transformer["id"]
            if isinstance(transformer_id, str) and transformer_id.startswith("line"):
                transformer["id"] = "tr" + transformer_id.removeprefix("line")

    net = ElectricalNetwork.from_dict(data)
    net.to_json(path)


if __name__ == "__main__":
    for path in all_network_paths():
        try:
            upgrade_network(path)
            # update_bad_transformer_id(path)
        except RoseauLoadFlowException:
            print(f"Error in {path.relative_to(PROJECT_ROOT)}")
            raise
