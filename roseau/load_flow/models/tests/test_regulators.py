import cmath
import json
import math

import numpy as np
import numpy.testing as npt
import pytest

import roseau.load_flow as rlf
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.testing import assert_json_close

UN = 400.0
A = cmath.exp(-2j * math.pi / 3)


def create_network(
    connection: str = "wye",
    *,
    phases: str | None = None,
    u_src: tuple[float, float, float] = (370.0, 370.0, 370.0),
    powers: tuple[complex, complex, complex] = (0j, 0j, 0j),
    u_ref: float = 1.0,
    z2: complex = 1e-4,
    ym: complex = 1e-4j,
    u_range: float = 0.1,
) -> rlf.ElectricalNetwork:
    """A minimal radial network: source ─ regulator ─ load, `u_src` being line-to-line magnitudes."""
    ground = rlf.Ground("Ground")
    bus1 = rlf.Bus("Bus1", phases="abcn", nominal_voltage=UN)
    bus2 = rlf.Bus("Bus2", phases="abcn", nominal_voltage=UN)
    rlf.GroundConnection(ground=ground, element=bus1)
    if connection != "wye":
        # A wye regulator carries the neutral through: the neutral of Bus2 is already grounded
        rlf.GroundConnection(id="GC2", ground=ground, element=bus2)
    rlf.PotentialRef("PRef", element=ground)
    voltages = [u / math.sqrt(3) * A**i for i, u in enumerate(u_src)]
    rlf.VoltageSource("Src", bus1, voltages=voltages)
    rp = rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=z2, ym=ym, u_range=u_range, connection=connection)
    rlf.VoltageRegulator("Reg", bus1, bus2, parameters=rp, u_ref=u_ref, phases=phases)
    rlf.PowerLoad("Load", bus2, powers=powers)
    return rlf.ElectricalNetwork.from_element(bus1)


def test_regulator_parameters():
    rp = rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=1e-4, ym=1e-4j)
    assert rp.connection == "wye"
    assert not rp.is_delta
    assert rp.sn.m == 1e6
    assert rp.un.m == UN
    assert rp.z2.m == 1e-4
    assert rp.ym.m == 1e-4j
    assert rp.u_range == 0.1
    assert rp.alpha == 1000.0
    assert "connection='wye'" in repr(rp)

    rp = rlf.RegulatorParameters("RP2", sn=1e6, un=UN, z2=1e-4, ym=0, connection="delta_negative_rotation")
    assert rp.connection == "delta_negative_rotation"
    assert rp.is_delta

    # Serialization
    rp2 = rlf.RegulatorParameters.from_dict(rp.to_dict())
    assert rp2.to_dict() == rp.to_dict()

    # Bad values
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=1e-4, ym=0, connection="delta")  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONNECTION
    for kwargs in ({"u_range": 0.0}, {"u_range": 1.0}, {"alpha": 0.0}, {"z2": 0.0}, {"sn": 0.0}, {"un": -1.0}):
        params = {"sn": 1e6, "un": UN, "z2": 1e-4, "ym": 0} | kwargs
        with pytest.raises(RoseauLoadFlowException) as e:
            rlf.RegulatorParameters("RP", **params)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE


@pytest.mark.no_patch_engine
def test_compute_tap():
    rp = rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=1e-4, ym=1e-4j)
    assert math.isclose(rp.compute_tap(u_ref=1.0, u_in=370.0), UN / 370.0, rel_tol=1e-9)
    assert math.isclose(rp.compute_tap(u_ref=1.0, u_in=300.0), 1.1, rel_tol=1e-6)  # saturated
    assert math.isclose(rp.compute_tap(u_ref=1.0, u_in=500.0), 0.9, rel_tol=1e-6)  # saturated


