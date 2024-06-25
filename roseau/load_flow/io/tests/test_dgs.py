import json
import warnings

import numpy as np
import pandas as pd
import pytest

from roseau.load_flow.io.dgs import _dgs_dict_to_df
from roseau.load_flow.io.dgs.constants import GENERAL_LOAD_INPUT_MODE
from roseau.load_flow.io.dgs.loads import compute_3phase_load_powers
from roseau.load_flow.models import Line
from roseau.load_flow.network import ElectricalNetwork


def test_from_dgs(dgs_network_path):
    # Read DGS
    with warnings.catch_warnings():
        if dgs_network_path.stem == "Line_Without_Type":
            warnings.filterwarnings("ignore", message=r".*is missing line types", category=UserWarning)
        en = ElectricalNetwork.from_dgs(dgs_network_path)
    # Check the validity of the network
    en._check_validity(constructed=False)


def test_from_dgs_no_line_type(dgs_special_network_dir):
    path = dgs_special_network_dir / "Line_Without_Type.json"

    dgs_json = json.loads(path.read_bytes())
    assert "ElmLne" in dgs_json
    assert "TypLne" not in dgs_json
    elm_lne = pd.DataFrame(data=dgs_json["ElmLne"]["Values"], columns=dgs_json["ElmLne"]["Attributes"]).set_index("FID")

    expected_msg = (
        r"The network contains lines but is missing line types \(TypLne\)\. "
        r"Please copy all line types from the library to the project before "
        r"exporting otherwise a LineParameter object will be created for each line."
    )
    with pytest.warns(UserWarning, match=expected_msg):
        en = ElectricalNetwork.from_dgs(path)
    en._check_validity(constructed=False)

    assert len(en.branches) == 1
    line_id = elm_lne.index[0]
    line = en.branches[line_id]
    assert isinstance(line, Line)
    assert line.parameters.id == f"line {line.id!r}"
    assert line.length.m == elm_lne.at[line.id, "dline"]
    assert line.length.m == 10
    # Test impedances with line length taken into account
    zs, zm = line.z_line.m[0, :2]  # series and mutual components
    r0, r1 = elm_lne.at[line_id, "R0"], elm_lne.at[line_id, "R1"]
    x0, x1 = elm_lne.at[line_id, "X0"], elm_lne.at[line_id, "X1"]
    np.testing.assert_allclose(zs.real, (r0 + 2 * r1) / 3)
    np.testing.assert_allclose(zs.imag, (x0 + 2 * x1) / 3)
    np.testing.assert_allclose(zm.real, (r0 - r1) / 3)
    np.testing.assert_allclose(zm.imag, (x0 - x1) / 3)
    np.testing.assert_allclose(line.parameters.z_line.m, line.z_line.m / line.length.m)


def test_dgs_general_load_input_modes(dgs_special_network_dir):
    path = dgs_special_network_dir / "General_Load.json"
    data = json.loads(path.read_bytes())
    elm_lod = _dgs_dict_to_df(data, "ElmLod")
    load_id = elm_lod.index[0]
    assert elm_lod.at[load_id, "mode_inp"] == "DEF"
    expected_powers = compute_3phase_load_powers(elm_lod, load_id, i_sym=0, factor=1, load_type="General")
    for mode_inp in GENERAL_LOAD_INPUT_MODE:
        elm_lod.at[load_id, "mode_inp"] = mode_inp
        try:
            powers = compute_3phase_load_powers(elm_lod, load_id, i_sym=0, factor=1, load_type="General")
        except NotImplementedError:
            continue
        np.testing.assert_allclose(powers, expected_powers, atol=1e-5, err_msg=f"Input Mode: {mode_inp!r}")
