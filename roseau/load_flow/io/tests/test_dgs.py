import copy
import json
import warnings

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs import dgs_dict_to_df, typ_lne_to_lp
from roseau.load_flow.io.dgs.constants import GENERAL_LOAD_INPUT_MODE
from roseau.load_flow.io.dgs.loads import compute_3phase_load_powers
from roseau.load_flow.models import Line
from roseau.load_flow.network import ElectricalNetwork


def test_from_dgs(dgs_network_path):
    # Read DGS
    with warnings.catch_warnings():
        if dgs_network_path.stem == "Line_Without_Type":
            warnings.filterwarnings("ignore", message=r".*is missing line types", category=UserWarning)
        en = ElectricalNetwork.from_dgs_file(dgs_network_path)
        # Also make sure use_name_as_id=True works
        en2 = ElectricalNetwork.from_dgs_file(dgs_network_path, use_name_as_id=True)
    assert len(en2.buses) == len(en.buses)
    assert len(en2.lines) == len(en.lines)
    assert len(en2.loads) == len(en.loads)
    assert len(en2.sources) == len(en.sources)
    assert len(en2.transformers) == len(en.transformers)
    assert len(en2.switches) == len(en.switches)
    assert len(en2.potential_refs) == len(en.potential_refs)
    assert len(en2.grounds) == len(en.grounds)
    assert len(en2.ground_connections) == len(en.ground_connections)

    # Check the validity of the network
    en._check_validity(constructed=False)

    pref_ids = set(en.potential_refs)
    source_id = next(iter(en.sources))

    # Check that if there is a ground, it is always used as potential ref
    if "pref (ground)" in pref_ids:
        assert en.grounds
    else:
        assert not en.grounds

    # Check the created potential refs
    match dgs_network_path.stem:
        case "MV_LV_Transformer_LV_grid" | "MV_LV_Transformer_unbalanced" | "MV_LV_Transformer" | "Full_Example":
            # MV/LV networks => ground on the LV side and no ground on the MV side
            assert pref_ids == {"pref (ground)", f"pref (source '{source_id}')"}, pref_ids
        case "MV_Network" | "Switch":
            # MV network: no neutral conductor (and no lines shunt here) => no ground
            assert pref_ids == {f"pref (source '{source_id}')"}, pref_ids
        case _:
            # All other test networks have lines with shunt => ground
            assert pref_ids == {"pref (ground)"}, pref_ids


def test_from_dgs_no_line_type(dgs_special_networks_dir):
    path = dgs_special_networks_dir / "Line_Without_Type.json"

    dgs_json = json.loads(path.read_bytes())
    assert "ElmLne" in dgs_json
    assert "TypLne" not in dgs_json
    elm_lne = pd.DataFrame(data=dgs_json["ElmLne"]["Values"], columns=dgs_json["ElmLne"]["Attributes"]).set_index("FID")

    expected_msg = (
        r"The network contains lines but it is missing line types \(TypLne\)\. "
        r"Please copy all line types from the library to the project before "
        r"exporting otherwise a LineParameter object will be created for each line."
    )
    with pytest.warns(UserWarning, match=expected_msg):
        en = ElectricalNetwork.from_dgs_file(path)
    en._check_validity(constructed=False)

    assert len(en.lines) == 1
    assert len(en.transformers) == 0
    assert len(en.switches) == 0
    line_id = elm_lne.index[0]
    line = en.lines[line_id]
    assert isinstance(line, Line)
    assert line.parameters.id == f"line {line.id!r}"
    assert line.length.m == elm_lne.at[line.id, "dline"]
    assert line.length.m == 10
    # Test impedances with line length taken into account
    zs, zm = line.z_line.m[0, :2]  # series and mutual components
    r0, r1 = elm_lne.at[line_id, "R0"], elm_lne.at[line_id, "R1"]
    x0, x1 = elm_lne.at[line_id, "X0"], elm_lne.at[line_id, "X1"]
    npt.assert_allclose(zs.real, (r0 + 2 * r1) / 3)
    npt.assert_allclose(zs.imag, (x0 + 2 * x1) / 3)
    npt.assert_allclose(zm.real, (r0 - r1) / 3)
    npt.assert_allclose(zm.imag, (x0 - x1) / 3)
    npt.assert_allclose(line.parameters.z_line.m, line.z_line.m / line.length.m)


