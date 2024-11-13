import numpy as np
import pandas as pd
import pytest

from roseau.load_flow import (
    Q_,
    Bus,
    ElectricalNetwork,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    RoseauLoadFlowException,
    RoseauLoadFlowExceptionCode,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)


def test_bus_potentials_of_phases():
    bus = Bus("bus", phases="abcn")
    bus._res_potentials = np.array([1, 2, 3, 4], dtype=np.complex128)

    assert np.allclose(bus._get_potentials_of("abcn", warning=False), [1, 2, 3, 4])
    assert isinstance(bus._get_potentials_of("abcn", warning=False), np.ndarray)

    assert np.allclose(bus._get_potentials_of("abc", warning=False), [1, 2, 3])
    assert np.allclose(bus._get_potentials_of("ca", warning=False), [3, 1])
    assert np.allclose(bus._get_potentials_of("n", warning=False), [4])
    assert np.allclose(bus._get_potentials_of("", warning=False), [])


def test_short_circuit():
    bus = Bus(id="bus", phases="abc")

    # Bad parameters
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a", "n")
    assert "Phase 'n' is not in the phases" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("n", "a")
    assert "Phase 'n' is not in the phases" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a", "a")
    assert "some phases are duplicated" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a")
    assert e.value.msg == (
        "For the short-circuit on bus 'bus', expected at least two phases or a phase and a ground. "
        "Only phase 'a' is given."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE

    assert not bus._short_circuits
    bus.add_short_circuit("c", "a", "b")
    assert bus._short_circuits[0]["phases"] == ["c", "a", "b"]
    assert bus._short_circuits[0]["ground"] is None

    # Dict methods
    vn = 400 / np.sqrt(3)
    _ = VoltageSource("vs", bus=bus, voltages=vn)
    _ = PotentialRef("pref", element=bus)
    en = ElectricalNetwork.from_element(bus)
    en2 = ElectricalNetwork.from_dict(en.to_dict())
    assert en2.buses["bus"]._short_circuits[0]["phases"] == ["c", "a", "b"]
    assert en2.buses["bus"]._short_circuits[0]["ground"] is None

    ground = Ground("ground")
    bus.add_short_circuit("a", ground=ground)  # ok
    assert len(bus.short_circuits) == 2

    # Cannot connect a load on a short-circuited bus
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="load", bus=bus, powers=[10, 10, 10])
    assert "is connected on bus" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT

    # Cannot short-circuit a bus with a power load
    bus = Bus("bus", phases="abc")
    assert not bus.short_circuits
    _ = PowerLoad(id="load", bus=bus, powers=[10, 10, 10])
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a", "b")
    assert "is already connected on bus" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT


def test_voltage_limits(recwarn):
    # Default values
    bus = Bus(id="bus", phases="abc")
    assert bus.nominal_voltage is None
    assert bus.min_voltage is None
    assert bus.max_voltage is None

    # Passed as arguments
    bus = Bus(id="bus", phases="abc", nominal_voltage=400, min_voltage_level=0.95, max_voltage_level=1.05)
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
    bus.nominal_voltage = None
    bus.min_voltage_level = None
    bus.max_voltage_level = None
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
        bus.nominal_voltage = na
        bus.min_voltage_level = na
        bus.max_voltage_level = na
        assert bus.nominal_voltage is None
        assert bus.min_voltage_level is None
        assert bus.max_voltage_level is None
        assert bus.min_voltage is None
        assert bus.max_voltage is None

    # Min/Max voltage values defined without nominal voltage are useless
    bus.nominal_voltage = None
    bus.min_voltage_level = None
    bus.max_voltage_level = None
    recwarn.clear()
    bus.min_voltage_level = 0.95
    assert len(recwarn) == 1
    assert (
        recwarn[0].message.args[0]
        == "The min voltage level of the bus 'bus' is useless without a nominal voltage. Please define a nominal "
        "voltage for this bus."
    )
    assert bus.min_voltage_level == Q_(0.95, "")
    assert bus.min_voltage is None
    recwarn.clear()
    bus.max_voltage_level = 1.05
    assert len(recwarn) == 1
    assert (
        recwarn[0].message.args[0]
        == "The max voltage level of the bus 'bus' is useless without a nominal voltage. Please define a nominal "
        "voltage for this bus."
    )
    assert bus.max_voltage_level == Q_(1.05, "")
    assert bus.max_voltage is None

    # Erasing a nominal voltage with a min or max voltage level emits a warning
    bus.nominal_voltage = Q_(400, "V")
    recwarn.clear()
    bus.nominal_voltage = None
    assert len(recwarn) == 1
    assert (
        recwarn[0].message.args[0]
        == "The nominal voltage of the bus 'bus' is required to use `min_voltage_level` and `max_voltage_level`."
    )
    bus.nominal_voltage = Q_(400, "V")
    bus.min_voltage_level = None
    bus.max_voltage_level = None
    recwarn.clear()
    bus.nominal_voltage = None
    assert len(recwarn) == 0

    # Bad values
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


