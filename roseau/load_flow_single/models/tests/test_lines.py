import numpy as np
import pytest
from pint import DimensionalityError

from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_single.models import Bus, Line, LineParameters


def test_lines_length():
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    lp = LineParameters(id="lp", z_line=1.0)

    # Negative value for length in the constructor
    with pytest.raises(RoseauLoadFlowException) as e:
        Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=-5)
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # The same with a unit
    with pytest.raises(RoseauLoadFlowException) as e:
        Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(-5, "m"))
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # Test on the length setter
    line = Line(id="line3", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "m"))
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
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    lp = LineParameters(id="lp", z_line=1.0)

    # Good unit constructor
    line = Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "km"))
    assert np.isclose(line._length, 5)

    # Good unit setter
    line = Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    assert np.allclose(line._length, 5)
    line.length = Q_(6.5, "m")
    assert np.isclose(line._length, 6.5e-3)

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        Line(id="line3", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "A"))

    # Bad unit setter
    line = Line(id="line4", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        line.length = Q_(6.5, "A")


def test_line_parameters_shortcut():
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")

    #
    # Without shunt
    #
    lp = LineParameters(id="lp", z_line=1.0)

    # Z
    line = Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))
    assert np.allclose(line.z_line.m_as("ohm"), 0.05)

    # Y
    assert not line.with_shunt
    assert np.allclose(line.y_shunt.m_as("S"), 0.0)

    #
    # With shunt
    #
    z_line = 0.01
    y_shunt = 1e-5
    lp = LineParameters(id="lp", z_line=z_line, y_shunt=y_shunt)

    # Z
    line = Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))
    assert np.allclose(line.z_line.m_as("ohm"), 0.05 * z_line)

    # Y
    assert line.with_shunt
    assert np.allclose(line.y_shunt.m_as("S"), 0.05 * y_shunt)


def test_max_loading():
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    lp = LineParameters(id="lp", z_line=1.0)
    line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))

    # Value must be positive
    with pytest.raises(RoseauLoadFlowException) as e:
        line.max_loading = -1
    assert e.value.msg == "Maximum loading must be positive: -1 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        line.max_loading = 0
    assert e.value.msg == "Maximum loading must be positive: 0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE


def test_res_violated():
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    lp = LineParameters(id="lp", z_line=1.0)
    line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))

    line._res_currents = 10, -10

    # No limits
    assert line.max_loading == Q_(1, "")
    assert line.res_violated is None

    # No constraint violated
    lp = LineParameters(id="lp", z_line=1.0, ampacity=11)
    line.parameters = lp
    assert not line.res_violated
    assert np.allclose(line.res_loading, 10 / 11)

    # Reduced max_loading
    line.max_loading = Q_(50, "%")
    assert line.max_loading.m == 0.5
    assert line.res_violated
    assert np.allclose(line.res_loading, 10 / 11)

    # Two violations
    lp = LineParameters(id="lp", z_line=1.0, ampacity=9)
    line.parameters = lp
    line.max_loading = 1
    assert line.res_violated
    assert np.allclose(line.res_loading, 10 / 9)

    # Side 1 violation
    lp = LineParameters(id="lp", z_line=1.0, ampacity=11)
    line.parameters = lp
    line._res_currents = 12, -10
    assert line.res_violated
    assert np.allclose(line.res_loading, 12 / 11)

    # Side 2 violation
    lp = LineParameters(id="lp", z_line=1.0, ampacity=11)
    line.parameters = lp
    line._res_currents = 10, -12
    assert line.res_violated
    assert np.allclose(line.res_loading, 12 / 11)

    #
    # The same with arrays
    #
    line._res_currents = 10, -10

    # No constraint violated
    lp = LineParameters(id="lp", z_line=1.0, ampacity=11)
    line.parameters = lp
    line.max_loading = 1
    assert not line.res_violated
    assert np.allclose(line.res_loading, 10 / 11)

    # Side 1 violation
    lp = LineParameters(id="lp", z_line=1.0, ampacity=11)
    line.parameters = lp
    line._res_currents = 12, -10
    assert line.res_violated
    assert np.allclose(line.res_loading, 12 / 11)

    # Side 2 violation
    lp = LineParameters(id="lp", z_line=1.0, ampacity=11)
    line.parameters = lp
    line._res_currents = 10, -12
    assert line.res_violated
    assert np.allclose(line.res_loading, 12 / 11)


def test_lines_results():
    z_line = (0.1 + 0.1j) / 2
    y_shunt = None
    len_line = 10
    line_voltages = 20000.0 + 0.0j, 19883.965550324414 - 84.999999999981j
    line_currents = (116.06729363657514 - 17.9177478743607j), (-116.06729363657514 + 17.9177478743607j)
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    lp = LineParameters(id="lp", z_line=z_line, y_shunt=y_shunt)
    line = Line(id="line", bus1=bus1, bus2=bus2, length=len_line, parameters=lp)
    line._res_voltages = line_voltages
    line._res_currents = line_currents
    res_powers1, res_powers2 = (x.m for x in line.res_powers)
    series_losses = line.res_series_power_losses.m
    shunt_losses = line.res_shunt_power_losses.m
    line_losses = line.res_power_losses.m
    if y_shunt is None:
        assert np.isclose(shunt_losses, 0)
    else:
        assert not np.isclose(shunt_losses, 0)
    assert np.isclose(line_losses, series_losses + shunt_losses)

    # Sanity check: the total power lost is equal to the sum of the powers flowing through
    assert np.isclose(res_powers1 + res_powers2, line_losses)

    # Check currents (Kirchhoff's law at each end of the line)
    i1_line, i2_line = (x.m for x in line.res_currents)
    i_series = line.res_series_current.m
    i1_shunt, i2_shunt = (x.m for x in line.res_shunt_currents)
    assert np.isclose(i1_line, i_series + i1_shunt)
    assert np.isclose(i2_line + i_series, i2_shunt)


def test_currents_equal(network_with_results):
    line = network_with_results.lines["line"]
    current1, current2 = (x.m for x in line.res_currents)
    series_current = line.res_series_current.m
    shunt_current1, shunt_current2 = (x.m for x in line.res_shunt_currents)
    assert np.isclose(current1, series_current + shunt_current1)
    assert np.isclose(current2 + series_current, shunt_current2)


def test_powers_equal(network_with_results):
    line = network_with_results.lines["line"]
    vs = network_with_results.sources["vs"]
    pl = network_with_results.loads["load"]
    power1, power2 = (x.m for x in line.res_powers)
    power_loss = power1 + power2
    expected_power1 = -vs.res_power.m
    expected_power2 = -pl.res_power.m
    expected_power_loss = line.res_power_losses.m
    assert np.isclose(power1, expected_power1)
    assert np.isclose(power2, expected_power2)
    assert np.isclose(power_loss, expected_power_loss)


def test_different_voltage_levels():
    bus1 = Bus(id="bus1", nominal_voltage=240)
    bus2 = Bus(id="bus2", nominal_voltage=240)
    bus3 = Bus(id="bus3")
    bus4 = Bus(id="bus4", nominal_voltage=400)
    lp = LineParameters(id="lp", z_line=1)
    Line(id="ln good", bus1=bus1, bus2=bus2, parameters=lp, length=0.1)  # OK
    Line(id="ln good2", bus1=bus1, bus2=bus3, parameters=lp, length=0.1)  # OK
    with pytest.warns(
        UserWarning, match=r"Line 'ln bad' connects buses with different nominal voltages: 240.0 and 400.0."
    ):
        Line(id="ln bad", bus1=bus1, bus2=bus4, parameters=lp, length=0.1)
