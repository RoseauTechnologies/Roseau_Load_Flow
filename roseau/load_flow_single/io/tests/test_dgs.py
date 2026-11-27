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


def test_dgs_closed_delta_regulator_parameters(dgs_regulators_networks_dir):
    en = _read_regulator_network(dgs_regulators_networks_dir, "Regulator_103_Type_A", TypVoltreg__config=3)
    rp = en.regulators[REGULATOR_ID].parameters
    assert rp.config == "closed-delta"
    # A unit of a closed delta has the line-to-line `Un` and the base power Sb = Un·In, on which its
    # uk = 1 % and pcu = 2 kW are read
    sb = 20e3 * 300
    np.testing.assert_allclose(rp.sn.m, np.sqrt(3) * sb)
    np.testing.assert_allclose(rp.un.m, 20e3)
    r = 2000 / sb
    np.testing.assert_allclose(rp.z2.m / (20e3**2 / sb), complex(r, np.sqrt(0.01**2 - r**2)))


def test_dgs_unsupported_regulators(dgs_regulators_networks_dir):
    # The open delta is not supported
    with pytest.raises(RoseauLoadFlowException) as e:
        _read_regulator_network(dgs_regulators_networks_dir, "Regulator_103_Type_A", TypVoltreg__config=4)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED
    assert "only the star and closed-delta configurations (1, 2, 3) are supported" in e.value.msg

    # No automatic tap changing
    with pytest.raises(RoseauLoadFlowException) as e:
        _read_regulator_network(dgs_regulators_networks_dir, "Regulator_103_Type_A", ElmVoltreg__ntrcn=0)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED
    assert "no automatic tap changing" in e.value.msg


def _create_regulator_network(ym: complex = 0j, config: str = "wye") -> rlfs.ElectricalNetwork:
    levels = {"min_voltage_level": 0.95, "max_voltage_level": 1.05}
    bus0 = rlfs.Bus("Source Bus", nominal_voltage=20e3, geometry=shapely.Point(5.74, 45.18), **levels)
    bus1 = rlfs.Bus("Bus 1", nominal_voltage=20e3, geometry=shapely.Point(5.75, 45.19), **levels)
    bus2 = rlfs.Bus("Bus 2", nominal_voltage=20e3, geometry=shapely.Point(5.76, 45.20), **levels)
    rlfs.VoltageSource("Grid", bus=bus0, voltage=20e3)
    lp = rlfs.LineParameters("LP", z_line=0.3 + 0.35j)
    rlfs.Line("Line", bus1=bus0, bus2=bus1, parameters=lp, length=10)
    rp = rlfs.RegulatorParameters("RP", sn=8e6, un=20e3, z2=0.05 + 0.5j, ym=ym, u_range=0.1, config=config, alpha=500.0)
    rlfs.VoltageRegulator(
        "Regulator",
        bus1=bus1,
        bus2=bus2,
        parameters=rp,
        u_ref=1.02,
        max_loading=0.9,
        geometry=shapely.Point(5.755, 45.195),
    )
    rlfs.PowerLoad("Load", bus=bus2, power=4e6 + 1e6j)
    return rlfs.ElectricalNetwork.from_element(bus0, name="Regulator Net", crs="EPSG:4326")


def test_to_from_dgs_roundtrip_with_regulator():
    en = _create_regulator_network()
    data = en.to_dgs_dict()
    (typ,) = (dict(zip(data["TypVoltreg"]["Attributes"], v, strict=True)) for v in data["TypVoltreg"]["Values"])
    assert typ["config"] == 2  # Star, 3 x 1-phase
    assert typ["type"] == 0  # Type A
    # The data of a unit: line-to-neutral rated voltage, base power Sb = Un·In = sn / 3
    np.testing.assert_allclose(typ["Un"], 20 / np.sqrt(3))
    np.testing.assert_allclose(typ["In"], 8e6 / (np.sqrt(3) * 20e3))
    np.testing.assert_allclose(typ["Sb"], 8e3 / 3)
    np.testing.assert_allclose(typ["pcReg"], 10)
    (elm,) = (dict(zip(data["ElmVoltreg"]["Attributes"], v, strict=True)) for v in data["ElmVoltreg"]["Values"])
    assert elm["usetp"] == 1.02
    assert elm["maxload"] == 90.0
    assert (elm["GPSlon"], elm["GPSlat"]) == (5.755, 45.195)

    en2 = rlfs.ElectricalNetwork.from_dgs_dict(data, use_name_as_id=True)
    assert_json_close(en2.to_dict(), en.to_dict())
    rp, rp2 = en.regulators["Regulator"].parameters, en2.regulators["Regulator"].parameters
    assert rp2.alpha == 500.0  # Kept in the description of the type
    np.testing.assert_allclose(rp2.z2.m, rp.z2.m)

    # The magnetising admittance is kept too, with a warning
    en = _create_regulator_network(ym=1e-6j)
    with pytest.warns(UserWarning, match=r"magnetising admittance"):
        data = en.to_dgs_dict()
    en2 = rlfs.ElectricalNetwork.from_dgs_dict(data, use_name_as_id=True)
    assert en2.regulators["Regulator"].parameters.ym.m == 1e-6j


def test_to_from_dgs_roundtrip_with_delta_regulator():
    en = _create_regulator_network(config="closed-delta")
    data = en.to_dgs_dict()
    (typ,) = (dict(zip(data["TypVoltreg"]["Attributes"], v, strict=True)) for v in data["TypVoltreg"]["Values"])
    assert typ["config"] == 3  # Closed delta, 3 x 1-phase
    assert typ["cldeltacn"] == 0  # Lagging
    np.testing.assert_allclose(typ["Sb"], 8e3 / np.sqrt(3))  # The base power of a unit, Un·In
    np.testing.assert_allclose(typ["In"], 8e6 / (np.sqrt(3) * 20e3))

    en2 = rlfs.ElectricalNetwork.from_dgs_dict(data, use_name_as_id=True)
    assert_json_close(en2.to_dict(), en.to_dict())
    rp, rp2 = en.regulators["Regulator"].parameters, en2.regulators["Regulator"].parameters
    assert rp2.config == "closed-delta"
    np.testing.assert_allclose(rp2.sn.m, rp.sn.m)
    np.testing.assert_allclose(rp2.z2.m, rp.z2.m)


def test_to_dgs_without_regulators():
    """The tables of the regulators are only written when the network has regulators."""
    bus = rlfs.Bus("Bus", nominal_voltage=400)
    rlfs.VoltageSource("Grid", bus=bus, voltage=400)
    en = rlfs.ElectricalNetwork.from_element(bus)
    data = en.to_dgs_dict()
    assert "TypVoltreg" not in data
    assert "ElmVoltreg" not in data
