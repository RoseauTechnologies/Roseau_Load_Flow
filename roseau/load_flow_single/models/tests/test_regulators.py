import numpy as np
import pytest

import roseau.load_flow_single as rlfs
from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode


def make_regulator(
    sn: float = 10e3,
    un: float = 400.0,
    z2: complex = 1e-4 + 0j,
    ym: complex = 1e-4j,
    u_range: float = 0.1,
    alpha: float = 100.0,
    u_ref: float = 1.0,
    max_loading: float = 1.0,
) -> rlfs.VoltageRegulator:
    bus1 = rlfs.Bus(id="bus1")
    bus2 = rlfs.Bus(id="bus2")
    rp = rlfs.RegulatorParameters(id="rp", sn=sn, un=un, z2=z2, ym=ym, u_range=u_range, alpha=alpha, config="wye")
    return rlfs.VoltageRegulator(id="reg", bus1=bus1, bus2=bus2, parameters=rp, u_ref=u_ref, max_loading=max_loading)


def test_regulator_parameters():
    # The config is required: "wye" and "closed-delta" give different results
    with pytest.raises(TypeError, match=r"missing a required (keyword-only )?argument: 'config'"):
        rlfs.RegulatorParameters("RP", sn=1e6, un=400.0, z2=1e-4, ym=0)  # type: ignore

    rp = rlfs.RegulatorParameters("RP", sn=1e6, un=400.0, z2=1e-4, ym=0, config="wye")
    assert rp.config == "wye"
    rp = rlfs.RegulatorParameters("RP", sn=1e6, un=400.0, z2=1e-4, ym=0, config="closed-delta")
    assert rp.config == "closed-delta"
    assert "config='closed-delta'" in repr(rp)

    # Serialization
    rp2 = rlfs.RegulatorParameters.from_dict(rp.to_dict())
    assert rp2.to_dict() == rp.to_dict()

    # The no-load voltage ratio of a closed delta: |a / (1 - (1 - a)·α²)|
    taps = np.array([0.9, 1.0, 1.1])
    expected = np.abs(taps / (1 - (1 - taps) * np.exp(-2j * np.pi / 3)))
    np.testing.assert_allclose(rp._no_load_voltage_ratio(taps), expected)

    # Bad values
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.RegulatorParameters("RP", sn=1e6, un=400.0, z2=1e-4, ym=0, config="open delta")  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONFIG
    assert e.value.msg == (
        "Invalid config 'open delta' for regulator parameters 'RP'. Allowed configs are: ['closed-delta', 'wye']."
    )
    for kwargs in ({"u_range": 0.0}, {"u_range": 1.0}, {"alpha": 0.0}, {"z2": 0.0}, {"sn": 0.0}, {"un": -1.0}):
        params = {"sn": 1e6, "un": 400.0, "z2": 1e-4, "ym": 0, "config": "wye"} | kwargs
        with pytest.raises(RoseauLoadFlowException) as e:
            rlfs.RegulatorParameters("RP", **params)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS


def test_update_parameters():
    reg = make_regulator()
    rlfs.VoltageSource(id="src", bus=reg.bus1, voltage=400.0)
    en = rlfs.ElectricalNetwork.from_element(reg.bus1)

    # Same config and range, other impedances: the C++ model is updated in place
    cy_element = reg._cy_element
    reg.parameters = rlfs.RegulatorParameters("RP2", sn=10e3, un=404.0, z2=1e-3, ym=0, alpha=100.0, config="wye")
    assert reg._cy_element is cy_element
    assert set(en._parameters["regulator"]) == {"RP2"}

    # Another config: the C++ model is rebuilt
    reg.parameters = rlfs.RegulatorParameters("RP3", sn=10e3, un=400.0, z2=1e-3, ym=0, config="closed-delta")
    assert reg._cy_element is not cy_element
    assert set(en._parameters["regulator"]) == {"RP3"}

    # Another range: the C++ model is rebuilt
    cy_element = reg._cy_element
    rp4 = rlfs.RegulatorParameters("RP4", sn=10e3, un=400.0, z2=1e-3, ym=0, u_range=0.05, config="closed-delta")
    reg.parameters = rp4
    assert reg._cy_element is not cy_element
    assert set(en._parameters["regulator"]) == {"RP4"}