def test_regulator_phases():
    bus1 = rlf.Bus("Bus1", phases="abcn")
    bus2 = rlf.Bus("Bus2", phases="abcn")
    rp_wye = rlf.RegulatorParameters("RP-wye", sn=1e6, un=UN, z2=1e-4, ym=0)
    rp_delta = rlf.RegulatorParameters("RP-delta", sn=1e6, un=UN, z2=1e-4, ym=0, connection="delta_positive_rotation")

    # Default phases
    reg = rlf.VoltageRegulator("Reg1", bus1, bus2, parameters=rp_wye)
    assert reg.phases == reg.phases1 == reg.phases2 == "abcn"
    assert reg.tap_phases == ["an", "bn", "cn"]
    reg = rlf.VoltageRegulator("Reg2", bus1, bus2, parameters=rp_delta)
    assert reg.phases == "abc"
    assert reg.tap_phases == ["ab", "bc", "ca"]
    reg = rlf.VoltageRegulator("Reg3", bus1, bus2, parameters=rp_wye, phases="can")
    assert reg.tap_phases == ["cn", "an"]

    # Incompatible phases and connection
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.VoltageRegulator("Reg4", bus1, bus2, parameters=rp_wye, phases="abc")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert "not compatible with the connection 'wye'" in e.value.msg
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.VoltageRegulator("Reg5", bus1, bus2, parameters=rp_delta, phases="abcn")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.VoltageRegulator("Reg6", bus1, bus2, parameters=rp_wye, phases="ab")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    bus3 = rlf.Bus("Bus3", phases="abc")
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.VoltageRegulator("Reg7", bus1, bus3, parameters=rp_wye)  # No neutral in bus3
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE

    # Changing the parameters to an incompatible connection
    reg = rlf.VoltageRegulator("Reg8", bus1, bus2, parameters=rp_wye)
    with pytest.raises(RoseauLoadFlowException) as e:
        reg.parameters = rp_delta
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert reg.parameters is rp_wye

    # Single-phase parameters
    import roseau.load_flow_single as rlfs

    rp_single = rlfs.RegulatorParameters("RP-single", sn=1e6, un=UN, z2=1e-4, ym=0)
    with pytest.raises(RoseauLoadFlowException):
        rlf.VoltageRegulator("Reg9", bus1, bus2, parameters=rp_single)  # type: ignore


def test_regulator_u_ref():
    bus1 = rlf.Bus("Bus1", phases="abcn")
    bus2 = rlf.Bus("Bus2", phases="abcn")
    rp = rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=1e-4, ym=0)
    reg = rlf.VoltageRegulator("Reg", bus1, bus2, parameters=rp)
    assert reg.u_ref.m == 1.0
    reg.u_ref = 1.02
    assert reg.u_ref.m == 1.02
    with pytest.raises(RoseauLoadFlowException) as e:
        reg.u_ref = 0
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES
    with pytest.warns(UserWarning, match=r"very high u_ref"):
        reg.u_ref = 102
    with pytest.raises(RoseauLoadFlowException) as e:
        reg.max_loading = 0
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE
    reg.max_loading = 0.5
    assert reg.max_power.m == 0.5e6
    assert reg.sn.m == 1e6
    assert reg.un.m == UN


@pytest.mark.no_patch_engine
@pytest.mark.parametrize("connection", ("wye", "delta_positive_rotation", "delta_negative_rotation"))
@pytest.mark.parametrize("solver", ("newton", "newton_goldstein"))
@pytest.mark.parametrize(("u_src", "expected_tap"), ((370.0, UN / 370.0), (430.0, UN / 430.0)))
def test_regulate_to_u_ref(connection, solver, u_src, expected_tap):
    """Within its range, each unit regulates its voltage exactly to u_ref (boost and buck)."""
    en = create_network(connection, u_src=(u_src,) * 3, powers=(1e3, 1e3, 1e3))
    en.solve_load_flow(solver=solver)
    reg = en.regulators["Reg"]
    bus2 = en.buses["Bus2"]
    if connection == "wye":
        npt.assert_allclose(np.abs(bus2.res_voltages_pn.m), UN / math.sqrt(3), rtol=1e-6)
        npt.assert_allclose(reg.res_taps, expected_tap, rtol=1e-3)
    else:
        npt.assert_allclose(np.abs(bus2.res_voltages_pp.m), UN, rtol=1e-6)
        # In a closed delta, each tap acts on the three line-to-line voltages: the regulation is
        # amplified by about 1.5
        npt.assert_allclose(reg.res_taps, reg.res_taps[0], rtol=1e-6)
        npt.assert_allclose(1 + 1.5 * (reg.res_taps - 1), expected_tap, rtol=5e-3)


