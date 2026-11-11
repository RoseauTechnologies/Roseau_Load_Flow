import json
import warnings

import numpy as np
import pytest
import shapely

import roseau.load_flow_single as rlfs
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.testing import assert_json_close


def test_from_dgs(dgs_network_path):
    # Read DGS
    with warnings.catch_warnings():
        if dgs_network_path.stem == "Line_Without_Type":
            warnings.filterwarnings(
                "ignore", message=r"The network contains lines but it is missing line types", category=UserWarning
            )
            warnings.filterwarnings("ignore", message=r"Unbalanced loads are not supported", category=UserWarning)
        en = rlfs.ElectricalNetwork.from_dgs_file(dgs_network_path)
        # Also make sure use_name_as_id=True works
        en2 = rlfs.ElectricalNetwork.from_dgs_file(dgs_network_path, use_name_as_id=True)
    assert len(en2.buses) == len(en.buses)
    assert len(en2.lines) == len(en.lines)
    assert len(en2.loads) == len(en.loads)
    assert len(en2.sources) == len(en.sources)
    assert len(en2.transformers) == len(en.transformers)
    assert len(en2.switches) == len(en.switches)

    # Check the validity of the network
    en._check_validity(constructed=False)


def test_to_from_dgs_roundtrip():
    bus_mv = rlfs.Bus(
        "MV Bus",
        nominal_voltage=20e3,
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
        max_voltage_level=1.05,
        min_voltage_level=0.95,
    )
    bus1_lv = rlfs.Bus(
        "LV Bus 1",
        nominal_voltage=400,
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
        max_voltage_level=1.1,
        min_voltage_level=0.9,
    )
    bus2_lv = rlfs.Bus(
        "LV Bus 2",
        nominal_voltage=400,
        geometry=shapely.Point(5.738531306019317, 45.18776131177264),
        max_voltage_level=1.1,
        min_voltage_level=0.9,
    )

    tp = rlfs.TransformerParameters.from_catalogue("SE Vegeta AA0Ak 630kVA 20kV 410V Dyn11")
    rlfs.Transformer(
        "MV/LV Transformer",
        bus_hv=bus_mv,
        bus_lv=bus1_lv,
        parameters=tp,
        max_loading=0.9,
        tap=1.025,
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
    )

    lp = rlfs.LineParameters.from_catalogue("U_AL_240")
    rlfs.Line(
        "LV Line",
        bus1=bus1_lv,
        bus2=bus2_lv,
        parameters=lp,
        length=0.6,
        max_loading=0.95,
        geometry=shapely.LineString(
            [
                (5.741095497645757, 45.18848721409608),
                (5.740172817813646, 45.18832086229793),
                (5.7391643072994825, 45.18798815724316),
                (5.738531306019317, 45.18776131177264),
            ]
        ),
    )

    rlfs.Switch(
        "LV Switch",
        bus1=bus1_lv,
        bus2=bus2_lv,
        closed=False,  # Open switch
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
    )

    rlfs.VoltageSource("MV Grid", bus=bus_mv, voltage=21e3 * np.exp(1j * np.pi / 6))
    rlfs.PowerLoad("LV Load", bus=bus2_lv, power=7e3 + 2e3j)

    en = rlfs.ElectricalNetwork.from_element(bus_mv, name="My Test Net", crs="EPSG:4326")
    en2 = rlfs.ElectricalNetwork.from_dgs_dict(en.to_dgs_dict(), use_name_as_id=True)
    assert_json_close(en2.to_dict(), en.to_dict())

    # Test warning for non-EPSG:4326 CRS
    en.crs = "EPSG:2154"
    with pytest.warns(
        UserWarning,
        match=(
            r"Power factory only supports GPS coordinates that operate on the WGS84 datum "
            r"\(EPSG:4326\) while your network 'My Test Net' has crs 'EPSG:2154'. Please convert "
            r"the geometries to GPS coordinates and set en.crs to 'EPSG:4326' before exporting to DGS."
        ),
    ):
        en.to_dgs_dict()
    en.crs = None  # None is OK, considered as EPSG:4326
    with warnings.catch_warnings(action="error"):
        en.to_dgs_dict()


# PowerFactory 2022 exports of a source -> line -> step-voltage regulator -> 8 MW load feeder,
# solved by PowerFactory with a continuous tap: Type A and Type B, with a reachable (1.03 p.u.) and
# an unreachable (1.2 p.u., tap saturated) voltage setpoint.
REGULATOR_ID = "Step-Voltage Regulator"


def _read_regulator_network(dgs_regulators_networks_dir, name: str, **changes) -> rlfs.ElectricalNetwork:
    """Read a single-phase regulator network, changing some fields of its rows (`Class.field`)."""
    data = json.loads((dgs_regulators_networks_dir / "single" / f"{name}.json").read_text())
    for key, value in changes.items():
        cls, field = key.split("__")
        index = data[cls]["Attributes"].index(field)
        data[cls]["Values"][0][index] = value
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return rlfs.ElectricalNetwork.from_dgs_dict(data, use_name_as_id=True)