def test_dgs_general_load_input_modes(dgs_special_networks_dir):
    path = dgs_special_networks_dir / "General_Load.json"
    data = json.loads(path.read_bytes())
    elm_lod = dgs_dict_to_df(data, "ElmLod", index_col="FID")
    load_id = elm_lod.index[0]
    assert elm_lod.at[load_id, "mode_inp"] == "DEF"
    expected_powers = compute_3phase_load_powers(elm_lod, load_id, i_sym=0, factor=1, load_type="General")
    for mode_inp in GENERAL_LOAD_INPUT_MODE:
        elm_lod.at[load_id, "mode_inp"] = mode_inp
        try:
            powers = compute_3phase_load_powers(elm_lod, load_id, i_sym=0, factor=1, load_type="General")
        except NotImplementedError:
            continue
        npt.assert_allclose(powers, expected_powers, atol=1e-5, err_msg=f"Input Mode: {mode_inp!r}")


def test_dgs_switches(dgs_special_networks_dir, tmp_path):
    path = dgs_special_networks_dir / "Switch.json"
    good_json = json.loads(path.read_bytes())

    with warnings.catch_warnings(action="error"):  # Make sure there is no warning
        en = ElectricalNetwork.from_dgs_file(path)

    assert len(en.switches) == 1
    switch = next(iter(en.switches.values()))
    assert switch.phases == "abc"
    assert switch.closed

    source = next(iter(en.sources.values()))
    load = next(iter(en.loads.values()))
    assert switch.bus1 is source.bus
    assert switch.bus2 is load.bus

    bad_path = tmp_path / "Bad_Switch.json"

    # Error on wrong nphase
    bad_json = copy.deepcopy(good_json)
    bad_json["ElmCoup"]["Values"][0][bad_json["ElmCoup"]["Attributes"].index("nphase")] = 2
    bad_path.write_text(json.dumps(bad_json))
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_dgs_file(bad_path)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER
    assert e.value.msg == "nphase=2 for switch '2' is not supported. Only 3-phase switches are currently supported."

    # Parse open switch
    switch_attrs = good_json["ElmCoup"]["Attributes"]
    new_switch = good_json["ElmCoup"]["Values"][0].copy()
    new_switch[switch_attrs.index("FID")] = "1000"
    new_switch[switch_attrs.index("loc_name")] = "Open Switch"
    assert new_switch[switch_attrs.index("on_off")] == 1
    new_switch[switch_attrs.index("on_off")] = 0  # Open the switch
    open_switch_json = copy.deepcopy(good_json)
    open_switch_json["ElmCoup"]["Values"].append(new_switch)
    open_switch_path = tmp_path / "Open_Switch.json"
    open_switch_path.write_text(json.dumps(open_switch_json))
    en2 = ElectricalNetwork.from_dgs_file(open_switch_path)
    assert len(en2.switches) == 2
    open_switch = en2.switches["1000"]
    assert not open_switch.closed


