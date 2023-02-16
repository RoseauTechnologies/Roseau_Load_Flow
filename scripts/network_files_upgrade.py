from collections.abc import Generator
from pathlib import Path

from roseau.load_flow import ElectricalNetwork, RoseauLoadFlowException

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "roseau" / "load_flow" / "tests" / "data"
DOC_DATA_DIR = PROJECT_ROOT / "doc" / "notebooks" / "data"


def all_network_paths() -> Generator[Path, None, None]:
    # Test networks
    yield from (DATA_DIR / "networks").glob("**/network*.json")
    # Benchmark networks
    yield from (DATA_DIR / "benchmark").glob("**/network*.json")
    # Documentation networks
    yield from DOC_DATA_DIR.glob("*.json")


if __name__ == "__main__":
    # from roseau.load_flow import AbstractLoad, VoltageSource

    # # Allow floating neutral otherwise the upgrade will fail for some files
    # AbstractLoad._floating_neutral_allowed = True
    # VoltageSource._floating_neutral_allowed = True

    for path in all_network_paths():
        try:
            net = ElectricalNetwork.from_json(path)
            net.to_json(path)
        except RoseauLoadFlowException:
            print(f"Error in {path.relative_to(PROJECT_ROOT)}")
            raise
