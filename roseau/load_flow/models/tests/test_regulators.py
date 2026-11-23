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
    rlf.VoltageSource("Src", bus1, voltages=np.array(u_src) / rlf.SQRT3 * rlf.PositiveSequence)
    rp = rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=z2, ym=ym, u_range=u_range, connection=connection)
    rlf.VoltageRegulator("Reg", bus1, bus2, parameters=rp, u_ref=u_ref, phases=phases)
    rlf.PowerLoad("Load", bus2, powers=powers)
    return rlf.ElectricalNetwork.from_element(bus1)


def test_regulator_parameters():
    rp = rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=1e-4, ym=1e-4j)
    assert rp.connection == "wye"
    assert rp.sn.m == 1e6
    assert rp.un.m == UN
    assert rp.z2.m == 1e-4
    assert rp.ym.m == 1e-4j
    assert rp.u_range == 0.1
    assert rp.alpha == 1000.0
    assert "connection='wye'" in repr(rp)

    rp = rlf.RegulatorParameters("RP2", sn=1e6, un=UN, z2=1e-4, ym=0, connection="delta")
    assert rp.connection == "delta"

    # Serialization
    rp2 = rlf.RegulatorParameters.from_dict(rp.to_dict())
    assert rp2.to_dict() == rp.to_dict()

    # Bad values
    for connection in ("delta_positive_rotation", "delta_negative_rotation"):
        with pytest.raises(RoseauLoadFlowException) as e:
            rlf.RegulatorParameters("RP", sn=1e6, un=UN, z2=1e-4, ym=0, connection=connection)  # type: ignore
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REGULATOR_CONNECTION
    for kwargs in ({"u_range": 0.0}, {"u_range": 1.0}, {"alpha": 0.0}, {"z2": 0.0}, {"sn": 0.0}, {"un": -1.0}):
        params = {"sn": 1e6, "un": UN, "z2": 1e-4, "ym": 0} | kwargs
        with pytest.raises(RoseauLoadFlowException) as e:
            rlf.RegulatorParameters("RP", **params)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS


def test_regulator_phases():
    bus1 = rlf.Bus("Bus1", phases="abcn")
    bus2 = rlf.Bus("Bus2", phases="abcn")
    rp_wye = rlf.RegulatorParameters("RP-wye", sn=1e6, un=UN, z2=1e-4, ym=0)
    rp_delta = rlf.RegulatorParameters("RP-delta", sn=1e6, un=UN, z2=1e-4, ym=0, connection="delta")

    # Default phases
    reg = rlf.VoltageRegulator("Reg1", bus1, bus2, parameters=rp_wye)
    assert reg.phases == reg.phases1 == reg.phases2 == "abcn"
    assert reg.tap_phases == ["an", "bn", "cn"]
    reg = rlf.VoltageRegulator("Reg2", bus1, bus2, parameters=rp_delta)
    assert reg.phases == "abc"
    assert reg.tap_phases == ["ab", "bc", "ca"]
    reg = rlf.VoltageRegulator("Reg3", bus1, bus2, parameters=rp_wye, phases="cn")
    assert reg.tap_phases == ["cn"]

    # Incompatible phases and connection
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.VoltageRegulator("Reg4", bus1, bus2, parameters=rp_wye, phases="abc")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert "not compatible with the connection 'wye'" in e.value.msg
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.VoltageRegulator("Reg5", bus1, bus2, parameters=rp_delta, phases="abcn")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    for phases in ("ab", "abn", "bcn", "can"):  # No bi-phase regulators
        with pytest.raises(RoseauLoadFlowException) as e:
            rlf.VoltageRegulator("Reg6", bus1, bus2, parameters=rp_wye, phases=phases)
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


def test_update_parameters():
    en = create_network("wye")
    reg = en.regulators["Reg"]

    # Same connection and range, other impedances: the C++ model is updated in place
    cy_element = reg._cy_element
    reg.parameters = rlf.RegulatorParameters("RP2", sn=1e6, un=1.01 * UN, z2=1e-3, ym=0)
    assert reg._cy_element is cy_element
    assert set(en._parameters["regulator"]) == {"RP2"}

    # Another range: the C++ model is rebuilt
    reg.parameters = rlf.RegulatorParameters("RP3", sn=1e6, un=UN, z2=1e-3, ym=0, u_range=0.05)
    assert reg._cy_element is not cy_element
    assert set(en._parameters["regulator"]) == {"RP3"}


def test_results(all_elements_network_with_results, tmp_path):
    en = all_elements_network_with_results
    reg = en.regulators["reg0"]

    # Loading
    powers1, powers2 = reg.res_powers
    loading = max(abs(powers1.m.sum()), abs(powers2.m.sum())) / reg.sn.m
    npt.assert_allclose(reg.res_loading.m, loading)
    assert not reg.res_violated
    reg.max_loading = loading / 2
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
    assert df.loc["reg0", "parameters_id"] == "rp0"
    assert df.loc["reg0", "phases"] == "abc"

    # Results to dict
    res = en.results_to_dict(full=True)
    (res_reg,) = res["regulators"]
    npt.assert_allclose(res_reg["taps"], reg.res_taps)
    npt.assert_allclose(res_reg["loading"], loading)

    # JSON round trip with the results
    path = tmp_path / "network.json"
    en.to_json(path)
    data = json.loads(path.read_text())
    assert data["regulators_params"][0]["connection"] == "delta"
    en2 = rlf.ElectricalNetwork.from_json(path)
    reg2 = en2.regulators["reg0"]
    assert reg2.parameters.connection == "delta"
    assert reg2.u_ref.m == 1.025
    npt.assert_allclose(reg2.res_taps, reg.res_taps)
    npt.assert_allclose(en2.buses["bus7"].res_potentials.m, en.buses["bus7"].res_potentials.m)
    assert_json_close(en2.to_dict(), en.to_dict())


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
    rp = rlf.RegulatorParameters.from_power_factory(
        "delta", un=20, in_=300, pc_reg=10, uk=1, pcu=2000, configuration="Closed delta, 3 x 1-phase"
    )
    assert rp.connection == "delta"
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
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REGULATOR_PARAMETERS
    assert "exceed" in e.value.msg
