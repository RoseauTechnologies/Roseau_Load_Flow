import numpy as np
import pytest

from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow import PositiveSequence as PosSeq
from roseau.load_flow.models import Bus, Transformer, TransformerParameters


def test_max_power():
    tp = TransformerParameters.from_catalogue(name="FT 100kVA 15/20kV(20) 400V Dyn11")
    assert tp.sn == Q_(100, "kVA")

    bus_hv = Bus(id="bus_hv", phases="abc")
    bus_lv = Bus(id="bus_lv", phases="abc")
    transformer = Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp, max_loading=1)
    assert transformer.sn == Q_(100, "kVA")
    assert transformer.max_power == Q_(100, "kVA")

    transformer.max_loading = 0.5
    assert transformer.sn == Q_(100, "kVA")
    assert transformer.max_power == Q_(50, "kVA")


def test_max_loading():
    bus_hv = Bus(id="bus_hv", phases="abc")
    bus_lv = Bus(id="bus_lv", phases="abc")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", psc=1350.0, p0=145.0, i0=1.8 / 100, ulv=400, uhv=20000, sn=50 * 1e3, vsc=4 / 100, vg="yzn11"
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
    bus_hv = Bus(id="bus_hv", phases="abc")
    bus_lv = Bus(id="bus_lv", phases="abcn")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", psc=1350.0, p0=145.0, i0=1.8 / 100, ulv=400, uhv=20000, sn=50 * 1e3, vsc=4 / 100, vg="yzn11"
    )
    transformer = Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp)

    bus_hv._res_potentials = 20_000 * PosSeq
    bus_lv._res_potentials = np.concatenate([230 * PosSeq, [0]])
    transformer.side_hv._res_currents = 0.8 * PosSeq
    transformer.side_lv._res_currents = np.concatenate([-65 * PosSeq, [0]])
    transformer.side_hv._res_potentials = bus_hv._res_potentials[list(map(bus_hv.phases.index, transformer.phases_hv))]
    transformer.side_lv._res_potentials = bus_lv._res_potentials[list(map(bus_lv.phases.index, transformer.phases_lv))]

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

    # HV side violation
    transformer.max_loading = Q_(45, "%")
    assert transformer.res_violated is True
    np.testing.assert_allclose(transformer.res_loading.m, 0.8 * 20 * 3 / 50)

    # LV side violation
    transformer.max_loading = 1
    transformer.side_hv._res_currents = 0.8 * PosSeq
    transformer.side_lv._res_currents = np.concatenate([-80 * PosSeq, [0]])
    assert transformer.res_violated is True
    np.testing.assert_allclose(transformer.res_loading.m, 80 * 230 * 3 / 50_000)


def test_res_state():
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abcn")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", vg="Yzn11", sn=50e3, uhv=20e3, ulv=400, p0=145, i0=0.018, psc=1350, vsc=0.04
    )
    tr = Transformer(id="transformer", bus_hv=bus1, bus_lv=bus2, parameters=tp)

    def current(s, u):
        return s / (np.sqrt(3) * u)

    tr.side_hv._res_potentials = 20e3 / np.sqrt(3) * PosSeq
    tr.side_lv._res_potentials = 400 / np.sqrt(3) * PosSeq
    tr.side_hv._res_currents = current(30e3, 20e3) * PosSeq
    tr.side_lv._res_currents = current(-30e3, 400) * PosSeq

    assert tr._res_state_getter() == "normal"
    tr.side_hv._res_currents = current(45e3, 20e3) * PosSeq
    assert tr._res_state_getter() == "high"
    tr.side_hv._res_currents = current(60e3, 20e3) * PosSeq
    assert tr._res_state_getter() == "very-high"

    # Change max loading
    tr._max_loading = 1.2
    assert tr._res_state_getter() == "high"


def test_transformer_results():
    bus_hv = Bus(id="bus_hv", phases="abc")
    bus_lv = Bus(id="bus_lv", phases="abcn")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp", psc=1350, p0=145, i0=0.018, ulv=400, uhv=20e3, sn=50e3, vsc=0.04, vg="yzn11"
    )
    tr = Transformer(id="tr", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp)

    bus_hv._res_potentials = 20_000 * PosSeq
    bus_lv._res_potentials = np.concatenate([230 * PosSeq, [0]])
    tr.side_hv._res_currents = 0.8 * PosSeq
    tr.side_lv._res_currents = np.concatenate([-65 * PosSeq, [0]])
    tr.side_hv._res_potentials = bus_hv._res_potentials[list(map(bus_hv.phases.index, tr.phases_hv))]
    tr.side_lv._res_potentials = bus_lv._res_potentials[list(map(bus_lv.phases.index, tr.phases_lv))]

    p_hv = tr.side_hv.res_powers.m
    p_lv = tr.side_lv.res_powers.m

    np.testing.assert_allclose(p_hv, tr.side_hv.res_potentials.m * tr.side_hv.res_currents.m.conj())
    np.testing.assert_allclose(p_lv, tr.side_lv.res_potentials.m * tr.side_lv.res_currents.m.conj())

    expected_total_losses = p_hv[0] + p_hv[1] + p_hv[2] + p_lv[0] + p_lv[1] + p_lv[2] + p_lv[3]
    actual_total_losses = tr.res_power_losses.m
    assert np.isscalar(actual_total_losses)
    np.testing.assert_allclose(actual_total_losses, expected_total_losses)