def test_generate_typ_lne_errors(monkeypatch):
    # Small number of conductor (not in (3, 4)
    typ_line = pd.DataFrame(
        data={"loc_name": "lt1", "nneutral": [0], "nlnph": [1]},
        index=pd.Index(["1"], name="FID"),
    )
    with pytest.raises(RoseauLoadFlowException) as e:
        typ_lne_to_lp(typ_lne=typ_line, line_params={}, use_name_as_id=False)
    assert e.value.msg == (
        "The number of phases (1) of line type with FID='1' and loc_name='lt1' cannot be handled, it should be 3 or 4."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER

    # Too large impedance/shunt admittance matrices generated
    typ_line = pd.DataFrame(
        data={
            "loc_name": "lt2",
            "nneutral": [0],
            "nlnph": [3],
            "cohl_": [0],
            "mlei": ["Cu"],
            "imiso": [0],
            "rline": [0.188],
            "xline": [0.3283],
            "lline": [1.045011],
            "rline0": [0.188],
            "xline0": [0.3283],
            "lline0": [1.045011],
            "rnline": [0],
            "xnline": [0],
            "lnline": [0],
            "rpnline": [0],
            "xpnline": [0],
            "lpnline": [0],
            "gline0": [0],
            "bline0": [0],
            "gline": [0],
            "bline": [0],
        },
        index=pd.Index(["2"], name="FID"),
    )

    def _sym_to_zy_good(*args, **kwargs):
        return np.diag(np.array([1, 2, 3, 4, 5], dtype=complex)), np.diag(np.array([1, 2, 3, 4, 5], dtype=complex))

    with monkeypatch.context() as m:
        m.setattr("roseau.load_flow.io.dgs.lines.LineParameters._sym_to_zy", _sym_to_zy_good)
        line_params = {}
        typ_lne_to_lp(typ_lne=typ_line, line_params=line_params, use_name_as_id=False)
    npt.assert_allclose(line_params["2"].z_line.m, np.diag(np.array([1, 2, 3], dtype=complex)))
    npt.assert_allclose(line_params["2"].y_shunt.m, np.diag(np.array([1, 2, 3], dtype=complex)))

    # Too small matrices
    def _sym_to_zy_bad(*args, **kwargs):
        return np.eye(N=2, dtype=complex), np.eye(N=2, dtype=complex)

    with monkeypatch.context() as m:
        m.setattr("roseau.load_flow.io.dgs.lines.LineParameters._sym_to_zy", _sym_to_zy_bad)
        with pytest.raises(RoseauLoadFlowException) as e:
            typ_lne_to_lp(typ_lne=typ_line, line_params={}, use_name_as_id=False)
        assert e.value.msg == (
            "A 3x3 impedance matrix was expected for the line type with FID='2' and loc_name='lt2' but a 2x2 matrix was generated."
        )
        assert e.value.code == RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER


def test_use_name_as_id(dgs_networks_dir, tmp_path):
    dgs_path = dgs_networks_dir / "Full_Example.json"
    dgs_data = json.loads(dgs_path.read_bytes())
    en_fid = ElectricalNetwork.from_dgs_file(dgs_path, use_name_as_id=False)
    en_name = ElectricalNetwork.from_dgs_file(dgs_path, use_name_as_id=True)

    elm_term = dgs_dict_to_df(dgs_data, "ElmTerm", index_col="FID")["loc_name"].to_dict()
    typ_lne = dgs_dict_to_df(dgs_data, "TypLne", index_col="FID")["loc_name"].to_dict()
    typ_tr2 = dgs_dict_to_df(dgs_data, "TypTr2", index_col="FID")["loc_name"].to_dict()

    lp_fid = {line.parameters.id: line.parameters for line in en_fid.lines.values()}
    lp_name = {line.parameters.id: line.parameters for line in en_name.lines.values()}
    tp_fid = {tr.parameters.id: tr.parameters for tr in en_fid.transformers.values()}
    tp_name = {tr.parameters.id: tr.parameters for tr in en_name.transformers.values()}

    # Basic checks for buses and types
    for bus_fid in en_fid.buses:
        assert elm_term[bus_fid] in en_name.buses
    for typ_lne_fid in lp_fid:
        assert typ_lne[typ_lne_fid] in lp_name
    for typ_tr2_fid in tp_fid:
        assert typ_tr2[typ_tr2_fid] in tp_name

    # Check that elements are assigned the correct buses and types
    elm_lne = dgs_dict_to_df(dgs_data, "ElmLne", index_col="FID")["loc_name"].to_dict()
    for line_fid in en_fid.lines.values():
        line_name = en_name.lines[elm_lne[line_fid.id]]
        assert line_name.parameters.id == typ_lne[line_fid.parameters.id]
        assert line_name.bus1.id == elm_term[line_fid.bus1.id]
        assert line_name.bus2.id == elm_term[line_fid.bus2.id]
    elm_tr2 = dgs_dict_to_df(dgs_data, "ElmTr2", index_col="FID")["loc_name"].to_dict()
    for tr_fid in en_fid.transformers.values():
        tr_name = en_name.transformers[elm_tr2[tr_fid.id]]
        assert tr_name.parameters.id == typ_tr2[tr_fid.parameters.id]
        assert tr_name.bus_hv.id == elm_term[tr_fid.bus_hv.id]
        assert tr_name.bus_lv.id == elm_term[tr_fid.bus_lv.id]
    elm_lod = (
        dgs_dict_to_df(dgs_data, "ElmLodLV", index_col="FID")["loc_name"].to_dict()
        | dgs_dict_to_df(dgs_data, "ElmLodmv", index_col="FID")["loc_name"].to_dict()
        | dgs_dict_to_df(dgs_data, "ElmPvsys", index_col="FID")["loc_name"].to_dict()
    )
    for load_fid in en_fid.loads.values():
        load_name = en_name.loads[elm_lod[load_fid.id]]
        assert load_name.bus.id == elm_term[load_fid.bus.id]
    elm_xnet = dgs_dict_to_df(dgs_data, "ElmXnet", index_col="FID")["loc_name"].to_dict()
    for source_fid in en_fid.sources.values():
        source_name = en_name.sources[elm_xnet[source_fid.id]]
        assert source_name.bus.id == elm_term[source_fid.bus.id]

    # Duplicate bus ID
    dgs_data = json.loads(dgs_path.read_bytes())
    bus_name_index = dgs_data["ElmTerm"]["Attributes"].index("loc_name")
    for bus in dgs_data["ElmTerm"]["Values"][:2]:
        bus[bus_name_index] = "Duplicate Bus"
    bad_path = tmp_path / "Bad_Duplicate_Bus.json"
    bad_path.write_text(json.dumps(dgs_data))
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_dgs_file(bad_path, use_name_as_id=True)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NON_UNIQUE_NAME
    assert e.value.msg == "ElmTerm has non-unique loc_name values, cannot use them as IDs."

    # Duplicate line ID
    dgs_data = json.loads(dgs_path.read_bytes())
    line_name_index = dgs_data["ElmLne"]["Attributes"].index("loc_name")
    for line in dgs_data["ElmLne"]["Values"]:
        line[line_name_index] = "Duplicate Line"
    bad_path = tmp_path / "Bad_Duplicate_Line.json"
    bad_path.write_text(json.dumps(dgs_data))
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_dgs_file(bad_path, use_name_as_id=True)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NON_UNIQUE_NAME
    assert e.value.msg == "ElmLne has non-unique loc_name values, cannot use them as IDs."


def _dgs_rows(data: dict, cls: str) -> list[dict]:
    table = data[cls]
    return [dict(zip(table["Attributes"], values, strict=True)) for values in table["Values"]]


def _max_voltage_deviation(data: dict, en: ElectricalNetwork, line_to_line: bool) -> float:
    """The largest deviation (p.u.) between the voltages of the buses and those of PowerFactory:
    phase-to-ground for a four-wire network, line-to-line for a three-wire one."""
    deviation = 0.0
    for term in _dgs_rows(data, "ElmTerm"):
        base = term["uknom"] * 1e3 / np.sqrt(3)
        expected = np.array([complex(term[f"m:ur:{p}"] or 0, term[f"m:ui:{p}"] or 0) for p in "ABC"])
        actual = en.buses[term["loc_name"]].res_potentials.m[:3] / base
        if line_to_line:
            expected, actual = expected - np.roll(expected, -1), actual - np.roll(actual, -1)
        deviation = max(deviation, np.abs(expected - actual).max())
    return deviation


@pytest.mark.no_patch_engine
@pytest.mark.parametrize(
    ("name", "voltage_tolerance", "tap_tolerance"),
    (
        ("Star_3x1_103", 1e-3, 1e-3),
        ("Star_3x1_120", 1.5e-3, 1e-6),
        ("Star_3x1_103_Unbalanced", 1.5e-2, 1e-6),
        ("Star_3x1_103_Unbalanced_Separate_Star_Point", 3e-2, 5e-3),
        ("Closed_Delta_Lagging_103", 2e-3, 1e-3),
        ("Closed_Delta_Leading_103", 2e-3, 1e-3),
        ("Closed_Delta_Lagging_120", 2.5e-3, 1e-6),
    ),
)
def test_dgs_regulators_match_power_factory(dgs_regulators_networks_dir, name, voltage_tolerance, tap_tolerance):
    """The voltages and taps match PowerFactory's within its own regulation tolerance (it stops
    within about 0.07 % of the setpoint, while the continuous controller reaches it exactly). The
    unbalanced cases run at about 7 times the rating, where the position of the series impedance
    (source side in PowerFactory, load side here) is no longer negligible."""
    path = dgs_regulators_networks_dir / "multi" / f"{name}.json"
    data = json.loads(path.read_text())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        en = ElectricalNetwork.from_dgs_file(path, use_name_as_id=True)
    en.solve_load_flow()
    regulator = en.regulators["Step-Voltage Regulator"]
    assert _max_voltage_deviation(data, en, line_to_line=regulator.parameters.is_delta) < voltage_tolerance

    # PowerFactory's tap ratio of each unit (`1 + n·dutap`), `c:nntap1..3` being the units of the
    # phases A, B and C. PowerFactory does not always export `c:nntap1`.
    (typ,) = _dgs_rows(data, "TypVoltreg")
    (elm,) = _dgs_rows(data, "ElmVoltreg")
    if typ["config"] == 3:
        pairs = ("ca", "ab", "bc") if typ["cldeltacn"] == 1 else ("ab", "bc", "ca")
    else:
        pairs = ("an", "bn", "cn")
    taps = dict(zip(regulator.tap_phases, regulator.res_taps.tolist(), strict=True))
    for pair, field in zip(pairs, ("c:nntap1", "c:nntap2", "c:nntap3"), strict=True):
        if elm.get(field) is not None:
            assert abs(taps[pair] - (1 + elm[field] * typ["dutap"] / 100)) < tap_tolerance, pair


def test_dgs_regulator_shapes_and_earthing(dgs_regulators_networks_dir):
    def read(name: str) -> ElectricalNetwork:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ElectricalNetwork.from_dgs_file(
                dgs_regulators_networks_dir / "multi" / f"{name}.json", use_name_as_id=True
            )

    # Star: phases "abcn", wye connection
    en = read("Star_3x1_103")
    regulator = en.regulators["Step-Voltage Regulator"]
    assert regulator.phases == "abcn"
    assert regulator.parameters.connection == "wye"
    assert regulator.u_ref.m == 1.03
    assert regulator.parameters.id == "Step-Voltage Regulator Type"
    np.testing.assert_allclose(regulator.parameters.sn.m, np.sqrt(3) * 20e3 * 300, rtol=1e-6)  # Un is rounded
    np.testing.assert_allclose(regulator.parameters.un.m, 20e3, rtol=1e-6)
    assert regulator.parameters.u_range == 0.1

    # Closed deltas
    en = read("Closed_Delta_Lagging_103")
    regulator = en.regulators["Step-Voltage Regulator"]
    assert regulator.phases == "abc"
    assert regulator.parameters.connection == "delta_positive_rotation"
    assert not en.ground_connections  # Three-wire network
    en = read("Closed_Delta_Leading_103")
    assert en.regulators["Step-Voltage Regulator"].parameters.connection == "delta_negative_rotation"

    # `iintgnd = 1`: the external grid earths the neutral of its bus, the regulator its own
    # source-side neutral
    en = read("Star_3x1_103_Unbalanced")
    earthed = sorted((gc.element.id, gc.phase) for gc in en.ground_connections.values())
    assert earthed == [("Terminal1", "n"), ("Terminal2", "n")]

    # `iintgnd = 0`: the external grid earths its own floating neutral, the neutral of its bus is
    # only earthed by the regulator
    en = read("Star_3x1_103_Unbalanced_Separate_Star_Point")
    source = en.sources["External Grid"]
    assert source.has_floating_neutral
    earthed = sorted((type(gc.element).__name__, gc.element.id) for gc in en.ground_connections.values())
    assert earthed == [("Bus", "Terminal2"), ("VoltageSource", "External Grid")]


def test_dgs_unsupported_regulators(dgs_regulators_networks_dir):
    # Fixed taps (no automatic tap changing)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_dgs_file(dgs_regulators_networks_dir / "multi" / "Closed_Delta_Lagging_Fixed_Tap.json")
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED
    assert "no automatic tap changing" in e.value.msg

    data = json.loads((dgs_regulators_networks_dir / "multi" / "Closed_Delta_Lagging_103.json").read_text())
    config_index = data["TypVoltreg"]["Attributes"].index("config")

    # An open delta
    data_open_delta = copy.deepcopy(data)
    data_open_delta["TypVoltreg"]["Values"][0][config_index] = 4
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_dgs_dict(data_open_delta)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED
    assert "configuration 4" in e.value.msg

    # A star regulator on terminals without neutral
    data_star = copy.deepcopy(data)
    data_star["TypVoltreg"]["Values"][0][config_index] = 2
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_dgs_dict(data_star)
    assert e.value.code == RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY


@pytest.mark.no_patch_engine
@pytest.mark.parametrize("name", ("LV_Line", "LV_network"))
def test_dgs_external_grid_earthing(dgs_networks_dir, name):
    """The earthed star point of the external grid earths the neutral of its terminal (as in
    PowerFactory): the voltages match PowerFactory's."""
    path = dgs_networks_dir / f"{name}.json"
    data = json.loads(path.read_text())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        en = ElectricalNetwork.from_dgs_file(path, use_name_as_id=True)
    assert any(gc.element.id == next(iter(en.sources.values())).bus.id for gc in en.ground_connections.values())
    en.solve_load_flow()
    assert _max_voltage_deviation(data, en, line_to_line=False) < 1e-4
