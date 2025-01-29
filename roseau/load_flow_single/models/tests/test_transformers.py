import numpy as np
import pytest

from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_single.models import Bus, Transformer, TransformerParameters


def test_max_power():
    tp = TransformerParameters.from_catalogue(name="FT 100kVA 15/20kV(20) 400V Dyn11")
    assert tp.sn == Q_(100, "kVA")

    bus_hv = Bus(id="bus_hv")
    bus_lv = Bus(id="bus_lv")
    transformer = Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp, max_loading=1)
    assert transformer.sn == Q_(100, "kVA")
    assert transformer.max_power == Q_(100, "kVA")

    transformer.max_loading = 0.5
    assert transformer.sn == Q_(100, "kVA")
    assert transformer.max_power == Q_(50, "kVA")


def test_max_loading():
    bus_hv = Bus(id="bus_hv")
    bus_lv = Bus(id="bus_lv")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", vg="Yzn11", sn=50e3, uhv=20e3, ulv=400, p0=145, i0=0.018, psc=1350, vsc=0.04
    )
    transformer = Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp)

    # Value must be positive
    with pytest.raises(RoseauLoadFlowException) as e:
        transformer.max_loading = -1
    assert e.value.msg == "Maximum loading must be positive: -1 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        transformer.max_loading = 0
    assert e.value.msg == "Maximum loading must be positive: 0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE


def test_res_violated():
    bus_hv = Bus(id="bus_hv")
    bus_lv = Bus(id="bus_lv")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", vg="Yzn11", sn=50e3, uhv=20e3, ulv=400, p0=145, i0=0.018, psc=1350, vsc=0.04
    )
    transformer = Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp)

    transformer._res_voltages = (20e3 + 0j), (400 + 0j)
    transformer._res_currents = (1 + 0j), (-29 + 0j)  # 69% loading primary, 40% loading secondary

    # Default value
    assert transformer.max_loading == Q_(1, "")
    assert transformer.res_violated is False

    # No constraint violated
    transformer.max_loading = 1
    assert transformer.res_violated is False
    assert np.allclose(transformer.res_loading, 1.0 * 20 * np.sqrt(3) / 50)

    # Two violations
    transformer.max_loading = 0.3
    assert transformer.res_violated is True
    assert np.allclose(transformer.res_loading, 1.0 * 20 * np.sqrt(3) / 50)

    # Primary side violation
    transformer.max_loading = Q_(50, "%")
    assert transformer.res_violated is True
    assert np.allclose(transformer.res_loading, 1.0 * 20 * np.sqrt(3) / 50)

    # Secondary side violation
    transformer.max_loading = 1
    transformer._res_currents = 1.0, -87.0  # 69% loading primary, 120% loading secondary
    assert transformer.res_violated is True
    assert np.allclose(transformer.res_loading, 87 * 400 * np.sqrt(3) / 50_000)


def test_transformer_results():
    bus_hv = Bus(id="bus_hv")
    bus_lv = Bus(id="bus_lv")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", vg="Yzn11", sn=50e3, uhv=20e3, ulv=400, p0=145, i0=0.018, psc=1350, vsc=0.04
    )
    tr = Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp)

    tr._res_voltages = 20e3 + 0j, 400 + 0j
    tr._res_currents = 0.8 + 0j, -65 + 0j

    p_hv, p_lv = (p.m for p in tr.res_powers)

    np.testing.assert_allclose(p_hv, tr.res_voltages[0].m * tr.res_currents[0].m.conjugate() * np.sqrt(3.0))
    np.testing.assert_allclose(p_lv, tr.res_voltages[1].m * tr.res_currents[1].m.conjugate() * np.sqrt(3.0))

    expected_total_losses = p_hv + p_lv
    actual_total_losses = tr.res_power_losses.m
    assert np.isscalar(actual_total_losses)
    np.testing.assert_allclose(actual_total_losses, expected_total_losses)

    # Transformer HV aliases
    np.testing.assert_allclose(tr.res_current_hv.m, tr.res_currents[0].m)
    np.testing.assert_allclose(tr.res_voltage_hv.m, tr.res_voltages[0].m)
    np.testing.assert_allclose(tr.res_power_hv.m, tr.res_powers[0].m)

    # Transformer LV aliases
    np.testing.assert_allclose(tr.res_current_lv.m, tr.res_currents[1].m)
    np.testing.assert_allclose(tr.res_voltage_lv.m, tr.res_voltages[1].m)
    np.testing.assert_allclose(tr.res_power_lv.m, tr.res_powers[1].m)