def test_brought_out_neutral():
    bus_hv = Bus(id="bus_hv", phases="abcn")
    bus_lv = Bus(id="bus_lv", phases="abcn")

    tp1 = TransformerParameters("tp1", vg="Yd5", uhv=60e3, ulv=20e3, sn=1000e3, z2=0.01, ym=0.01j)
    tp2 = TransformerParameters("tp2", vg="Dy11", uhv=20e3, ulv=400, sn=100e3, z2=0.01, ym=0.01j)

    # Correct behavior when phases are not specified
    tr1 = Transformer(id="tr1", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp1)
    assert tr1.phases_hv == "abc"
    tr2 = Transformer(id="tr2", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp2)
    assert tr2.phases_lv == "abc"

    # Warn on missing brought out neutral
    with pytest.warns(
        UserWarning,
        match=(
            r"Transformer 'tr3' with vector group 'Yd5' does not have a brought out neutral on the "
            r"HV side. The neutral phase 'n' is ignored. If you meant to use a brought out neutral, "
            r"use vector group 'YNd5'."
        ),
    ):
        tr3 = Transformer(id="tr3", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp1, phases_hv="abcn", phases_lv="abc")
    assert tr3.phases_hv == "abc"
    with pytest.warns(
        UserWarning,
        match=(
            r"Transformer 'tr4' with vector group 'Dy11' does not have a brought out neutral on the "
            r"LV side. The neutral phase 'n' is ignored. If you meant to use a brought out neutral, "
            r"use vector group 'Dyn11'."
        ),
    ):
        tr4 = Transformer(id="tr4", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp2, phases_hv="abc", phases_lv="abcn")
    assert tr4.phases_lv == "abc"


def test_renamed_attributes():
    bus_hv = Bus(id="bus_hv", phases="abc")
    bus_lv = Bus(id="bus_lv", phases="abcn")
    tp = TransformerParameters("tp", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.01, ym=0.01j)
    tr = Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp, phases_hv="abc", phases_lv="abcn")

    # Old attributes
    assert tp.winding1 == "D"
    assert tp.winding2 == "yn"
    assert tp.phase_displacement == 11
    assert tr.phases1 == "abc"
    assert tr.phases2 == "abcn"
    assert tr.bus1 == bus_hv
    assert tr.bus2 == bus_lv

    # New attributes
    assert tp.whv == "D"
    assert tp.wlv == "yn"
    assert tp.clock == 11
    assert tr.phases_hv == "abc"
    assert tr.phases_lv == "abcn"
    assert tr.bus_hv == bus_hv
    assert tr.bus_lv == bus_lv


def test_deprecated_parameters():
    bus_hv = Bus(id="bus_hv", phases="abc")
    bus_lv = Bus(id="bus_lv", phases="abcn")
    tp = TransformerParameters("tp", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.01, ym=0.01j)

    with pytest.warns(
        DeprecationWarning,
        match=r"Argument 'bus1' for Transformer\(\) is deprecated. It has been renamed to 'bus_hv'",
    ):
        Transformer(id="transformer", bus1=bus_hv, bus_lv=bus_lv, parameters=tp)  # type: ignore

    with pytest.warns(
        DeprecationWarning,
        match=r"Argument 'bus2' for Transformer\(\) is deprecated. It has been renamed to 'bus_lv'",
    ):
        Transformer(id="transformer", bus_hv=bus_hv, bus2=bus_lv, parameters=tp)  # type: ignore

    with pytest.warns(
        DeprecationWarning,
        match=r"Argument 'phases1' for Transformer\(\) is deprecated. It has been renamed to 'phases_hv'",
    ):
        Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp, phases1="abc")  # type: ignore

    with pytest.warns(
        DeprecationWarning,
        match=r"Argument 'phases2' for Transformer\(\) is deprecated. It has been renamed to 'phases_lv'",
    ):
        Transformer(id="transformer", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp, phases2="abcn")  # type: ignore
