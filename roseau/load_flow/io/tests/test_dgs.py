from roseau.load_flow import ElectricalNetwork


def test_from_dgs(dgs_network_path):
    # Read DGS
    en = ElectricalNetwork.from_dgs(dgs_network_path)
    # Check the validity of the network
    en._check_validity()
