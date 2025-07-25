import cmath
import warnings

import numpy as np
import pytest
from shapely import LineString, Point

import roseau.load_flow as rlf
import roseau.load_flow_single as rlfs
from roseau.load_flow_single.io.rlf import _balance_voltages


def test_from_rlf():  # noqa: C901
    gnd = rlf.Ground(id="Gnd")
    bus1_m = rlf.Bus(
        id="Bus1",
        phases="abc",
        nominal_voltage=20e3,
        min_voltage_level=0.95,
        max_voltage_level=1.05,
        geometry=Point(0.0, 1.0),
        initial_potentials=15e3 / rlf.SQRT3 * rlf.PositiveSequence,  # 15 kV not 20 kV
    )
    bus2_m = rlf.Bus(
        id="Bus2",
        phases="abc",
        nominal_voltage=20e3,
        min_voltage_level=0.95,
        max_voltage_level=1.05,
        geometry=Point(0.0, 2.0),
    )
    bus3_m = rlf.Bus(
        id="Bus3",
        phases="abcn",
        nominal_voltage=400,
        max_voltage_level=1.1,
        geometry=Point(0.0, 2.0),
    )
    bus4_m = rlf.Bus(
        id="Bus4",
        phases="abcn",
        nominal_voltage=400,
        min_voltage_level=0.9,
        max_voltage_level=1.1,
    )
    bus5_m = rlf.Bus(
        id="Bus5",
        phases="abcn",
        nominal_voltage=400,
        min_voltage_level=0.9,
        geometry=Point(0.0, 4.0),
    )
    lp_m = rlf.LineParameters.from_catalogue("U_AL_150")
    ln_m = rlf.Line(
        id="Ln",
        bus1=bus1_m,
        bus2=bus2_m,
        parameters=lp_m,
        length=0.5,
        geometry=LineString([(0.0, 1.0), (0.0, 2.0)]),
        max_loading=0.8,
        ground=gnd,
    )
    tp_m = rlf.TransformerParameters.from_open_and_short_circuit_tests(
        id="TP", vg="Dyn11", uhv=20e3, ulv=400, sn=160e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    tr_m = rlf.Transformer(
        id="Tr",
        bus_hv=bus2_m,
        bus_lv=bus3_m,
        parameters=tp_m,
        tap=1.025,
        max_loading=0.9,
        geometry=Point(0.0, 2.0),
    )
    sw_m = rlf.Switch(
        id="Sw",
        bus1=bus3_m,
        bus2=bus4_m,
        closed=True,
        geometry=LineString([(0.0, 2.0), (0.0, 3.0)]),
    )
    rlf.Switch(id="Sw2", bus1=bus3_m, bus2=bus4_m, closed=False)
    lp2_m = rlf.LineParameters(id="LP2", z_line=(0.01 + 0.01j) * np.eye(4), insulators=rlf.Insulator.XLPE)
    rlf.Line(id="Ln2", bus1=bus4_m, bus2=bus5_m, parameters=lp2_m, length=0.1)

    src_m = rlf.VoltageSource(id="Src", bus=bus1_m, voltages=20e3)
    rlf.PowerLoad(id="PL", bus=bus2_m, powers=20e3)  # 60 kW MV load

    rlf.GroundConnection(ground=gnd, element=bus3_m)
    rlf.PotentialRef(id="PRef", element=gnd)
    en_m = rlf.ElectricalNetwork.from_element(bus1_m)

    with warnings.catch_warnings(action="error"):
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="ignore")

    assert len(en_s.buses) == len(en_m.buses)
    assert len(en_s.lines) == len(en_m.lines)
    assert len(en_s.transformers) == len(en_m.transformers)
    assert len(en_s.switches) == len(en_m.switches)
    assert len(en_s.loads) == len(en_m.loads)
    assert len(en_s.sources) == len(en_m.sources)

    # Buses
    for bus_id, bus_s in en_s.buses.items():
        bus_m = en_m.buses[bus_id]
        assert bus_s.id == bus_m.id
        assert bus_s.nominal_voltage == bus_m.nominal_voltage
        assert bus_s.min_voltage_level == bus_m.min_voltage_level
        assert bus_s.max_voltage_level == bus_m.max_voltage_level
        assert bus_s.geometry == bus_m.geometry
        if bus_m.initial_potentials is None:
            assert bus_s.initial_voltage is None
        else:
            assert bus_s.initial_voltage is not None
            assert np.isclose(
                bus_s.initial_voltage.m,
                rlf.converters.calculate_voltages(bus_m.initial_potentials.m[:3], bus_m.phases[:3]).m.item(0),
            )

    # Line parameters
    ln_params_done = set()
    for ln_id, ln_s in en_s.lines.items():
        lp_s = ln_s.parameters
        if lp_s.id in ln_params_done:
            continue
        ln_params_done.add(lp_s.id)
        lp_m = en_m.lines[ln_id].parameters
        assert lp_s.id == lp_m.id
        assert lp_s.line_type == lp_m.line_type
        if lp_m.materials is None:
            assert lp_s.material is None
        else:
            assert lp_s.material == lp_m.materials.item(0)
        if lp_m.insulators is None:
            assert lp_s.insulator is None
        else:
            assert lp_s.insulator == lp_m.insulators.item(0)
        if lp_m.sections is None:
            assert lp_s.section is None
        else:
            assert lp_s.section is not None
            assert lp_s.section.m == lp_m.sections.m.item(0)
        # Actual line parameters conversion is tested in test_line_parameters.py
        assert np.allclose(lp_s.z_line.m, lp_m.z_line.m.item((0, 0)))
        assert np.allclose(lp_s.y_shunt.m, lp_m.y_shunt.m.item((0, 0)))

    # Transformer parameters
    tr_params_done = set()
    for tr_id, tr_s in en_s.transformers.items():
        tp_s = tr_s.parameters
        if tp_s.id in tr_params_done:
            continue
        tr_params_done.add(tp_s.id)
        tp_m = en_m.transformers[tr_id].parameters
        assert tp_s.id == tp_m.id
        assert tp_s.vg == tp_m.vg
        assert tp_s.cooling == tp_m.cooling
        assert tp_s.insulation == tp_m.insulation
        assert tp_s.fn == tp_m.fn
        assert tp_s.efficiency == tp_m.efficiency
        assert tp_s.manufacturer == tp_m.manufacturer
        assert tp_s.range == tp_m.range
        assert np.isclose(tp_s.uhv.m, tp_m.uhv.m)
        assert np.isclose(tp_s.ulv.m, tp_m.ulv.m)
        assert np.isclose(tp_s.sn.m, tp_m.sn.m)
        assert np.isclose(tp_s.z2.m, tp_m.z2.m)
        assert np.isclose(tp_s.ym.m, tp_m.ym.m)
        assert np.isclose(tp_s.p0.m, tp_m.p0.m)
        assert np.isclose(tp_s.i0.m, tp_m.i0.m)
        assert np.isclose(tp_s.psc.m, tp_m.psc.m)
        assert np.isclose(tp_s.vsc.m, tp_m.vsc.m)

    # Lines
    for ln_id, ln_s in en_s.lines.items():
        ln_m = en_m.lines[ln_id]
        assert ln_s.id == ln_m.id
        assert ln_s.bus1.id == ln_m.bus1.id
        assert ln_s.bus2.id == ln_m.bus2.id
        assert ln_s.parameters.id == ln_m.parameters.id
        assert np.isclose(ln_s.length.m, ln_m.length.m)
        assert np.isclose(ln_s.max_loading.m, ln_m.max_loading.m)
        assert ln_s.geometry == ln_m.geometry

    # Transformers
    for tr_id, tr_s in en_s.transformers.items():
        tr_m = en_m.transformers[tr_id]
        assert tr_s.id == tr_m.id
        assert tr_s.bus_hv.id == tr_m.bus_hv.id
        assert tr_s.bus_lv.id == tr_m.bus_lv.id
        assert tr_s.parameters.id == tr_m.parameters.id
        assert np.isclose(tr_s.tap, tr_m.tap)
        assert np.isclose(tr_s.max_loading.m, tr_m.max_loading.m)
        assert tr_s.geometry == tr_m.geometry

    # Switches
    for sw_id, sw_s in en_s.switches.items():
        sw_m = en_m.switches[sw_id]
        assert sw_s.id == sw_m.id
        assert sw_s.bus1.id == sw_m.bus1.id
        assert sw_s.bus2.id == sw_m.bus2.id
        assert sw_s.closed == sw_m.closed
        assert sw_s.geometry == sw_m.geometry

    # Sources
    for src_id, src_s in en_s.sources.items():
        src_m = en_m.sources[src_id]
        assert src_s.id == src_m.id
        assert src_s.bus.id == src_m.bus.id
        assert np.isclose(src_s.voltage.m, src_m.voltages.m.item(0))

    # Loads
    for load_id, load_s in en_s.loads.items():
        load_m = en_m.loads[load_id]
        assert load_s.id == load_m.id
        assert load_s.bus.id == load_m.bus.id
        if isinstance(load_m, rlf.PowerLoad):
            assert isinstance(load_s, rlfs.PowerLoad)
            assert np.isclose(load_s.power.m, load_m.powers.m.sum())
            if load_m.flexible_params is None:
                assert load_s.flexible_param is None
            else:
                fp_s = load_s.flexible_param
                for fp_m in load_m.flexible_params:
                    assert fp_s.control_p.u_min == fp_m.control_p.u_min
                    assert fp_s.control_p.u_down == fp_m.control_p.u_down
                    assert fp_s.control_p.u_up == fp_m.control_p.u_up
                    assert fp_s.control_p.u_max == fp_m.control_p.u_max
                    assert fp_s.control_p.alpha == fp_m.control_p.alpha
                    assert fp_s.control_p.epsilon == fp_m.control_p.epsilon
                    assert fp_s.control_q.u_min == fp_m.control_q.u_min
                    assert fp_s.control_q.u_down == fp_m.control_q.u_down
                    assert fp_s.control_q.u_up == fp_m.control_q.u_up
                    assert fp_s.control_q.u_max == fp_m.control_q.u_max
                    assert fp_s.control_q.alpha == fp_m.control_q.alpha
                    assert fp_s.control_q.epsilon == fp_m.control_q.epsilon
                    assert fp_s.projection.type == fp_m.projection.type
                    assert fp_s.projection.alpha == fp_m.projection.alpha
                    assert fp_s.projection.epsilon == fp_m.projection.epsilon
        elif isinstance(load_m, rlf.CurrentLoad):
            assert isinstance(load_s, rlfs.CurrentLoad)
            assert np.isclose(load_s.current.m, load_m.currents.m.mean())
        elif isinstance(load_m, rlf.ImpedanceLoad):
            assert isinstance(load_s, rlfs.ImpedanceLoad)
            assert np.isclose(load_s.impedance.m, load_m.impedances.m.mean())


