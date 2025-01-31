import numpy as np


def test_powers_equal(network_with_results):
    line = network_with_results.lines["line"]
    vs = network_with_results.sources["vs"]
    pl = network_with_results.loads["load"]
    powers1, powers2 = line.res_powers
    assert np.allclose(sum(powers1), -sum(vs.res_powers))
    assert np.allclose(sum(powers2), -sum(pl.res_powers))
    assert np.allclose(powers1 + powers2, line.res_power_losses)