def test_dgs_regulator_parameters(dgs_regulators_networks_dir):
    en = _read_regulator_network(dgs_regulators_networks_dir, "Regulator_103_Type_A")
    regulator = en.regulators[REGULATOR_ID]
    assert regulator.u_ref.m == 1.03
    assert regulator.max_loading.m == 1.0
    rp = regulator.parameters
    # Sb = √3·Un·In (PowerFactory displays 10 392.3 kVA), Zb = Un²/Sb
    sb = np.sqrt(3) * 20e3 * 300
    np.testing.assert_allclose(rp.sn.m, sb)
    np.testing.assert_allclose(rp.un.m, 20e3)
    np.testing.assert_allclose(rp.u_range, 0.1)
    # uk = 1 %, pcu = 2 kW (PowerFactory's own rounded r1pu/x1pu: 0.000192/0.009998)
    zb = 20e3**2 / sb
    np.testing.assert_allclose(rp.z2.m / zb, 0.000192 + 0.009998j, atol=1e-6)
    assert rp.ym.m == 0

    # Three single-phase star-connected units (line-to-neutral `Un`, per-unit `pcu`) are the same
    # regulator as the equivalent "Star, 3-phase" one
    en2 = _read_regulator_network(
        dgs_regulators_networks_dir,
        "Regulator_103_Type_A",
        TypVoltreg__config=2,
        TypVoltreg__Un=20 / np.sqrt(3),
        TypVoltreg__pcu=2000 / 3,
    )
    rp2 = en2.regulators[REGULATOR_ID].parameters
    np.testing.assert_allclose(rp2.sn.m, rp.sn.m)
    np.testing.assert_allclose(rp2.un.m, rp.un.m)
    np.testing.assert_allclose(rp2.z2.m, rp.z2.m)


@pytest.mark.no_patch_engine
@pytest.mark.parametrize(
    ("name", "tolerance"),
    (
        ("Regulator_103_Type_A", 1e-3),
        ("Regulator_103_Type_B", 1.5e-3),
        # Saturated: the same tap ratio 1.1, only the position of the series impedance differs
        ("Regulator_12_Type_A", 2e-4),
    ),
)
def test_dgs_regulator_voltages_match_power_factory(dgs_regulators_networks_dir, name, tolerance):
    """The voltages match PowerFactory's: exactly at the source side, and at the regulated side
    within PowerFactory's own regulation tolerance (it stops within 0.1 % of the setpoint, while the
    continuous controller reaches it exactly)."""
    data = json.loads((dgs_regulators_networks_dir / "single" / f"{name}.json").read_text())
    elm = dict(zip(data["ElmVoltreg"]["Attributes"], data["ElmVoltreg"]["Values"][0], strict=True))
    en = _read_regulator_network(dgs_regulators_networks_dir, name)
    en.solve_load_flow()
    regulator = en.regulators[REGULATOR_ID]
    for side, tol in ((regulator.side1, 1e-5), (regulator.side2, tolerance)):
        expected = elm[f"m:U1l:bus{'s' if side is regulator.side1 else 'l'}"] * 1e3
        np.testing.assert_allclose(abs(side.res_voltage.m), expected, rtol=tol)


@pytest.mark.no_patch_engine
@pytest.mark.parametrize("name", ("Regulator_12_Type_A", "Regulator_12_Type_B"))
def test_dgs_type_b_regulator_saturates_with_type_a_law(dgs_regulators_networks_dir, name):
    """A Type B regulator is read with the Type A ratio law: an unreachable setpoint saturates it
    at `1 + u_range` = 1.1, where PowerFactory's own Type B ratio is 1 / (1 - 0.1) = 1.111."""
    en = _read_regulator_network(dgs_regulators_networks_dir, name)
    en.solve_load_flow()
    np.testing.assert_allclose(en.regulators[REGULATOR_ID].res_tap, 1.1, rtol=1e-6)


def test_dgs_unsupported_regulators(dgs_regulators_networks_dir):
    # A closed delta has no single-phase equivalent
    with pytest.raises(RoseauLoadFlowException) as e:
        _read_regulator_network(dgs_regulators_networks_dir, "Regulator_103_Type_A", TypVoltreg__config=3)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED
    assert "only the star configurations (1, 2) are supported" in e.value.msg

    # No automatic tap changing
    with pytest.raises(RoseauLoadFlowException) as e:
        _read_regulator_network(dgs_regulators_networks_dir, "Regulator_103_Type_A", ElmVoltreg__ntrcn=0)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED
    assert "no automatic tap changing" in e.value.msg
