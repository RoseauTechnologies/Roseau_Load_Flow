import warnings

import numpy as np
import pytest

from roseau.load_flow.models import Bus, Line, LineParameters, Switch


def test_powers_equal(network_with_results):
    line = network_with_results.lines["line"]
    vs = network_with_results.sources["vs"]
    pl = network_with_results.loads["load"]
    powers1, powers2 = line.res_powers
    assert np.allclose(sum(powers1), -sum(vs.res_powers))
    assert np.allclose(sum(powers2), -sum(pl.res_powers))
    assert np.allclose(powers1 + powers2, line.res_power_losses)


def test_different_voltage_levels():
    bus1 = Bus(id="bus1", phases="abc", nominal_voltage=240)
    bus2 = Bus(id="bus2", phases="abc", nominal_voltage=240)
    bus3 = Bus(id="bus3", phases="abc")
    bus4 = Bus(id="bus4", phases="abc", nominal_voltage=400)
    lp = LineParameters(id="lp", z_line=np.eye(3, dtype=complex))
    with warnings.catch_warnings(action="error"):
        Line(id="ln good", bus1=bus1, bus2=bus2, parameters=lp, length=0.1)  # OK
        Line(id="ln good2", bus1=bus1, bus2=bus3, parameters=lp, length=0.1)  # OK
        Switch(id="sw good", bus1=bus1, bus2=bus2)  # OK
        Switch(id="sw good2", bus1=bus1, bus2=bus3)  # OK
    with pytest.warns(
        UserWarning, match=r"Line 'ln bad' connects buses with different nominal voltages: 240 V and 400 V."
    ):
        Line(id="ln bad", bus1=bus1, bus2=bus4, parameters=lp, length=0.1)
    with pytest.warns(
        UserWarning, match=r"Switch 'sw bad' connects buses with different nominal voltages: 240 V and 400 V."
    ):
        Switch(id="sw bad", bus1=bus1, bus2=bus4)