def test_source_voltage():
    potentials = cmath.rect(400 / rlf.SQRT3, cmath.pi / 3) * np.array([*rlf.PositiveSequence, 0], dtype=np.complex128)
    v_exp = cmath.rect(400, cmath.pi / 6 + cmath.pi / 3)

    v_abcn = rlf.converters.calculate_voltages(potentials, "abcn").m
    v_abc = rlf.converters.calculate_voltages(potentials[:3], "abc").m
    assert np.isclose(v_exp, v_abc.item(0))

    assert np.isclose(_balance_voltages("abcn", v_abcn, "abcn", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("abc", v_abc, "abc", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("abn", v_abcn[:2], "abn", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("bcn", v_abcn[1:], "bcn", on_incompatible="raise"), v_exp)
    v_can = np.array([v_abcn[2], v_abcn[0]], dtype=np.complex128)
    assert np.isclose(_balance_voltages("can", v_can, "can", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("ab", v_abc[0:1], "ab", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("bc", v_abc[1:2], "bc", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("ca", v_abc[2:3], "ca", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("an", v_abcn[0:1], "an", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("bn", v_abcn[1:2], "bn", on_incompatible="raise"), v_exp)
    assert np.isclose(_balance_voltages("cn", v_abcn[2:3], "cn", on_incompatible="raise"), v_exp)

    # Unbalanced voltages
    with pytest.raises(RuntimeError, match=r"abcn"):
        _balance_voltages("abcn", rlf.NegativeSequence, "abcn", on_incompatible="raise")
    with pytest.raises(RuntimeError, match=r"abc"):
        _balance_voltages("abc", rlf.NegativeSequence, "abc angle", on_incompatible="raise")
    with pytest.raises(RuntimeError, match=r"abn angle"):
        _balance_voltages("abn", rlf.NegativeSequence[:2], "abn angle", on_incompatible="raise")
    with pytest.raises(RuntimeError, match=r"abn mag"):
        _balance_voltages("abn", [1, 1.2] * rlf.PositiveSequence[:2], "abn mag", on_incompatible="raise")