def test_max_power():
    reg = make_regulator(sn=10e3)
    assert reg.sn == Q_(10e3, "VA")
    assert reg.max_power == Q_(10e3, "VA")

    reg.max_loading = 0.5
    assert reg.sn == Q_(10e3, "VA")
    assert reg.max_power == Q_(5e3, "VA")


def test_max_loading():
    reg = make_regulator()

    with pytest.raises(RoseauLoadFlowException) as e:
        reg.max_loading = -1
    assert e.value.msg == "Maximum loading must be positive: -1 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        reg.max_loading = 0
    assert e.value.msg == "Maximum loading must be positive: 0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE


def test_u_ref_validation():
    reg = make_regulator()

    with pytest.raises(RoseauLoadFlowException) as e:
        reg.u_ref = -1.0
    assert e.value.msg == "u_ref must be positive: -1.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES

    with pytest.raises(RoseauLoadFlowException) as e:
        reg.u_ref = 0.0
    assert e.value.msg == "u_ref must be positive: 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES

    with pytest.warns(UserWarning, match=r"got very high u_ref 25.00 p.u"):
        reg.u_ref = 25.0


def test_res_violated():
    sn = 10e3
    reg = make_regulator(sn=sn)

    reg.side1._res_voltage = 400.0 + 0j
    reg.side2._res_voltage = 400.0 + 0j
    reg.side1._res_current = 10.0 + 0j  # loading = 400 * 10 * sqrt(3) / sn ≈ 0.693
    reg.side2._res_current = -10.0 + 0j

    # Default max_loading = 1.0 → not violated
    assert reg.max_loading == Q_(1.0, "")
    assert reg.res_violated is False
    np.testing.assert_allclose(reg.res_loading.m, 400 * 10 * np.sqrt(3) / sn)

    # Tighter constraint → violated
    reg.max_loading = 0.5
    assert reg.res_violated is True
    np.testing.assert_allclose(reg.res_loading.m, 400 * 10 * np.sqrt(3) / sn)

    # LV side dominates when its current is larger
    reg.max_loading = 1.0
    reg.side1._res_current = 5.0 + 0j
    reg.side2._res_current = -20.0 + 0j  # loading = 400 * 20 * sqrt(3) / sn ≈ 1.386
    assert reg.res_violated is True
    np.testing.assert_allclose(reg.res_loading.m, 400 * 20 * np.sqrt(3) / sn)

    # Percentage form works
    reg.max_loading = Q_(200, "%")
    assert reg.res_violated is False


def test_res_state():
    sn = 10e3
    reg = make_regulator(sn=sn)

    reg.side1._res_voltage = 400.0 + 0j
    reg.side2._res_voltage = 400.0 + 0j
    reg.side1._res_current = 10.0 + 0j  # loading ≈ 0.693 — below 0.75 × 1.0
    reg.side2._res_current = -10.0 + 0j

    assert reg._res_state_getter() == "normal"

    reg.side1._res_current = 12.0 + 0j  # loading ≈ 0.831 — between 0.75 and 1.0
    assert reg._res_state_getter() == "high"

    reg.side1._res_current = 16.0 + 0j  # loading ≈ 1.109 — above 1.0
    assert reg._res_state_getter() == "very-high"

    # Relaxed max_loading brings 1.109 back to "high"
    reg._max_loading = 1.2
    assert reg._res_state_getter() == "high"


def test_regulator_results():
    reg = make_regulator(sn=10e3)

    reg.side1._res_voltage = 400.0 + 0j
    reg.side2._res_voltage = 398.0 + 0j
    reg.side1._res_current = 8.0 + 2.0j
    reg.side2._res_current = -8.0 - 2.0j

    p1 = reg.side1.res_power.m
    p2 = reg.side2.res_power.m

    np.testing.assert_allclose(p1, reg.side1.res_voltage.m * reg.side1.res_current.m.conjugate() * np.sqrt(3.0))
    np.testing.assert_allclose(p2, reg.side2.res_voltage.m * reg.side2.res_current.m.conjugate() * np.sqrt(3.0))
    np.testing.assert_allclose(reg.res_losses.m, p1 + p2)
