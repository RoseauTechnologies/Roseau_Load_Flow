import numpy as np

from roseau.load_flow_single import Bus, Line, LineParameters


def test_res_branches_voltages():
    # Same phases
    bus1 = Bus("bus1")
    bus2 = Bus("bus2")
    lp = LineParameters("lp", z_line=1)
    line = Line("line", bus1, bus2, length=1, parameters=lp)
    bus1._res_voltage = 400.0 + 0.0j
    bus2._res_voltage = 380.47405027 + 0.0j
    line_v1, line_v2 = line.res_voltages
    assert np.isclose(line_v1, bus1.res_voltage)
    assert np.isclose(line_v2, bus2.res_voltage)
