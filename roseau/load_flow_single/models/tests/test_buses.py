import numpy as np
import pandas as pd
import pytest

from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_single import (
    Bus,
    CurrentLoad,
    ElectricalNetwork,
    Line,
    LineParameters,
    PowerLoad,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)


def test_short_circuit():
    bus = Bus(id="bus")

    assert not bus._short_circuit
    bus.add_short_circuit()
    assert bus._short_circuit

    # Dict methods
    vn = 400 / np.sqrt(3)
    _ = VoltageSource("vs", bus=bus, voltage=vn)
    en = ElectricalNetwork.from_element(bus)
    en2 = ElectricalNetwork.from_dict(en.to_dict())
    assert en2.buses["bus"]._short_circuit

    # Cannot connect a load on a short-circuited bus
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="load", bus=bus, power=10)
    assert "is connected on bus" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT

    # Cannot short-circuit a bus with a power load
    bus = Bus("bus")
    assert not bus.short_circuit
    _ = PowerLoad(id="load", bus=bus, power=10)
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit()
    assert "is already connected on bus" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT

    # Cannot short-circuit a bus with a current load
    bus = Bus("bus")
    assert not bus.short_circuit
    _ = CurrentLoad(id="load", bus=bus, current=10)
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit()
    assert "is already connected on bus" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT


def test_voltage_limits():
    # Default values
    bus = Bus(id="bus")
    assert bus.nominal_voltage is None
    assert bus.min_voltage is None
    assert bus.max_voltage is None

    # Passed as arguments
    bus = Bus(id="bus", nominal_voltage=400, min_voltage_level=0.95, max_voltage_level=1.05)
    assert bus.nominal_voltage == Q_(400, "V")
    assert bus.min_voltage_level == Q_(0.95, "")
    assert bus.max_voltage_level == Q_(1.05, "")
    assert bus.min_voltage == Q_(380, "V")
    assert bus.max_voltage == Q_(420, "V")

    # Can be set to a real number
    bus.nominal_voltage = 410
    bus.min_voltage_level = 0.9
    bus.max_voltage_level = 1.06
    assert bus.min_voltage_level == Q_(0.9, "")
    assert bus.max_voltage_level == Q_(1.06, "")
    assert bus.min_voltage == Q_(369.0, "V")
    assert bus.max_voltage == Q_(434.6, "V")

    # Can be reset to None
    bus.min_voltage_level = None
    bus.max_voltage_level = None
    bus.nominal_voltage = None
    assert bus.min_voltage_level is None
    assert bus.max_voltage_level is None
    assert bus.min_voltage is None
    assert bus.max_voltage is None

    # Can be set to a Quantity
    bus.nominal_voltage = Q_(20, "kV")
    bus.min_voltage_level = Q_(90, "%")
    bus.max_voltage_level = Q_(110, "%")
    assert bus.nominal_voltage == Q_(20_000, "V")
    assert bus.min_voltage_level == Q_(0.9, "")
    assert bus.max_voltage_level == Q_(1.1, "")
    assert bus.min_voltage == Q_(18_000, "V")
    assert bus.max_voltage == Q_(22_000, "V")

    # NaNs are converted to None
    for na in (np.nan, float("nan"), pd.NA):
        bus.min_voltage_level = na
        bus.max_voltage_level = na
        bus.nominal_voltage = na
        assert bus.nominal_voltage is None
        assert bus.min_voltage_level is None
        assert bus.max_voltage_level is None
        assert bus.min_voltage is None
        assert bus.max_voltage is None

    # Min/Max voltage values defined without nominal voltage are useless
    bus.min_voltage_level = None
    bus.max_voltage_level = None
    bus.nominal_voltage = None
    with pytest.warns(
        UserWarning,
        match=(
            r"The min voltage level of bus 'bus' is useless without a nominal voltage. Please "
            r"define a nominal voltage for this bus."
        ),
    ):
        bus.min_voltage_level = 0.95

    assert bus.min_voltage_level == Q_(0.95, "")
    assert bus.min_voltage is None
    with pytest.warns(
        UserWarning,
        match=(
            r"The max voltage level of bus 'bus' is useless without a nominal voltage. Please "
            r"define a nominal voltage for this bus."
        ),
    ):
        bus.max_voltage_level = 1.05
    assert bus.max_voltage_level == Q_(1.05, "")
    assert bus.max_voltage is None

    # Erasing a nominal voltage with a min or max voltage level emits a warning
    bus.nominal_voltage = Q_(400, "V")
    with pytest.warns(
        UserWarning,
        match=r"The nominal voltage of bus 'bus' is required to use `min_voltage_level` and `max_voltage_level`.",
    ):
        bus.nominal_voltage = None

    bus.nominal_voltage = Q_(400, "V")
    bus.min_voltage_level = None
    bus.max_voltage_level = None

    # Bad values
    bus.nominal_voltage = 400
    bus.min_voltage_level = 0.95
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.max_voltage_level = 0.92
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == (
        "Cannot set max voltage level of bus 'bus' to 0.92 as it is lower than its min voltage (0.95)."
    )
    bus.max_voltage_level = 1.05
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.min_voltage_level = 1.06
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == (
        "Cannot set min voltage level of bus 'bus' to 1.06 as it is higher than its max voltage (1.05)."
    )
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.nominal_voltage = 0
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == "The nominal voltage of bus 'bus' must be positive. 0 V has been provided."
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.nominal_voltage = -400
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == "The nominal voltage of bus 'bus' must be positive. -400 V has been provided."