def test_res_voltages():
    # With a neutral
    bus = Bus(id="bus", phases="abcn")
    direct_seq = np.exp([0, -2 / 3 * np.pi * 1j, 2 / 3 * np.pi * 1j])
    direct_seq_neutral = np.array([1, np.exp(-2 / 3 * np.pi * 1j), np.exp(2 / 3 * np.pi * 1j), 0])
    bus._res_potentials = (230 + 0j) * direct_seq_neutral

    assert np.allclose(bus.res_potentials.m, (230 + 0j) * direct_seq_neutral)
    assert np.allclose(bus.res_voltages.m, (230 + 0j) * direct_seq)
    assert bus.res_voltages_level is None
    bus.nominal_voltage = 400  # V
    assert np.allclose(bus.res_voltages_level.m, 230 / 400 * np.sqrt(3))

    # Without a neutral
    bus = Bus(id="bus", phases="abc")
    bus._res_potentials = (20_000 + 0j) * direct_seq / np.sqrt(3)

    assert np.allclose(bus.res_potentials.m, (20_000 + 0j) * direct_seq / np.sqrt(3))
    assert np.allclose(bus.res_voltages.m, (20_000 + 0j) * direct_seq * np.exp(np.pi * 1j / 6))
    assert bus.res_voltages_level is None
    bus.nominal_voltage = 20_000  # V
    assert np.allclose(bus.res_voltages_level.m, 1.0)


def test_res_violated():
    bus = Bus(id="bus", phases="abc")
    direct_seq = np.exp([0, -2 / 3 * np.pi * 1j, 2 / 3 * np.pi * 1j])
    bus._res_potentials = (230 + 0j) * direct_seq

    # No limits
    assert bus.res_violated is None

    # Only a nominal voltage
    bus.nominal_voltage = 400
    assert bus.res_violated is None

    # Only min voltage
    bus.min_voltage_level = 0.9
    assert bus.res_violated is False
    bus.min_voltage_level = 1.1
    assert bus.res_violated is True

    # Only max voltage
    bus.min_voltage_level = None
    bus.max_voltage_level = 1.1
    assert bus.res_violated is False
    bus.max_voltage_level = 0.9
    assert bus.res_violated is True

    # Both min and max voltage
    # min <= v <= max
    bus.min_voltage_level = 0.9
    bus.max_voltage_level = 1.1
    assert bus.res_violated is False
    # v < min
    bus.min_voltage_level = 1.1
    assert bus.res_violated is True
    # v > max
    bus.min_voltage_level = 0.9
    bus.max_voltage_level = 0.9
    assert bus.res_violated is True


