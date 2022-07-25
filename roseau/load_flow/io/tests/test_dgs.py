from pandas.testing import assert_frame_equal

from roseau.load_flow import ElectricalNetwork


def test_from_dgs(dgs_network_path):
    # Read DGS
    en = ElectricalNetwork.from_dgs(dgs_network_path)
    en.solve_load_flow(max_iterations=50)
    buses_results_1, branches_results_1 = en.results()

    # Write to json
    en_dict = en.to_dict()
    en2 = en.from_dict(en_dict)
    en2.solve_load_flow(max_iterations=50)
    buses_results_2, branches_results_2 = en2.results()

    # Check
    assert_frame_equal(buses_results_1, buses_results_2, check_like=True)
    assert_frame_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
