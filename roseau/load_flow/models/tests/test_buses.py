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
    bus._res_potentials = [1, 2, 3, 4]

    assert np.allclose(bus._get_potentials_of("abcn", warning=False), [1, 2, 3, 4])
    assert isinstance(bus._get_potentials_of("abcn", warning=False), np.ndarray)

    assert np.allclose(bus._get_potentials_of("abc", warning=False), [1, 2, 3])
    assert np.allclose(bus._get_potentials_of("ca", warning=False), [3, 1])
    assert np.allclose(bus._get_potentials_of("n", warning=False), [4])
    assert np.allclose(bus._get_potentials_of("", warning=False), [])


def test_short_circuit():
    bus = Bus("bus", phases="abc")

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
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    _ = VoltageSource("vs", bus=bus, voltages=voltages)
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


def test_voltage_limits():
    # Default values
    bus = Bus("bus", phases="abc")
    assert bus.min_voltage is None
    assert bus.max_voltage is None

    # Passed as arguments
    bus = Bus("bus", phases="abc", min_voltage=350, max_voltage=420)
    assert bus.min_voltage == Q_(350, "V")
    assert bus.max_voltage == Q_(420, "V")

    # Can be set to a real number
    bus.min_voltage = 350.0
    bus.max_voltage = 420.0
    assert bus.min_voltage == Q_(350.0, "V")
    assert bus.max_voltage == Q_(420.0, "V")

    # Can be reset to None
    bus.min_voltage = None
    bus.max_voltage = None
    assert bus.min_voltage is None
    assert bus.max_voltage is None

    # Can be set to a Quantity
    bus.min_voltage = Q_(19, "kV")
    bus.max_voltage = Q_(21, "kV")
    assert bus.min_voltage == Q_(19_000, "V")
    assert bus.max_voltage == Q_(21_000, "V")

    # NaNs are converted to None
    for na in (np.nan, float("nan"), pd.NA):
        bus.min_voltage = na
        bus.max_voltage = na
        assert bus.min_voltage is None
        assert bus.max_voltage is None

    # Bad values
    bus.min_voltage = 220
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.max_voltage = 200
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == "Cannot set max voltage of bus 'bus' to 200 V as it is lower than its min voltage (220 V)."
    bus.max_voltage = 240
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.min_voltage = 250
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == "Cannot set min voltage of bus 'bus' to 250 V as it is higher than its max voltage (240 V)."


def test_res_violated():
    bus = Bus("bus", phases="abc")
    direct_seq = np.exp([0, -2 / 3 * np.pi * 1j, 2 / 3 * np.pi * 1j])
    bus._res_potentials = 230 * direct_seq

    # No limits
    assert bus.res_violated is None

    # Only min voltage
    bus.min_voltage = 350
    assert bus.res_violated is False
    bus.min_voltage = 450
    assert bus.res_violated is True

    # Only max voltage
    bus.min_voltage = None
    bus.max_voltage = 450
    assert bus.res_violated is False
    bus.max_voltage = 350
    assert bus.res_violated is True

    # Both min and max voltage
    # min <= v <= max
    bus.min_voltage = 350
    bus.max_voltage = 450
    assert bus.res_violated is False
    # v < min
    bus.min_voltage = 450
    assert bus.res_violated is True
    # v > max
    bus.min_voltage = 350
    bus.max_voltage = 350
    assert bus.res_violated is True