def test_res_voltage():
    bus = Bus(id="bus")
    bus._res_voltage = 400 + 0j

    assert np.allclose(bus.res_voltage.m, 400 + 0j)
    assert bus.res_voltage_level is None
    bus.nominal_voltage = 400  # V
    assert np.allclose(bus.res_voltage_level.m, 400 / 400)


def test_res_violated():
    bus = Bus(id="bus")
    bus._res_voltage = 400 + 0j

    # No limits
    assert bus.res_violated is None

    # Only a nominal voltage
    bus.nominal_voltage = 400
    assert bus.res_violated is None

    # Only min voltage
    bus.min_voltage_level = 0.9
    assert not bus.res_violated
    bus.min_voltage_level = 1.1
    assert bus.res_violated

    # Only max voltage
    bus.min_voltage_level = None
    bus.max_voltage_level = 1.1
    assert not bus.res_violated
    bus.max_voltage_level = 0.9
    assert bus.res_violated

    # Both min and max voltage
    # min <= v <= max
    bus.min_voltage_level = 0.9
    bus.max_voltage_level = 1.1
    assert not bus.res_violated
    # v < min
    bus.min_voltage_level = 1.1
    assert bus.res_violated
    # v > max
    bus.min_voltage_level = 0.9
    bus.max_voltage_level = 0.9
    assert bus.res_violated


def test_res_state():
    bus = Bus(id="bus")
    bus._res_voltage = 400 + 0j

    # No nominal voltage
    assert bus._res_state_getter() == "unknown"

    # No limits
    bus.nominal_voltage = 400
    assert bus._res_state_getter() == "unknown"

    # Only max voltage
    bus.max_voltage_level = 1.05
    bus._res_voltage = (400 + 0j) * 1.06
    assert bus._res_state_getter() == "very-high"
    bus._res_voltage = (400 + 0j) * 1.04
    assert bus._res_state_getter() == "high"
    bus._res_voltage = (400 + 0j) * 1.02
    assert bus._res_state_getter() == "normal"

    # Only min voltage
    bus.max_voltage_level = None
    bus.min_voltage_level = 0.95
    bus._res_voltage = (400 + 0j) * 0.94
    assert bus._res_state_getter() == "very-low"
    bus._res_voltage = (400 + 0j) * 0.96
    assert bus._res_state_getter() == "low"
    bus._res_voltage = (400 + 0j) * 0.98
    assert bus._res_state_getter() == "normal"

    # Both min and max voltage
    bus.min_voltage_level = 0.95
    bus.max_voltage_level = 1.05
    bus._res_voltage = (400 + 0j) * 1.06
    assert bus._res_state_getter() == "very-high"
    bus._res_voltage = (400 + 0j) * 1.04
    assert bus._res_state_getter() == "high"
    bus._res_voltage = (400 + 0j) * 1.0
    assert bus._res_state_getter() == "normal"
    bus._res_voltage = (400 + 0j) * 0.96
    assert bus._res_state_getter() == "low"
    bus._res_voltage = (400 + 0j) * 0.94
    assert bus._res_state_getter() == "very-low"


