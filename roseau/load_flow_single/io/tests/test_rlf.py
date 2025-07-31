import cmath
import warnings

import numpy as np
import numpy.testing as npt
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
    ln2_m = rlf.Line(id="Ln2", bus1=bus4_m, bus2=bus5_m, parameters=lp2_m, length=0.1)

    rlf.VoltageSource(id="Src", bus=bus1_m, voltages=20e3)
    # Three-phase loads
    rlf.PowerLoad(id="P-L", bus=bus2_m, powers=50e3)  # 150 kW MV load
    rlf.CurrentLoad(id="I-L (Y)", bus=bus5_m, phases="abcn", currents=100 + 10j)
    rlf.CurrentLoad(id="I-L (D)", bus=bus5_m, phases="abc", currents=100 + 10j)
    rlf.ImpedanceLoad(id="Z-L (Y)", bus=bus5_m, phases="abcn", impedances=1 + 0.1j)
    rlf.ImpedanceLoad(id="Z-L (D)", bus=bus5_m, phases="abc", impedances=1 + 0.1j)
    rlf.PowerLoad(
        id="F-L (Y)",
        bus=bus5_m,
        phases="abcn",
        powers=9e3 + 1e3j,
        flexible_params=rlf.FlexibleParameter.pq_u_consumption(
            up_min=0.8 * 230,
            up_down=0.9 * 230,
            uq_min=0.6 * 230,
            uq_down=0.7 * 230,
            uq_up=1.05 * 230,
            uq_max=1.1 * 230,
            s_max=10e3,
            q_max=1e3,
        ),
    )
    rlf.PowerLoad(
        id="F-L (D)",
        bus=bus5_m,
        phases="abc",
        powers=9e3 + 1e3j,
        flexible_params=rlf.FlexibleParameter.pq_u_consumption(
            up_min=0.8 * 400,
            up_down=0.9 * 400,
            uq_min=0.6 * 400,
            uq_down=0.7 * 400,
            uq_up=1.05 * 400,
            uq_max=1.1 * 400,
            s_max=10e3,
            q_min=-1e3,
        ),
    )

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
            npt.assert_allclose(
                bus_s.initial_voltage.m,
                rlf.converters.calculate_voltages(bus_m.initial_potentials.m[:3], bus_m.phases[:3]).m.item(0)
                / cmath.rect(1, cmath.pi / 6),
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
        if "n" in src_m.phases:
            voltage_m = src_m.voltages.m.item(0) * rlf.SQRT3
        else:
            voltage_m = src_m.voltages.m.item(0) / cmath.rect(1, cmath.pi / 6)
        assert np.isclose(src_s.voltage.m, voltage_m)

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
                v_factor = rlf.SQRT3 if "n" in load_m.phases else 1
                for fp_m in load_m.flexible_params:
                    # P control
                    assert np.isclose(fp_s.control_p.u_min, fp_m.control_p.u_min * v_factor)
                    assert np.isclose(fp_s.control_p.u_down, fp_m.control_p.u_down * v_factor)
                    assert np.isclose(fp_s.control_p.u_up, fp_m.control_p.u_up * v_factor)
                    assert np.isclose(fp_s.control_p.u_max, fp_m.control_p.u_max * v_factor)
                    assert np.isclose(fp_s.control_p.alpha, fp_m.control_p.alpha)
                    assert np.isclose(fp_s.control_p.epsilon, fp_m.control_p.epsilon)
                    # Q control
                    assert np.isclose(fp_s.control_q.u_min, fp_m.control_q.u_min * v_factor)
                    assert np.isclose(fp_s.control_q.u_down, fp_m.control_q.u_down * v_factor)
                    assert np.isclose(fp_s.control_q.u_up, fp_m.control_q.u_up * v_factor)
                    assert np.isclose(fp_s.control_q.u_max, fp_m.control_q.u_max * v_factor)
                    assert np.isclose(fp_s.control_q.alpha, fp_m.control_q.alpha)
                    assert np.isclose(fp_s.control_q.epsilon, fp_m.control_q.epsilon)
                    # Projection
                    assert fp_s.projection.type == fp_m.projection.type
                    assert fp_s.projection.alpha == fp_m.projection.alpha
                    assert fp_s.projection.epsilon == fp_m.projection.epsilon
                    # Limits
                    assert np.isclose(fp_s.s_max.m, fp_m.s_max.m * 3)
                    assert np.isclose(fp_s.q_min.m, fp_m.q_min.m * 3)
                    assert np.isclose(fp_s.q_max.m, fp_m.q_max.m * 3)
        elif isinstance(load_m, rlf.CurrentLoad):
            assert isinstance(load_s, rlfs.CurrentLoad)
            current_m = np.mean(load_m.currents.m).item()
            if "n" not in load_m.phases:
                current_m *= rlf.SQRT3
            assert np.isclose(load_s.current.m, current_m)
        elif isinstance(load_m, rlf.ImpedanceLoad):
            assert isinstance(load_s, rlfs.ImpedanceLoad)
            impedance_m = np.mean(load_m.impedances.m).item()
            if "n" not in load_m.phases:
                impedance_m /= 3
            assert np.isclose(load_s.impedance.m, impedance_m), load_id
        else:
            raise AssertionError(f"Unknown load type: {type(load_m)}")

    # Single-phase and dual-phase connectables
    for phases in ("an", "bn", "cn", "ab", "bc", "ca", "abn", "bcn", "can"):
        load_m = rlf.PowerLoad(id="Tmp Load", phases=phases, bus=bus5_m, powers=2e3)
        with pytest.raises(rlf.RoseauLoadFlowException) as e:
            en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
        assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
        assert e.value.msg == f"Load 'Tmp Load' is not three-phase, phases='{phases}'"
        load_m.disconnect()
        load_m = rlf.CurrentLoad(id="Tmp Load", phases=phases, bus=bus5_m, currents=10 + 1j)
        with pytest.raises(rlf.RoseauLoadFlowException) as e:
            en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
        assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
        assert e.value.msg == f"Load 'Tmp Load' is not three-phase, phases='{phases}'"
        load_m.disconnect()
        load_m = rlf.ImpedanceLoad(id="Tmp Load", phases=phases, bus=bus5_m, impedances=1 + 0.1j)
        with pytest.raises(rlf.RoseauLoadFlowException) as e:
            en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
        assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
        assert e.value.msg == f"Load 'Tmp Load' is not three-phase, phases='{phases}'"
        load_m.disconnect()
    for phases in ("an", "bn", "cn", "ab", "bc", "ca", "abn", "bcn", "can"):
        src2_m = rlf.VoltageSource(id="Tmp Src", phases=phases, bus=bus5_m, voltages=400)
        with pytest.raises(rlf.RoseauLoadFlowException) as e:
            en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
        assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
        assert e.value.msg == f"Source 'Tmp Src' is not three-phase, phases='{phases}'"
        src2_m.disconnect()

    # Unbalanced connectables
    src_m = en_m.sources["Src"]
    old_voltages = src_m.voltages.m
    src_m.voltages = rlf.NegativeSequence
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise-critical")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "Source 'Src' has unbalanced voltages"
    src_m.voltages = old_voltages
    for load_m in en_m.loads.values():
        if isinstance(load_m, rlf.PowerLoad):
            old_powers = load_m.powers.m
            load_m.powers = old_powers * (1, 0.9, 0.5)
            with pytest.raises(rlf.RoseauLoadFlowException) as e:
                en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
            assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
            assert e.value.msg == f"Load '{load_m.id}' has unbalanced powers"
            load_m.powers = old_powers
        elif isinstance(load_m, rlf.CurrentLoad):
            old_currents = load_m.currents.m
            load_m.currents = old_currents * (1, 0.9, 0.5)
            with pytest.raises(rlf.RoseauLoadFlowException) as e:
                en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
            assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
            assert e.value.msg == f"Load '{load_m.id}' has unbalanced currents"
            load_m.currents = old_currents
        elif isinstance(load_m, rlf.ImpedanceLoad):
            old_impedances = load_m.impedances.m
            load_m.impedances = old_impedances * (1, 0.9, 0.5)
            with pytest.raises(rlf.RoseauLoadFlowException) as e:
                en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
            assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
            assert e.value.msg == f"Load '{load_m.id}' has unbalanced impedances"
            load_m.impedances = old_impedances

    # Unbalanced initial potentials (with different incompatible handling)
    old_potentials = bus1_m.initial_potentials.m
    bus1_m.initial_potentials = 20e3 / rlf.SQRT3 * rlf.NegativeSequence
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "Bus 'Bus1' has unbalanced initial potentials"
    with pytest.warns(UserWarning, match=r"Bus 'Bus1' has unbalanced initial potentials"):
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise-critical")
    with pytest.warns(UserWarning, match=r"Bus 'Bus1' has unbalanced initial potentials"):
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="warn")
    with warnings.catch_warnings(action="error"):
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="ignore")
    bus1_m.initial_potentials = old_potentials

    # Asymmetric line parameters
    lp2_m = rlf.LineParameters(
        id="LP2",
        z_line=[
            [0.01 + 0.01j, 0, 0.1j, 0],
            [0, 0.01 + 0.01j, 0, 0.1j],
            [0.1j, 0, 0.01 + 0.01j, 0],
            [0, 0.1j, 0, 0.01 + 0.01j],
        ],
    )
    ln2_m.parameters = lp2_m
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "Multi-phase line parameters with id 'LP2' have unbalanced series impedances."
    with pytest.warns(
        UserWarning, match=r"Multi-phase line parameters with id 'LP2' have unbalanced series impedances."
    ):
        en_s = rlfs.ElectricalNetwork.from_rlf(en_m, on_incompatible="raise-critical")

    # Non-three-phase buses or branches always raise an exception
    bus_tmp_m = rlf.Bus(id="Tmp Bus", phases="abn")
    rlf.PotentialRef(id="Tmp PRef", element=bus_tmp_m)
    rlf.VoltageSource(id="Tmp Src", bus=bus_tmp_m, voltages=400)
    en_tmp_m = rlf.ElectricalNetwork.from_element(bus_tmp_m)
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        en_s = rlfs.ElectricalNetwork.from_rlf(en_tmp_m, on_incompatible="ignore")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "Bus 'Tmp Bus' is not three-phase, phases='abn'"

    def create_non_three_phase_branch(br_type):
        gnd_tmp_m = rlf.Ground(id="Tmp Gnd")
        rlf.PotentialRef(id="Tmp PRef", element=gnd_tmp_m)
        bus1_tmp_m = rlf.Bus(id="Tmp Bus", phases="abcn")
        bus2_tmp_m = rlf.Bus(id="Tmp Bus2", phases="abcn")
        rlf.GroundConnection(ground=gnd_tmp_m, element=bus1_tmp_m)
        rlf.GroundConnection(ground=gnd_tmp_m, element=bus2_tmp_m)
        if br_type == "line":
            lp_tmp_m = rlf.LineParameters(id="Tmp TP", z_line=(0.01 + 0.01j) * np.eye(3))
            rlf.Line(id="Tmp Ln", bus1=bus1_tmp_m, bus2=bus2_tmp_m, phases="abn", parameters=lp_tmp_m, length=0.1)
        elif br_type == "switch":
            rlf.Switch(id="Tmp Sw", bus1=bus1_tmp_m, bus2=bus2_tmp_m, phases="abn")
        elif br_type == "transformer":
            tp_tmp_m = rlf.TransformerParameters(id="Tmp TP", vg="Ii0", uhv=400, ulv=400, sn=10e3, z2=0.1, ym=0.01j)
            rlf.Transformer(
                id="Tmp Tr", bus_hv=bus1_tmp_m, bus_lv=bus2_tmp_m, phases_hv="an", phases_lv="an", parameters=tp_tmp_m
            )
        rlf.VoltageSource(id="Tmp Src", bus=bus1_tmp_m, voltages=400)
        rlf.PowerLoad(id="Tmp Load", bus=bus2_tmp_m, powers=2e3)
        return rlf.ElectricalNetwork.from_element(bus1_tmp_m)

    en_tmp_m = create_non_three_phase_branch("line")
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        en_s = rlfs.ElectricalNetwork.from_rlf(en_tmp_m, on_incompatible="ignore")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "Line 'Tmp Ln' is not three-phase, phases='abn'"
    en_tmp_m = create_non_three_phase_branch("switch")
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        en_s = rlfs.ElectricalNetwork.from_rlf(en_tmp_m, on_incompatible="ignore")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "Switch 'Tmp Sw' is not three-phase, phases='abn'"
    en_tmp_m = create_non_three_phase_branch("transformer")
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        en_s = rlfs.ElectricalNetwork.from_rlf(en_tmp_m, on_incompatible="ignore")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == (
        "Multi-phase transformer parameters with id 'Tmp TP' and vector group 'Ii0' cannot be "
        "converted to `rlfs.TransformerParameters`. It must be three-phase."
    )


def test_source_voltage():
    potentials = cmath.rect(400 / rlf.SQRT3, cmath.pi / 3) * np.array([*rlf.PositiveSequence, 0], dtype=np.complex128)
    v_exp = cmath.rect(400, cmath.pi / 3)

    v_abcn = rlf.converters.calculate_voltages(potentials, "abcn").m
    v_abc = rlf.converters.calculate_voltages(potentials[:3], "abc").m
    assert np.isclose(v_exp, v_abcn.item(0) * rlf.SQRT3)

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
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        _balance_voltages("abcn", rlf.NegativeSequence, "abcn", on_incompatible="raise")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "abcn"
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        _balance_voltages("abc", rlf.NegativeSequence, "abc angle", on_incompatible="raise")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "abc angle"
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        _balance_voltages("abn", rlf.NegativeSequence[:2], "abn angle", on_incompatible="raise")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "abn angle"
    with pytest.raises(rlf.RoseauLoadFlowException) as e:
        _balance_voltages("abn", [1, 1.2] * rlf.PositiveSequence[:2], "abn mag", on_incompatible="raise")
    assert e.value.code == rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == "abn mag"
