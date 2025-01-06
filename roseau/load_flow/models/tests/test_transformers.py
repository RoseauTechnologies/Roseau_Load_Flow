import numpy as np
import pytest

from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow import PositiveSequence as PosSeq
from roseau.load_flow.models import Bus, Transformer, TransformerParameters


def test_max_power():
    tp = TransformerParameters.from_catalogue(name="FT 100kVA 15/20kV(20) 400V Dyn11")
    assert tp.sn == Q_(100, "kVA")

    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abc")
    transformer = Transformer(id="transformer", bus1=bus1, bus2=bus2, parameters=tp, max_loading=1)
    assert transformer.sn == Q_(100, "kVA")
    assert transformer.max_power == Q_(100, "kVA")

    transformer.max_loading = 0.5
    assert transformer.sn == Q_(100, "kVA")
    assert transformer.max_power == Q_(50, "kVA")


def test_max_loading():
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abc")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", psc=1350.0, p0=145.0, i0=1.8 / 100, ulv=400, uhv=20000, sn=50 * 1e3, vsc=4 / 100, vg="yzn11"
    )
    transformer = Transformer(id="transformer", bus1=bus1, bus2=bus2, parameters=tp)

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
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abcn")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", psc=1350.0, p0=145.0, i0=1.8 / 100, ulv=400, uhv=20000, sn=50 * 1e3, vsc=4 / 100, vg="yzn11"
    )
    transformer = Transformer(id="transformer", bus1=bus1, bus2=bus2, parameters=tp)

    bus1._res_potentials = 20_000 * PosSeq
    bus2._res_potentials = np.concatenate([230 * PosSeq, [0]])
    transformer._res_currents = 0.8 * PosSeq, np.concatenate([-65 * PosSeq, [0]])

    # Default value
    assert transformer.max_loading == Q_(1, "")
    assert transformer.res_violated is False

    # No constraint violated
    transformer.max_loading = 1
    assert transformer.res_violated is False
    np.testing.assert_allclose(transformer.res_loading.m, 0.8 * 20 * 3 / 50)

    # Two violations
    transformer.max_loading = 4 / 5
    assert transformer.res_violated is True
    np.testing.assert_allclose(transformer.res_loading.m, 0.8 * 20 * 3 / 50)

    # Primary side violation
    transformer.max_loading = Q_(45, "%")
    assert transformer.res_violated is True
    np.testing.assert_allclose(transformer.res_loading.m, 0.8 * 20 * 3 / 50)

    # Secondary side violation
    transformer.max_loading = 1
    transformer._res_currents = 0.8 * PosSeq, np.concatenate([-80 * PosSeq, [0]])
    assert transformer.res_violated is True
    np.testing.assert_allclose(transformer.res_loading.m, 80 * 230 * 3 / 50_000)


def test_transformer_results():
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abcn")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", psc=1350, p0=145, i0=0.018, ulv=400, uhv=20e3, sn=50e3, vsc=0.04, vg="yzn11"
    )
    transformer = Transformer(id="transformer", bus1=bus1, bus2=bus2, parameters=tp)

    bus1._res_potentials = 20_000 * PosSeq
    bus2._res_potentials = np.concatenate([230 * PosSeq, [0]])
    transformer._res_currents = 0.8 * PosSeq, np.concatenate([-65 * PosSeq, [0]])

    res_p1, res_p2 = (p.m for p in transformer.res_powers)

    np.testing.assert_allclose(res_p1, transformer.res_potentials[0].m * transformer.res_currents[0].m.conj())
    np.testing.assert_allclose(res_p2, transformer.res_potentials[1].m * transformer.res_currents[1].m.conj())

    expected_total_losses = res_p1[0] + res_p1[1] + res_p1[2] + res_p2[0] + res_p2[1] + res_p2[2] + res_p2[3]
    actual_total_losses = transformer.res_power_losses.m
    assert np.isscalar(actual_total_losses)
    np.testing.assert_allclose(actual_total_losses, expected_total_losses)


def test_brought_out_neutral():
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")

    tp1 = TransformerParameters("tp1", vg="Yd5", uhv=60e3, ulv=20e3, sn=1000e3, z2=0.01, ym=0.01j)
    tp2 = TransformerParameters("tp2", vg="Dy11", uhv=20e3, ulv=400, sn=100e3, z2=0.01, ym=0.01j)

    # Correct behavior when phases are not specified
    tr1 = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp1)
    assert tr1.phases1 == "abc"
    tr2 = Transformer(id="tr2", bus1=bus1, bus2=bus2, parameters=tp2)
    assert tr2.phases2 == "abc"

    # Warn on old behavior
    with pytest.warns(
        FutureWarning,
        match=(
            r"Transformer 'tr3' with vector group 'Yd5' does not have a brought out neutral on the "
            r"HV side. The neutral phase 'n' is ignored. If you meant to use a brought out neutral, "
            r"use vector group 'YNd5'. This will raise an error in the future."
        ),
    ):
        tr3 = Transformer(id="tr3", bus1=bus1, bus2=bus2, parameters=tp1, phases1="abcn", phases2="abc")
    assert tr3.phases1 == "abc"
    with pytest.warns(
        FutureWarning,
        match=(
            r"Transformer 'tr4' with vector group 'Dy11' does not have a brought out neutral on the "
            r"LV side. The neutral phase 'n' is ignored. If you meant to use a brought out neutral, "
            r"use vector group 'Dyn11'. This will raise an error in the future."
        ),
    ):
        tr4 = Transformer(id="tr4", bus1=bus1, bus2=bus2, parameters=tp2, phases1="abc", phases2="abcn")
    assert tr4.phases2 == "abc"
