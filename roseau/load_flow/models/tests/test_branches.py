import numpy as np

from roseau.load_flow import Bus, Line, LineParameters


def test_res_branches_potentials():
    # Same phases
    bus1 = Bus("bus1", phases="an")
    bus2 = Bus("bus2", phases="an")
    lp = LineParameters("lp", z_line=np.eye(2, dtype=complex))
    line = Line("line", bus1, bus2, phases="an", length=1, parameters=lp)
    bus1._res_potentials = np.array([230.0 + 0.0j, 0.0 + 0.0j])
    bus2._res_potentials = np.array([225.47405027 + 0.0j, 4.52594973 + 0.0j])
    line_pot1, line_pot2 = line.res_potentials
    assert np.allclose(line_pot1, bus1.res_potentials)
    assert np.allclose(line_pot2, bus2.res_potentials)

    # Different phases
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abc")
    lp = LineParameters("lp", z_line=np.eye(2, dtype=complex))
    line = Line("line", bus1, bus2, phases="ca", length=1, parameters=lp)
    bus1._res_potentials = np.array(
        [20000.0 + 0.0j, -10000.0 - 17320.50807569j, -10000.0 + 17320.50807569j, 0.0 + 0.0j]
    )
    bus2._res_potentials = np.array(
        [19962.27794964 - 62.50004648j, -10017.22332639 - 17267.46636437j, -9945.05462325 + 17329.96641085j]
    )
    line_pot1, line_pot2 = line.res_potentials
    assert np.allclose(line_pot1.m_as("V"), [-10000.0 + 17320.50807569j, 20000.0 + 0.0j])
    assert np.allclose(line_pot2.m_as("V"), [-9945.05462325 + 17329.96641085j, 19962.27794964 - 62.50004648j])


def test_powers_equal(network_with_results):
    line: Line = network_with_results.branches["line"]
    vs = network_with_results.sources["vs"]
    pl = network_with_results.loads["load"]
    powers1, powers2 = line.res_powers
    assert np.allclose(sum(powers1), -sum(vs.res_powers))
    assert np.allclose(sum(powers2), -sum(pl.res_powers))
    assert np.allclose(powers1 + powers2, line.res_power_losses)
