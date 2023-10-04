import numpy as np
import pytest
from pint import DimensionalityError

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineParameters
from roseau.load_flow.units import Q_


def test_lines_length():
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus1", phases="abcn")
    lp = LineParameters("lp", z_line=np.eye(4, dtype=complex))

    # Negative value for length in the constructor
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=-5)
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # The same with a unit
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(-5, "m"))
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # Test on the length setter
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "m"))
    with pytest.raises(RoseauLoadFlowException) as e:
        line.length = -6.5
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # The same with a unit
    with pytest.raises(RoseauLoadFlowException) as e:
        line.length = Q_(-6.5, "cm")
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE


def test_lines_units():
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus1", phases="abcn")
    lp = LineParameters("lp", z_line=np.eye(4, dtype=complex))

    # Good unit constructor
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "km"))
    assert np.isclose(line._length, 5)

    # Good unit setter
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    assert np.allclose(line._length, 5)
    line.length = Q_(6.5, "m")
    assert np.isclose(line._length, 6.5e-3)

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "A"))

    # Bad unit setter
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        line.length = Q_(6.5, "A")


def test_line_parameters_shortcut():
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus1", phases="abcn")

    #
    # Without shunt
    #
    lp = LineParameters("lp", z_line=np.eye(4, dtype=complex))

    # Z
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))
    assert np.allclose(line.z_line.m_as("ohm"), 0.05 * np.eye(4, dtype=complex))

    # Y
    assert not line.with_shunt
    assert np.allclose(line.y_shunt.m_as("S"), np.zeros(shape=(4, 4), dtype=complex))

    #
    # With shunt
    #
    z_line = 0.01 * np.eye(4, dtype=complex)
    y_shunt = 1e-5 * np.eye(4, dtype=complex)
    lp = LineParameters("lp", z_line=z_line, y_shunt=y_shunt)

    # Z
    ground = Ground("ground")
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"), ground=ground)
    assert np.allclose(line.z_line.m_as("ohm"), 0.05 * z_line)

    # Y
    assert line.with_shunt
    assert np.allclose(line.y_shunt.m_as("S"), 0.05 * y_shunt)


def test_res_violated():
    bus1 = Bus("bus1", phases="abc")
    bus2 = Bus("bus1", phases="abc")
    lp = LineParameters("lp", z_line=np.eye(3, dtype=complex))
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))
    direct_seq = np.exp([0, -2 / 3 * np.pi * 1j, 2 / 3 * np.pi * 1j])

    bus1._res_potentials = 230 * direct_seq
    bus2._res_potentials = 225 * direct_seq
    line._res_currents = 10 * direct_seq, -10 * direct_seq

    # No limits
    assert line.res_violated is None

    # No constraint violated
    lp.max_current = 11
    assert line.res_violated is False

    # Two violations
    lp.max_current = 9
    assert line.res_violated is True

    # Side 1 violation
    lp.max_current = 11
    line._res_currents = 12 * direct_seq, -10 * direct_seq
    assert line.res_violated is True

    # Side 2 violation
    lp.max_current = 11
    line._res_currents = 10 * direct_seq, -12 * direct_seq
    assert line.res_violated is True

    # A single phase violation
    lp.max_current = 11
    line._res_currents = 10 * direct_seq, -10 * direct_seq
    line._res_currents[0][0] = 12 * direct_seq[0]
    line._res_currents[1][0] = -12 * direct_seq[0]
    assert line.res_violated is True
