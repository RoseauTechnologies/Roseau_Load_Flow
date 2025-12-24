import roseau.load_flow_single as rlfs


def test_plot_interactive_map(test_networks_path):
    en = rlfs.ElectricalNetwork.from_json(path=test_networks_path / "all_elements_network.json", include_results=True)
    en.crs = "EPSG:4326"
    rlfs.plotting.plot_interactive_map(en)
    rlfs.plotting.plot_results_interactive_map(en)
