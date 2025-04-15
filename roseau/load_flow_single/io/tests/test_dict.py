import copy
import hashlib
import json
import warnings
from importlib import resources

import numpy as np
import pytest
from shapely import LineString, Point

import roseau.load_flow_single as rlfs
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow_single.io.dict import NETWORK_JSON_VERSION, v3_to_v4_converter

# Store the expected hashes of the files that should not be modified
EXPECTED_HASHES = {
    "network_json_v3.json": "d38c827b85f143f7a6a31ff5112a74cd",
}


def read_json_file(filename: str) -> str:
    return (resources.files("roseau.load_flow_single.io") / "tests" / "data" / filename).read_text()


def remove_results(obj: object, /) -> None:
    """Recursively remove the 'results' key from a JSON structure."""
    if isinstance(obj, dict):
        if "results" in obj:
            del obj["results"]
        for v in obj.values():
            remove_results(v)
    elif isinstance(obj, list):
        for x in obj:
            remove_results(x)


def test_to_dict():
    vn = 400
    source_bus = rlfs.Bus(id="source", geometry=Point(0.0, 0.0), min_voltage_level=0.9, nominal_voltage=vn)
    load_bus = rlfs.Bus(id="load bus", geometry=Point(0.0, 1.0), max_voltage_level=1.1, nominal_voltage=vn)
    vs = rlfs.VoltageSource(id="vs", bus=source_bus, voltage=vn)

    # Same id, different line parameters -> fail
    lp1 = rlfs.LineParameters(
        id="test",
        z_line=1,
        y_shunt=1,
        line_type=rlfs.LineType.UNDERGROUND,
        material=rlfs.Material.AA,
        insulator=rlfs.Insulator.PVC,
        section=120,
    )

    geom = LineString([(0.0, 0.0), (0.0, 1.0)])
    line1 = rlfs.Line(id="line1", bus1=source_bus, bus2=load_bus, parameters=lp1, length=10, geometry=geom)
    line2 = rlfs.Line(id="line2", bus1=source_bus, bus2=load_bus, parameters=lp1, length=10, geometry=geom)
    en = rlfs.ElectricalNetwork(
        buses=[source_bus, load_bus],
        lines=[line1, line2],
        transformers=[],
        switches=[],
        loads=[],
        sources=[vs],
    )

    # Dict content
    lp1.ampacity = 1000
    res = en.to_dict(include_results=False)
    res_bus0, res_bus1 = res["buses"]
    res_line0, res_line1 = res["lines"]
    assert "geometry" in res_bus0
    assert "geometry" in res_bus1
    assert "geometry" in res_line0
    assert "geometry" in res_line1
    assert np.isclose(res_bus0["nominal_voltage"], 400.0)
    assert np.isclose(res_bus0["min_voltage_level"], 0.9)
    assert np.isclose(res_bus1["nominal_voltage"], 400.0)
    assert np.isclose(res_bus1["max_voltage_level"], 1.1)
    lp_dict = res["lines_params"][0]
    assert np.isclose(lp_dict["ampacity"], 1000)
    assert lp_dict["line_type"] == "UNDERGROUND"
    assert lp_dict["material"] == "ACSR"
    assert lp_dict["insulator"] == "PVC"
    assert np.isclose(lp_dict["section"], 120)
    assert "results" not in res_bus0
    assert "results" not in res_bus1
    assert "results" not in res_line0
    assert "results" not in res_line1

    # Same id, different transformer parameters -> fail
    vn = 400
    geom = Point(0.0, 0.0)
    source_bus = rlfs.Bus(id="source", geometry=geom)
    load_bus = rlfs.Bus(id="load bus", geometry=geom)
    vs = rlfs.VoltageSource(id="vs", bus=source_bus, voltage=vn)

    # Same id, different transformer parameters -> fail
    tp1 = rlfs.TransformerParameters.from_open_and_short_circuit_tests(
        id="t", vg="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer1 = rlfs.Transformer(
        id="Transformer1", bus_hv=source_bus, bus_lv=load_bus, parameters=tp1, geometry=geom
    )
    transformer2 = rlfs.Transformer(
        id="Transformer2", bus_hv=source_bus, bus_lv=load_bus, parameters=tp1, geometry=geom
    )
    en = rlfs.ElectricalNetwork(
        buses=[source_bus, load_bus],
        lines=[],
        transformers=[transformer1, transformer2],
        switches=[],
        loads=[],
        sources=[vs],
    )

    # Dict content
    res = en.to_dict(include_results=False)
    assert "geometry" in res["buses"][0]
    assert "geometry" in res["buses"][1]
    assert "geometry" in res["transformers"][0]
    assert "geometry" in res["transformers"][1]


def test_from_dict_errors():
    with pytest.raises(
        AssertionError,
        match=(
            r"Trying to import a multi-phase network as a single-phase network. Did you mean to use "
            r"`rlf\.ElectricalNetwork` instead of `rlfs\.ElectricalNetwork`\?"
        ),
    ):
        rlfs.ElectricalNetwork.from_dict(data={"version": 2, "is_multiphase": True})

    with pytest.raises(AssertionError, match=r"Unsupported network file version 2, expected >=3"):
        rlfs.ElectricalNetwork.from_dict(data={"version": 2, "is_multiphase": False})
    with pytest.raises(AssertionError, match=r"Unsupported network file version \d+, expected <=\d+"):
        rlfs.ElectricalNetwork.from_dict(data={"version": NETWORK_JSON_VERSION + 1, "is_multiphase": False})


def test_all_converters():
    from roseau.load_flow_single.io.tests.data.network_json_v3 import en

    dict_v3 = json.loads(read_json_file("network_json_v3.json"))
    net_dict = en.to_dict(include_results=False)
    expected_dict = copy.deepcopy(dict_v3)
    remove_results(expected_dict)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        expected_dict = v3_to_v4_converter(expected_dict)
    assert_json_close(net_dict, expected_dict)


def test_from_dict_v3():
    dict_v3 = json.loads(read_json_file("network_json_v3.json"))

    with pytest.warns(UserWarning, match=r"Got an outdated network file \(version 3\)"):
        en = rlfs.ElectricalNetwork.from_dict(data=dict_v3, include_results=True)
    net_dict = en.to_dict(include_results=True)
    expected_dict = copy.deepcopy(dict_v3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        expected_dict = v3_to_v4_converter(expected_dict)

    assert_json_close(net_dict, expected_dict)


@pytest.mark.parametrize("version", list(range(3, NETWORK_JSON_VERSION)))
def test_json_files_not_modified(version):
    """Test that the JSON files have not been modified when refactoring the code."""
    filename = f"network_json_v{version}.json"
    dict_data = read_json_file(filename)
    digest = hashlib.md5(dict_data.encode()).hexdigest()
    if filename not in EXPECTED_HASHES:
        # Add the computed hash to EXPECTED_HASHES (after formatting the file with prettier)
        raise AssertionError(f"Hash of '{filename}' is not in EXPECTED_HASHES.\nComputed hash: {digest}")
    elif EXPECTED_HASHES[filename] != digest:
        raise AssertionError(
            f"Hash of '{filename}' has changed. Do not change the content of this file or update the hash "
            f"for formatting-only changes.\nExpected hash: {EXPECTED_HASHES[filename]}\nComputed hash: {digest}"
        )
