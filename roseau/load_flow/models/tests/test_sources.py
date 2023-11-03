import numpy as np
import pytest
from pint.errors import DimensionalityError

from roseau.load_flow import Q_, Bus, VoltageSource


def test_source_units():
    bus = Bus("bus", phases="abcn")

    # Good unit constructor
    vs = VoltageSource("vs", bus, voltages=Q_([1, 1, 1], "kV"), phases="abcn")
    assert np.allclose(vs._voltages, [1000, 1000, 1000])

    # Good unit setter
    vs = VoltageSource("vs", bus, voltages=[100, 100, 100], phases="abcn")
    assert np.allclose(vs._voltages, [100, 100, 100])
    vs.voltages = Q_([1, 1, 1], "kV")
    assert np.allclose(vs._voltages, [1000, 1000, 1000])

    # Units in a list
    vs = VoltageSource("vs", bus, voltages=[Q_(1_000, "V"), Q_(1, "kV"), Q_(0.001, "MV")], phases="abcn")
    assert np.allclose(vs._voltages, [1000, 1000, 1000])

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'volt'"):
        VoltageSource("vs", bus, voltages=Q_([100, 100, 100], "A"), phases="abcn")

    # Bad unit setter
    vs = VoltageSource("vs", bus, voltages=[100, 100, 100], phases="abcn")
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'volt'"):
        vs.voltages = Q_([100, 100, 100], "A")