def test_propagate_limits():  # noqa: C901
    b1_mv = Bus("b1_mv", phases="abc")
    b2_mv = Bus("b2_mv", phases="abc")
    b3_mv = Bus("b3_mv", phases="abc")
    b1_lv = Bus("b1_lv", phases="abcn")
    b2_lv = Bus("b2_lv", phases="abcn")

    PotentialRef("pref_mv", element=b1_mv)
    g = Ground("g")
    PotentialRef("pref_lv", element=g)

    lp_mv = LineParameters("lp_mv", z_line=np.eye(3), y_shunt=0.1 * np.eye(3))
    lp_lv = LineParameters("lp_lv", z_line=np.eye(4))
    tp = TransformerParameters.from_catalogue(name="SE_Minera_A0Ak_100kVA", manufacturer="SE")

    Line("l1_mv", b1_mv, b2_mv, length=1.5, parameters=lp_mv, ground=g)
    Line("l2_mv", b2_mv, b3_mv, length=2, parameters=lp_mv, ground=g)
    Transformer("tr", b3_mv, b1_lv, parameters=tp)
    Line("l1_lv", b1_lv, b2_lv, length=1, parameters=lp_lv)

    voltages = 20_000 * np.exp([0, -2 / 3 * np.pi * 1j, 2 / 3 * np.pi * 1j])
    VoltageSource("s_mv", bus=b1_mv, voltages=voltages)

    PowerLoad("pl1_mv", bus=b2_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad("pl2_mv", bus=b3_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad("pl1_lv", bus=b1_lv, powers=[1e3, 1e3, 1e3])
    PowerLoad("pl2_lv", bus=b2_lv, powers=[1e3, 1e3, 1e3])

    # All buses have None as min and max voltage
    for bus in (b1_mv, b2_mv, b3_mv, b1_lv, b2_lv):
        assert bus.min_voltage is None
        assert bus.max_voltage is None

    # Set min and max voltage of b1_mv
    b1_mv.min_voltage = 19_000
    b1_mv.max_voltage = 21_000
    # propagate MV voltage limits
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.min_voltage == Q_(19_000, "V")
        assert bus.max_voltage == Q_(21_000, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.min_voltage is None
        assert bus.max_voltage is None

    # Set min and max voltage of b1_lv
    b1_lv.min_voltage = 217
    b1_lv.max_voltage = 253
    b1_lv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.min_voltage == Q_(19_000, "V")
        assert bus.max_voltage == Q_(21_000, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.min_voltage == Q_(217, "V")
        assert bus.max_voltage == Q_(253, "V")

    # Reset min MV voltage limits only
    b1_mv.min_voltage = None
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.min_voltage is None
        assert bus.max_voltage == Q_(21_000, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.min_voltage == Q_(217, "V")
        assert bus.max_voltage == Q_(253, "V")

    # Error, different max voltage limits
    b1_mv.max_voltage = 21_005
    with pytest.raises(RoseauLoadFlowException) as e:
        b1_mv.propagate_limits()
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    assert e.value.msg == (
        "Cannot propagate the maximum voltage (21005 V) of bus 'b1_mv' to bus 'b2_mv' with "
        "different maximum voltage (21000 V)."
    )

    # The limits are not changed after the error
    for bus in (b2_mv, b3_mv):
        assert bus.min_voltage is None
        assert bus.max_voltage == Q_(21_000, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.min_voltage == Q_(217, "V")
        assert bus.max_voltage == Q_(253, "V")

    # It is okay to propagate with different limits if force=True
    b1_mv.propagate_limits(force=True)
    for bus in (b1_mv, b2_mv, b3_mv):
        assert bus.min_voltage is None
        assert bus.max_voltage == Q_(21_005, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.min_voltage == Q_(217, "V")
        assert bus.max_voltage == Q_(253, "V")

    # What if there is a switch?
    b4_mv = Bus("b4_mv", phases="abc")
    Switch("sw", b2_mv, b4_mv)
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv, b4_mv):
        assert bus.min_voltage is None
        assert bus.max_voltage == Q_(21_005, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.min_voltage == Q_(217, "V")
        assert bus.max_voltage == Q_(253, "V")

    # Let's add a MV loop; does it still work?
    Line("l3_mv", b1_mv, b3_mv, length=1, parameters=lp_mv, ground=g)
    b1_mv.min_voltage = 19_000
    b1_mv.propagate_limits()
    for bus in (b1_mv, b2_mv, b3_mv, b4_mv):
        assert bus.min_voltage == Q_(19_000, "V")
        assert bus.max_voltage == Q_(21_005, "V")
    for bus in (b1_lv, b2_lv):
        assert bus.min_voltage == Q_(217, "V")
        assert bus.max_voltage == Q_(253, "V")


def test_get_connected_buses():
    b1_mv = Bus("b1_mv", phases="abc")
    b2_mv = Bus("b2_mv", phases="abc")
    b3_mv = Bus("b3_mv", phases="abc")
    b4_mv = Bus("b4_mv", phases="abc")
    b1_lv = Bus("b1_lv", phases="abcn")
    b2_lv = Bus("b2_lv", phases="abcn")
    b3_lv = Bus("b3_lv", phases="abcn")

    PotentialRef("pref_mv", element=b1_mv)
    g = Ground("g")
    PotentialRef("pref_lv", element=g)

    lp_mv = LineParameters("lp_mv", z_line=np.eye(3), y_shunt=0.1 * np.eye(3))
    lp_lv = LineParameters("lp_lv", z_line=np.eye(4))
    tp = TransformerParameters.from_catalogue(name="SE_Minera_A0Ak_100kVA", manufacturer="SE")

    Line("l1_mv", b1_mv, b2_mv, length=1.5, parameters=lp_mv, ground=g)
    Line("l2_mv", b2_mv, b3_mv, length=2, parameters=lp_mv, ground=g)
    Line("l3_mv", b2_mv, b4_mv, length=0.5, parameters=lp_mv, ground=g)  # creates a loop
    Switch("sw_mv", b3_mv, b4_mv)
    Transformer("tr", b3_mv, b1_lv, parameters=tp)
    Line("l1_lv", b1_lv, b2_lv, length=1, parameters=lp_lv)
    Switch("sw_lv", b2_lv, b3_lv)

    voltages = 20_000 * np.exp([0, -2 / 3 * np.pi * 1j, 2 / 3 * np.pi * 1j])
    VoltageSource("s_mv", bus=b1_mv, voltages=voltages)

    PowerLoad("pl1_mv", bus=b2_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad("pl2_mv", bus=b3_mv, powers=[10e3, 10e3, 10e3])
    PowerLoad("pl1_lv", bus=b1_lv, powers=[1e3, 1e3, 1e3])
    PowerLoad("pl2_lv", bus=b2_lv, powers=[1e3, 1e3, 1e3])

    mv_buses = (b1_mv, b2_mv, b3_mv, b4_mv)
    mv_bus_ids = sorted(b.id for b in mv_buses)
    lv_buses = (b1_lv, b2_lv, b3_lv)
    lv_bus_ids = sorted(b.id for b in lv_buses)
    for mvb in mv_buses:
        assert sorted(mvb.get_connected_buses()) == mv_bus_ids
    for lvb in lv_buses:
        assert sorted(lvb.get_connected_buses()) == lv_bus_ids


def test_res_voltage_unbalance():
    bus = Bus("b3", phases="abc")

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
    bus = Bus("b3n", phases="abcn")
    bus._res_potentials = np.array([va, vb, vc, 0])
    assert np.isclose(bus.res_voltage_unbalance().magnitude, 0)
    bus._res_potentials = np.array([va, vb, vb, 0])
    assert np.isclose(bus.res_voltage_unbalance().magnitude, 100)

    # Non 3-phase bus
    bus = Bus("b1", phases="an")
    bus._res_potentials = np.array([va, 0])
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.res_voltage_unbalance()
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Voltage unbalance is only available for 3-phases buses, bus 'b1' has phases 'an'"