def test_propagate_limits():  # noqa: C901
    b1_mv = Bus(id="b1_mv")
    b2_mv = Bus(id="b2_mv")
    b3_mv = Bus(id="b3_mv")
    b1_lv = Bus(id="b1_lv")
    b2_lv = Bus(id="b2_lv")

    lp_mv = LineParameters(id="lp_mv", z_line=1.0, y_shunt=0.1)
    lp_lv = LineParameters(id="lp_lv", z_line=1.0)
    tp = TransformerParameters.from_catalogue(name="SE Minera A0Ak 100kVA 15/20kV(20) 410V Dyn11")

    Line(id="l1_mv", bus1=b1_mv, bus2=b2_mv, length=1.5, parameters=lp_mv)
    Line(id="l2_mv", bus1=b2_mv, bus2=b3_mv, length=2, parameters=lp_mv)
    Transformer(id="tr", bus_hv=b3_mv, bus_lv=b1_lv, parameters=tp)
    Line(id="l1_lv", bus1=b1_lv, bus2=b2_lv, length=1, parameters=lp_lv)

    VoltageSource(id="s_mv", bus=b1_mv, voltage=20_000)

    PowerLoad(id="pl1_mv", bus=b2_mv, power=30e3)
    PowerLoad(id="pl2_mv", bus=b3_mv, power=30e3)
    PowerLoad(id="pl1_lv", bus=b1_lv, power=3e3)
    PowerLoad(id="pl2_lv", bus=b2_lv, power=3e3)

    # All buses have None as min and max voltage
    for bus in (b1_mv, b2_mv, b3_mv, b1_lv, b2_lv):
        assert bus.min_voltage is None
        assert bus.max_voltage is None

    # Set min and max voltage of b1_mv
    b1_mv.nominal_voltage = 20_000  # V
    b1_mv.min_voltage_level = 0.95
    b1_mv.max_voltage_level = 1.05
    # propagate MV voltage limits
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.nominal_voltage == Q_(20_000, "V")
        assert bus.min_voltage_level == Q_(0.95, "")
        assert bus.max_voltage_level == Q_(1.05, "")
        assert bus.min_voltage == Q_(19_000, "V")
        assert bus.max_voltage == Q_(21_000, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.nominal_voltage is None
        assert bus.min_voltage is None
        assert bus.max_voltage is None

    # Set min and max voltage of b1_lv
    b1_lv.nominal_voltage = 400
    b1_lv.min_voltage_level = 0.915
    b1_lv.max_voltage_level = 1.085
    b1_lv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.nominal_voltage == Q_(20_000, "V")
        assert bus.min_voltage_level == Q_(0.95, "")
        assert bus.max_voltage_level == Q_(1.05, "")
        assert bus.min_voltage == Q_(19_000, "V")
        assert bus.max_voltage == Q_(21_000, "V")

    for bus in (b1_lv, b2_lv):
        assert bus.nominal_voltage == Q_(400, "V")
        assert bus.min_voltage_level == Q_(0.915, "")
        assert bus.max_voltage_level == Q_(1.085, "")
        assert bus.min_voltage == Q_(366, "V")
        assert bus.max_voltage == Q_(434, "V")

    # Reset min MV voltage limits only
    b1_mv.min_voltage_level = None
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.nominal_voltage == Q_(20_000, "V")
        assert bus.min_voltage_level is None
        assert bus.min_voltage is None
        assert bus.max_voltage_level == Q_(1.05, "")
        assert bus.max_voltage == Q_(21_000, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.nominal_voltage == Q_(400, "V")
        assert bus.min_voltage_level == Q_(0.915, "")
        assert bus.max_voltage_level == Q_(1.085, "")
        assert bus.min_voltage == Q_(366, "V")
        assert bus.max_voltage == Q_(434, "V")

    # Error, different max voltage limits
    b1_mv.max_voltage_level = 1.06
    with pytest.raises(RoseauLoadFlowException) as e:
        b1_mv.propagate_limits()
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == (
        "Cannot propagate the maximum voltage level (1.06) of bus 'b1_mv' to bus 'b2_mv' with "
        "different maximum voltage level (1.05)."
    )

    # The limits are not changed after the error
    for bus in (b2_mv, b3_mv):
        assert bus.nominal_voltage == Q_(20_000, "V")
        assert bus.min_voltage_level is None
        assert bus.min_voltage is None
        assert bus.max_voltage_level == Q_(1.05, "")
        assert bus.max_voltage == Q_(21_000, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.nominal_voltage == Q_(400, "V")
        assert bus.min_voltage_level == Q_(0.915, "")
        assert bus.max_voltage_level == Q_(1.085, "")
        assert bus.min_voltage == Q_(366, "V")
        assert bus.max_voltage == Q_(434, "V")

    # It is okay to propagate with different limits if force=True
    b1_mv.propagate_limits(force=True)
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.nominal_voltage == Q_(20_000, "V")
        assert bus.min_voltage_level is None
        assert bus.min_voltage is None
        assert bus.max_voltage_level == Q_(1.06, "")
        assert bus.max_voltage == Q_(21_200, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.nominal_voltage == Q_(400, "V")
        assert bus.min_voltage_level == Q_(0.915, "")
        assert bus.max_voltage_level == Q_(1.085, "")
        assert bus.min_voltage == Q_(366, "V")
        assert bus.max_voltage == Q_(434, "V")

    # What if there is a switch?
    b4_mv = Bus(id="b4_mv")
    Switch(id="sw", bus1=b2_mv, bus2=b4_mv)
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv, b4_mv):
        assert bus.nominal_voltage == Q_(20_000, "V")
        assert bus.min_voltage_level is None
        assert bus.min_voltage is None
        assert bus.max_voltage_level == Q_(1.06, "")
        assert bus.max_voltage == Q_(21_200, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.nominal_voltage == Q_(400, "V")
        assert bus.min_voltage_level == Q_(0.915, "")
        assert bus.max_voltage_level == Q_(1.085, "")
        assert bus.min_voltage == Q_(366, "V")
        assert bus.max_voltage == Q_(434, "V")

    # Let's add a MV loop; does it still work?
    Line("l3_mv", b1_mv, b3_mv, length=1, parameters=lp_mv)
    b1_mv.min_voltage_level = 0.94
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv, b4_mv):
        assert bus.nominal_voltage == Q_(20_000, "V")
        assert bus.min_voltage_level == Q_(0.94, "")
        assert bus.min_voltage == Q_(18_800, "V")
        assert bus.max_voltage_level == Q_(1.06, "")
        assert bus.max_voltage == Q_(21_200, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.nominal_voltage == Q_(400, "V")
        assert bus.min_voltage_level == Q_(0.915, "")
        assert bus.max_voltage_level == Q_(1.085, "")
        assert bus.min_voltage == Q_(366, "V")
        assert bus.max_voltage == Q_(434, "V")


def test_get_connected_buses():
    b1_mv = Bus(id="b1_mv")
    b2_mv = Bus(id="b2_mv")
    b3_mv = Bus(id="b3_mv")
    b4_mv = Bus(id="b4_mv")
    b1_lv = Bus(id="b1_lv")
    b2_lv = Bus(id="b2_lv")
    b3_lv = Bus(id="b3_lv")

    lp_mv = LineParameters(id="lp_mv", z_line=1.0, y_shunt=0.1)
    lp_lv = LineParameters(id="lp_lv", z_line=1.0)
    tp = TransformerParameters.from_catalogue(name="SE Minera A0Ak 100kVA 15/20kV(20) 410V Dyn11")

    Line(id="l1_mv", bus1=b1_mv, bus2=b2_mv, length=1.5, parameters=lp_mv)
    Line(id="l2_mv", bus1=b2_mv, bus2=b3_mv, length=2, parameters=lp_mv)
    Line(id="l3_mv", bus1=b2_mv, bus2=b4_mv, length=0.5, parameters=lp_mv)  # creates a loop
    Switch(id="sw_mv", bus1=b3_mv, bus2=b4_mv)
    Transformer(id="tr", bus_hv=b3_mv, bus_lv=b1_lv, parameters=tp)
    Line(id="l1_lv", bus1=b1_lv, bus2=b2_lv, length=1, parameters=lp_lv)
    Switch(id="sw_lv", bus1=b2_lv, bus2=b3_lv)

    VoltageSource(id="s_mv", bus=b1_mv, voltage=20_000)

    PowerLoad(id="pl1_mv", bus=b2_mv, power=30e3)
    PowerLoad(id="pl2_mv", bus=b3_mv, power=30e3)
    PowerLoad(id="pl1_lv", bus=b1_lv, power=3e3)
    PowerLoad(id="pl2_lv", bus=b2_lv, power=3e3)

    mv_buses = (b1_mv, b2_mv, b3_mv, b4_mv)
    mv_bus_ids = sorted(b.id for b in mv_buses)
    lv_buses = (b1_lv, b2_lv, b3_lv)
    lv_bus_ids = sorted(b.id for b in lv_buses)
    for mvb in mv_buses:
        assert sorted(mvb.get_connected_buses()) == mv_bus_ids
    for lvb in lv_buses:
        assert sorted(lvb.get_connected_buses()) == lv_bus_ids