@pytest.mark.no_patch_engine
@pytest.mark.parametrize("connection", ("wye", "delta_positive_rotation", "delta_negative_rotation"))
def test_saturation(connection):
    """Outside its range, the taps stay at their bounds."""
    en = create_network(connection, u_src=(300.0, 300.0, 300.0), powers=(1e3, 1e3, 1e3))
    en.solve_load_flow()
    reg = en.regulators["Reg"]
    npt.assert_allclose(reg.res_taps, 1.1, rtol=1e-6)
    en = create_network(connection, u_src=(500.0, 500.0, 500.0), powers=(1e3, 1e3, 1e3))
    en.solve_load_flow()
    reg = en.regulators["Reg"]
    npt.assert_allclose(reg.res_taps, 0.9, rtol=1e-6)


# Reference results for the same unbalanced networks
REFERENCE_RESULTS = {
    ("wye", 1.0): (
        [
            230.81301338687211 - 5.966336060557444j,
            -119.01769443844712 - 197.90937760472556j,
            -104.43666788345533 + 196.6355313825748j,
            0j,
        ],
        [1.0984473035103586, 1.0626689290508522, 1.1],
    ),
    ("delta_positive_rotation", 1.0): (
        [
            228.5283857797637 + 6.041829074808867j,
            -111.31291905217799 - 204.92709643393778j,
            -124.09669827174676 + 194.86857011244092j,
            0j,
        ],
        [1.059505975400669, 1.0497357200300685, 1.0898921074920191],
    ),
    ("delta_negative_rotation", 1.02): (
        [
            239.78646006915196 - 26.462813423768157j,
            -131.87830159747492 - 194.77592918272518j,
            -91.6712157604981 + 211.2380967230025j,
            0j,
        ],
        [1.054755125640482, 1.0873843827934884, 1.098714950523822],
    ),
    ("wye", 1.05): (
        [
            231.15074014529347 - 5.95791432578975j,
            -123.03284590394844 - 205.14330864277562j,
            -104.43666788371479 + 196.63553138023497j,
            0j,
        ],
        [1.1, 1.0999999997162635, 1.1],
    ),
}


@pytest.mark.no_patch_engine
@pytest.mark.parametrize(("connection", "u_ref"), list(REFERENCE_RESULTS))
def test_unbalanced_reference_results(connection, u_ref):
    en = create_network(
        connection,
        u_src=(370.0, 380.0, 360.0),
        powers=(30e3 + 5e3j, 20e3 + 2e3j, 40e3 + 10e3j),
        u_ref=u_ref,
        z2=0.02 + 0.05j,
    )
    en.solve_load_flow()
    expected_potentials, expected_taps = REFERENCE_RESULTS[connection, u_ref]
    npt.assert_allclose(en.buses["Bus2"].res_potentials.m, expected_potentials, atol=1e-8)
    npt.assert_allclose(en.regulators["Reg"].res_taps, expected_taps, rtol=1e-8)

    # Currents: the regulator conserves the currents
    reg = en.regulators["Reg"]
    currents1, currents2 = reg.res_currents
    npt.assert_allclose(sum(currents1.m) + sum(currents2.m), 0, atol=1e-6)
    # Losses are small and positive
    assert reg.res_power_losses.m.real > 0


@pytest.mark.no_patch_engine
def test_neutral_current():
    """The neutral of a wye regulator is carried through: its current flows from one side to the other."""
    en = create_network("wye", powers=(30e3, 10e3, 20e3), z2=0.02 + 0.05j)
    en.solve_load_flow()
    reg = en.regulators["Reg"]
    _, currents2 = reg.res_currents
    load_currents = en.loads["Load"].res_currents.m
    npt.assert_allclose(-currents2.m, load_currents, atol=1e-8)  # All the load currents flow through bus2
    potentials1, potentials2 = reg.res_potentials
    npt.assert_allclose(potentials1.m[3], potentials2.m[3], atol=1e-10)