def test_propagate_limits():  # noqa: C901
    b1_mv = Bus(id="b1_mv", phases="abc")
    b2_mv = Bus(id="b2_mv", phases="abc")
    b3_mv = Bus(id="b3_mv", phases="abc")
    b1_lv = Bus(id="b1_lv", phases="abcn")
    b2_lv = Bus(id="b2_lv", phases="abcn")

    PotentialRef(id="pref_mv", element=b1_mv)
    g = Ground("g")
    PotentialRef(id="pref_lv", element=g)

    lp_mv = LineParameters(id="lp_mv", z_line=np.eye(3), y_shunt=0.1 * np.eye(3))
    lp_lv = LineParameters(id="lp_lv", z_line=np.eye(4))
    tp = TransformerParameters.from_catalogue(name="SE_Minera_A0Ak_100kVA", manufacturer="SE")

    Line(id="l1_mv", bus1=b1_mv, bus2=b2_mv, length=1.5, parameters=lp_mv, ground=g)
    Line(id="l2_mv", bus1=b2_mv, bus2=b3_mv, length=2, parameters=lp_mv, ground=g)
    Transformer(id="tr", bus1=b3_mv, bus2=b1_lv, parameters=tp)
    Line(id="l1_lv", bus1=b1_lv, bus2=b2_lv, length=1, parameters=lp_lv)

    VoltageSource(id="s_mv", bus=b1_mv, voltages=20_000)

    PowerLoad(id="pl1_mv", bus=b2_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad(id="pl2_mv", bus=b3_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad(id="pl1_lv", bus=b1_lv, powers=[1e3, 1e3, 1e3])
    PowerLoad(id="pl2_lv", bus=b2_lv, powers=[1e3, 1e3, 1e3])

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
    b4_mv = Bus(id="b4_mv", phases="abc")
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
    Line("l3_mv", b1_mv, b3_mv, length=1, parameters=lp_mv, ground=g)
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
    b1_mv = Bus(id="b1_mv", phases="abc")
    b2_mv = Bus(id="b2_mv", phases="abc")
    b3_mv = Bus(id="b3_mv", phases="abc")
    b4_mv = Bus(id="b4_mv", phases="abc")
    b1_lv = Bus(id="b1_lv", phases="abcn")
    b2_lv = Bus(id="b2_lv", phases="abcn")
    b3_lv = Bus(id="b3_lv", phases="abcn")

    PotentialRef(id="pref_mv", element=b1_mv)
    g = Ground("g")
    PotentialRef(id="pref_lv", element=g)

    lp_mv = LineParameters(id="lp_mv", z_line=np.eye(3), y_shunt=0.1 * np.eye(3))
    lp_lv = LineParameters(id="lp_lv", z_line=np.eye(4))
    tp = TransformerParameters.from_catalogue(name="SE_Minera_A0Ak_100kVA", manufacturer="SE")

    Line(id="l1_mv", bus1=b1_mv, bus2=b2_mv, length=1.5, parameters=lp_mv, ground=g)
    Line(id="l2_mv", bus1=b2_mv, bus2=b3_mv, length=2, parameters=lp_mv, ground=g)
    Line(id="l3_mv", bus1=b2_mv, bus2=b4_mv, length=0.5, parameters=lp_mv, ground=g)  # creates a loop
    Switch(id="sw_mv", bus1=b3_mv, bus2=b4_mv)
    Transformer(id="tr", bus1=b3_mv, bus2=b1_lv, parameters=tp)
    Line(id="l1_lv", bus1=b1_lv, bus2=b2_lv, length=1, parameters=lp_lv)
    Switch(id="sw_lv", bus1=b2_lv, bus2=b3_lv)

    VoltageSource(id="s_mv", bus=b1_mv, voltages=20_000)

    PowerLoad(id="pl1_mv", bus=b2_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad(id="pl2_mv", bus=b3_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad(id="pl1_lv", bus=b1_lv, powers=[1e3, 1e3, 1e3])
    PowerLoad(id="pl2_lv", bus=b2_lv, powers=[1e3, 1e3, 1e3])

    mv_buses = (b1_mv, b2_mv, b3_mv, b4_mv)
    mv_bus_ids = sorted(b.id for b in mv_buses)
    lv_buses = (b1_lv, b2_lv, b3_lv)
    lv_bus_ids = sorted(b.id for b in lv_buses)
    for mvb in mv_buses:
        assert sorted(mvb.get_connected_buses()) == mv_bus_ids
    for lvb in lv_buses:
        assert sorted(lvb.get_connected_buses()) == lv_bus_ids


def test_res_voltage_unbalance():
    bus = Bus(id="b3", phases="abc")

    va = 230 + 0j
    vb = 230 * np.exp(4j * np.pi / 3)
    vc = 230 * np.exp(2j * np.pi / 3)

    # Balanced system
    bus._res_potentials = np.array([va, vb, vc])
    assert np.isclose(bus.res_voltage_unbalance().magnitude, 0)

    # Unbalanced system
    bus._res_potentials = np.array([va, vb, vb])
    assert np.isclose(bus.res_voltage_unbalance().magnitude, 100)

    # With neutral
    bus = Bus(id="b3n", phases="abcn")
    bus._res_potentials = np.array([va, vb, vc, 0])
    assert np.isclose(bus.res_voltage_unbalance().magnitude, 0)
    bus._res_potentials = np.array([va, vb, vb, 0])
    assert np.isclose(bus.res_voltage_unbalance().magnitude, 100)

    # Non 3-phase bus
    bus = Bus(id="b1", phases="an")
    bus._res_potentials = np.array([va, 0])
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.res_voltage_unbalance()
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Voltage unbalance is only available for 3-phases buses, bus 'b1' has phases 'an'"
