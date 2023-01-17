from roseau.load_flow.models import AbstractLoad, VoltageSource
from roseau.load_flow.network import ElectricalNetwork


def test_from_dgs(dgs_network_path, monkeypatch):
    # Test with floating neutral (monkeypatch the whole test function)
    monkeypatch.setattr(AbstractLoad, "_floating_neutral_allowed", True)
    monkeypatch.setattr(VoltageSource, "_floating_neutral_allowed", True)
    # Read DGS
    en = ElectricalNetwork.from_dgs(dgs_network_path)
    # Check the validity of the network
    en._check_validity(constructed=False)