@pytest.mark.no_patch_engine
def test_update_parameters():
    en = create_network("wye", powers=(10e3, 10e3, 10e3))
    reg = en.regulators["Reg"]
    en.solve_load_flow()
    npt.assert_allclose(np.abs(en.buses["Bus2"].res_voltages_pn.m), UN / math.sqrt(3), rtol=1e-6)

    # New target: warm started
    reg.u_ref = 0.98
    en.solve_load_flow()
    npt.assert_allclose(np.abs(en.buses["Bus2"].res_voltages_pn.m), 0.98 * UN / math.sqrt(3), rtol=1e-6)

    # Same connection and range, other impedances: the C++ model is updated in place
    cy_element = reg._cy_element
    reg.parameters = rlf.RegulatorParameters("RP2", sn=1e6, un=1.01 * UN, z2=1e-3, ym=0)
    assert reg._cy_element is cy_element
    en.solve_load_flow()
    npt.assert_allclose(np.abs(en.buses["Bus2"].res_voltages_pn.m), 0.98 * 1.01 * UN / math.sqrt(3), rtol=1e-6)

    # Another range: the C++ model is rebuilt
    reg.parameters = rlf.RegulatorParameters("RP3", sn=1e6, un=UN, z2=1e-3, ym=0, u_range=0.05)
    assert reg._cy_element is not cy_element
    en.solve_load_flow()
    npt.assert_allclose(reg.res_taps, 1.05, rtol=1e-6)  # saturated
    assert set(en._parameters["regulator"]) == {"RP3"}


@pytest.mark.no_patch_engine
def test_results(tmp_path):
    en = create_network(
        "delta_negative_rotation",
        u_src=(370.0, 380.0, 360.0),
        powers=(30e3 + 5e3j, 20e3 + 2e3j, 40e3 + 10e3j),
        u_ref=1.02,
        z2=0.02 + 0.05j,
    )
    en.solve_load_flow()
    reg = en.regulators["Reg"]

    # Loading
    powers1, powers2 = reg.res_powers
    loading = max(abs(powers1.m.sum()), abs(powers2.m.sum())) / 1e6
    assert math.isclose(reg.res_loading.m, loading)
    assert not reg.res_violated
    reg.max_loading = 0.05
    assert reg.res_violated
    assert reg._res_state_getter() == "very-high"

    # Data frames
    df = en.res_regulators
    assert df.index.names == ["regulator_id", "phase"]
    assert list(df.index.get_level_values("phase")) == ["a", "b", "c"]
    npt.assert_allclose(df["potential2"].to_numpy(), reg.res_potentials[1].m)
    assert df["violated"].all()
    df = en.res_regulators_taps
    assert list(df.index.get_level_values("phase")) == ["ab", "bc", "ca"]
    npt.assert_allclose(df["tap"].to_numpy(), reg.res_taps)
    df = en.regulators_frame
    assert df.loc["Reg", "parameters_id"] == "RP"
    assert df.loc["Reg", "phases"] == "abc"

    # Results to dict
    res = en.results_to_dict(full=True)
    (res_reg,) = res["regulators"]
    npt.assert_allclose(res_reg["taps"], reg.res_taps)
    assert math.isclose(res_reg["loading"], loading)

    # JSON round trip with the results
    path = tmp_path / "network.json"
    en.to_json(path)
    data = json.loads(path.read_text())
    assert data["regulators_params"][0]["connection"] == "delta_negative_rotation"
    en2 = rlf.ElectricalNetwork.from_json(path)
    reg2 = en2.regulators["Reg"]
    assert reg2.parameters.connection == "delta_negative_rotation"
    assert reg2.u_ref.m == 1.02
    npt.assert_allclose(reg2.res_taps, reg.res_taps)
    npt.assert_allclose(en2.buses["Bus2"].res_potentials.m, en.buses["Bus2"].res_potentials.m)
    assert_json_close(en2.to_dict(), en.to_dict())

    # Solving again gives the same results
    en2.solve_load_flow()
    npt.assert_allclose(reg2.res_taps, reg.res_taps, rtol=1e-8)


def test_network_without_regulators_json():
    """The keys of the regulators are written only when the network has regulators."""
    bus = rlf.Bus("Bus", phases="abcn")
    rlf.VoltageSource("Src", bus, voltages=230)
    ground = rlf.Ground("Ground")
    rlf.GroundConnection(ground=ground, element=bus)
    rlf.PotentialRef("PRef", element=ground)
    en = rlf.ElectricalNetwork.from_element(bus)
    data = en.to_dict(include_results=False)
    assert "regulators" not in data
    assert "regulators_params" not in data
    assert rlf.ElectricalNetwork.from_dict(data).regulators == {}


@pytest.mark.no_patch_engine
def test_convert_to_single_phase():
    import roseau.load_flow_single as rlfs

    en = create_network("wye", powers=(10e3 + 2e3j,) * 3, z2=0.02 + 0.05j, u_ref=1.02)
    en.solve_load_flow()
    en_s = rlfs.ElectricalNetwork.from_rlf(en)
    reg_s = en_s.regulators["Reg"]
    assert reg_s.u_ref.m == 1.02
    assert reg_s.parameters.sn.m == 1e6
    en_s.solve_load_flow()
    reg = en.regulators["Reg"]
    npt.assert_allclose(reg_s.res_tap, reg.res_taps, rtol=1e-8)
    npt.assert_allclose(abs(en_s.buses["Bus2"].res_voltage.m), np.abs(en.buses["Bus2"].res_voltages_pp.m), rtol=1e-8)

    # A closed delta has no single-phase equivalent
    en = create_network("delta_positive_rotation")
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.ElectricalNetwork.from_rlf(en)
    assert e.value.code == RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE


def test_from_power_factory():
    # The PowerFactory 2022 example: 20 kV, 300 A, ±10 %, uk = 1 %, pcu = 2 kW, whose own load flow
    # results give Sb = 10 392.3 kVA and r1pu/x1pu = 0.000192/0.009998
    with pytest.warns(UserWarning, match=r"approximated by the Type A ratio") as records:
        rlf.RegulatorParameters.from_power_factory("B", un=20, in_=300, pc_reg=10, uk=1, pcu=2000, kind="Type B")
    assert len(records) == 1
    rp = rlf.RegulatorParameters.from_power_factory("rp", un=20, in_=300, pc_reg=10, uk=1, pcu=2000)
    assert rp.connection == "wye"
    assert math.isclose(rp.sn.m, 10392.3e3, rel_tol=1e-6)
    assert rp.un.m == 20e3
    assert math.isclose(rp.u_range, 0.1)
    assert rp.ym.m == 0
    z_pu = rp.z2.m / (rp.un.m**2 / rp.sn.m)
    assert math.isclose(z_pu.real, 0.000192, abs_tol=1e-6)
    assert math.isclose(z_pu.imag, 0.009998, abs_tol=1e-6)
    assert math.isclose(abs(z_pu), 0.01)

    # Three single-phase 11.547 kV (line-to-neutral) units of 300 A are the same regulator as a
    # three-phase 20 kV, 300 A one, with a third of the copper losses each
    three_phase = rlf.RegulatorParameters.from_power_factory("3ph", un=20, in_=300, pc_reg=10, uk=1, pcu=3000)
    units = rlf.RegulatorParameters.from_power_factory(
        "3x1ph", un=20 / math.sqrt(3), in_=300, pc_reg=10, uk=1, pcu=1000, configuration="Star, 3 x 1-phase"
    )
    assert math.isclose(units.sn.m, three_phase.sn.m)
    assert math.isclose(units.un.m, three_phase.un.m)
    assert cmath.isclose(units.z2.m, three_phase.z2.m)

    # The closed-delta type of the PowerFactory 2022 validation: three 20 kV (line-to-line), 300 A
    # units, uk = 1 %, pcu = 2 kW each, whose export gives Sb = 6000 kVA (one unit) and
    # r1pu/x1pu = 0.000333/0.009994
    for closed_delta_connection, expected in (
        (None, "delta_positive_rotation"),
        ("Lagging", "delta_positive_rotation"),
        ("Leading", "delta_negative_rotation"),
    ):
        rp = rlf.RegulatorParameters.from_power_factory(
            "delta",
            un=20,
            in_=300,
            pc_reg=10,
            uk=1,
            pcu=2000,
            configuration="Closed delta, 3 x 1-phase",
            closed_delta_connection=closed_delta_connection,
        )
        assert rp.connection == expected
        assert rp.un.m == 20e3
        z_pu = rp.z2.m / (20e3**2 / 6e6)  # The impedance base is a single unit's
        assert math.isclose(z_pu.real, 0.000333, abs_tol=1e-6)
        assert math.isclose(z_pu.imag, 0.009994, abs_tol=1e-6)

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.RegulatorParameters.from_power_factory(
            "rp", un=20, in_=300, pc_reg=10, uk=1, pcu=2000, configuration="Open delta, 2 x 1-phase"
        )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONNECTION
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.RegulatorParameters.from_power_factory("rp", un=20, in_=300, pc_reg=10, uk=1, pcu=1e6)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE
    assert "exceed" in e.value.msg
