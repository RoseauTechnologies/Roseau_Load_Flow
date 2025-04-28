import copy
import hashlib
import importlib.resources as resources
import json
import warnings

import numpy as np
import pytest
from pyproj import CRS
from shapely import LineString, Point

from roseau.load_flow.io.dict import (
    NETWORK_JSON_VERSION,
    v0_to_v1_converter,
    v1_to_v2_converter,
    v2_to_v3_converter,
    v3_to_v4_converter,
    v4_to_v5_converter,
)
from roseau.load_flow.models import (
    Bus,
    Ground,
    GroundConnection,
    Line,
    LineParameters,
    PotentialRef,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow.types import Insulator, LineType, Material

# Store the expected hashes of the files that should not be modified
EXPECTED_HASHES = {
    "network_json_v0.json": "ad984cbcd26b36602a2789e2f0badcb5",
    "network_json_v1.json": "fc930431b69165f68961b0f0dc2635b5",
    "network_json_v2.json": "d85a2658708576c083ceab666a83150b",
    "network_json_v3.json": "551f852aefc71d744f4738d31bd0e90b",
    "network_json_v4.json": "6c1af7193a771488df4c8b2c476a1ef9",
}


def read_json_file(filename: str) -> str:
    return (resources.files("roseau.load_flow.io") / "tests" / "data" / filename).read_text()


def ignore_unmatched_warnings(warn_check, /) -> None:
    """Ignore unmatched warnings in the pytest.warns context manager."""
    for w in warn_check:
        if not warn_check.matches(w):
            warn_check.list.remove(w)


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
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    source_bus = Bus(id="source", phases="abcn", geometry=Point(0.0, 0.0), min_voltage_level=0.9, nominal_voltage=400)
    load_bus = Bus(id="load bus", phases="abcn", geometry=Point(0.0, 1.0), max_voltage_level=1.1, nominal_voltage=400)
    gc = GroundConnection(id="gc", ground=ground, element=load_bus)
    p_ref = PotentialRef(id="pref", element=ground)
    vs = VoltageSource(id="vs", bus=source_bus, phases="abcn", voltages=vn)

    # Same id, different line parameters -> fail
    lp1 = LineParameters(
        id="test",
        z_line=np.eye(4, dtype=complex),
        y_shunt=np.eye(4, dtype=complex),
        line_type=LineType.UNDERGROUND,
        materials=Material.AA,
        insulators=Insulator.PVC,
        sections=120,
    )

    geom = LineString([(0.0, 0.0), (0.0, 1.0)])
    line1 = Line(
        id="line1",
        bus1=source_bus,
        bus2=load_bus,
        phases="abcn",
        ground=ground,
        parameters=lp1,
        length=10,
        geometry=geom,
    )
    line2 = Line(
        id="line2",
        bus1=source_bus,
        bus2=load_bus,
        phases="abcn",
        ground=ground,
        parameters=lp1,
        length=10,
        geometry=geom,
    )
    en = ElectricalNetwork(
        buses=[source_bus, load_bus],
        lines=[line1, line2],
        transformers=[],
        switches=[],
        loads=[],
        sources=[vs],
        grounds=[ground],
        potential_refs=[p_ref],
        ground_connections=[gc],
    )

    # Dict content
    lp1.ampacities = 1000
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
    assert np.allclose(lp_dict["ampacities"], 1000)
    assert lp_dict["line_type"] == "UNDERGROUND"
    assert lp_dict["materials"] == ["ACSR"] * 4
    assert lp_dict["insulators"] == ["PVC"] * 4
    assert np.allclose(lp_dict["sections"], 120)
    assert "results" not in res_bus0
    assert "results" not in res_bus1
    assert "results" not in res_line0
    assert "results" not in res_line1

    # Same id, different transformer parameters -> fail
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    geom = Point(0.0, 0.0)
    source_bus = Bus(id="source", phases="abcn", geometry=geom)
    load_bus = Bus(id="load bus", phases="abcn", geometry=geom)
    gc_load = GroundConnection(id="gc_load", ground=ground, element=load_bus)
    gc_source = GroundConnection(id="gc_source", ground=ground, element=source_bus)
    p_ref = PotentialRef(id="pref", element=ground)
    vs = VoltageSource(id="vs", bus=source_bus, phases="abcn", voltages=vn)

    # Same id, different transformer parameters -> fail
    tp1 = TransformerParameters.from_open_and_short_circuit_tests(
        id="t", vg="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer1 = Transformer(id="Transformer1", bus_hv=source_bus, bus_lv=load_bus, parameters=tp1, geometry=geom)
    transformer2 = Transformer(id="Transformer2", bus_hv=source_bus, bus_lv=load_bus, parameters=tp1, geometry=geom)
    en = ElectricalNetwork(
        buses=[source_bus, load_bus],
        lines=[],
        transformers=[transformer1, transformer2],
        switches=[],
        loads=[],
        sources=[vs],
        grounds=[ground],
        potential_refs=[p_ref],
        ground_connections=[gc_load, gc_source],
    )

    # Dict content
    res = en.to_dict(include_results=False)
    assert "geometry" in res["buses"][0]
    assert "geometry" in res["buses"][1]
    assert "geometry" in res["transformers"][0]
    assert "geometry" in res["transformers"][1]


def test_all_converters():
    from roseau.load_flow.io.tests.data.network_json_v0 import en

    dict_v0 = json.loads(read_json_file("network_json_v0.json"))
    net_dict = en.to_dict(include_results=False)
    expected_dict = copy.deepcopy(dict_v0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        expected_dict = v0_to_v1_converter(expected_dict)
        expected_dict = v1_to_v2_converter(expected_dict)
        expected_dict = v2_to_v3_converter(expected_dict)
        expected_dict = v3_to_v4_converter(expected_dict)
        expected_dict = v4_to_v5_converter(expected_dict)
    assert_json_close(net_dict, expected_dict)


def test_from_dict_v0():
    dict_v0 = json.loads(read_json_file("network_json_v0.json"))

    with pytest.warns(UserWarning, match=r"Got an outdated network file \(version 0\)") as warn_check:
        en = ElectricalNetwork.from_dict(data=dict_v0, include_results=False)
        ignore_unmatched_warnings(warn_check)
    net_dict = en.to_dict(include_results=False)
    expected_dict = copy.deepcopy(dict_v0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        expected_dict = v0_to_v1_converter(expected_dict)
        expected_dict = v1_to_v2_converter(expected_dict)
        expected_dict = v2_to_v3_converter(expected_dict)
        expected_dict = v3_to_v4_converter(expected_dict)
        expected_dict = v4_to_v5_converter(expected_dict)
    assert_json_close(net_dict, expected_dict)


def test_from_dict_v1():
    dict_v1 = json.loads(read_json_file("network_json_v1.json"))

    with pytest.warns(UserWarning, match=r"Got an outdated network file \(version 1\)") as warn_check:
        en = ElectricalNetwork.from_dict(data=dict_v1, include_results=True)
        ignore_unmatched_warnings(warn_check)
    net_dict = en.to_dict(include_results=True)
    expected_dict = copy.deepcopy(dict_v1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        expected_dict = v1_to_v2_converter(expected_dict)
        expected_dict = v2_to_v3_converter(expected_dict)
        expected_dict = v3_to_v4_converter(expected_dict)
        expected_dict = v4_to_v5_converter(expected_dict)
    assert_json_close(net_dict, expected_dict)

    # Test with `include_results=False`
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        net = ElectricalNetwork.from_dict(data=dict_v1, include_results=False)
        net_dict = net.to_dict(include_results=False)
        expected_dict_no_results = copy.deepcopy(dict_v1)
        remove_results(expected_dict_no_results)
        expected_dict_no_results = v1_to_v2_converter(expected_dict_no_results)
        expected_dict_no_results = v2_to_v3_converter(expected_dict_no_results)
        expected_dict_no_results = v3_to_v4_converter(expected_dict_no_results)
        expected_dict_no_results = v4_to_v5_converter(expected_dict_no_results)
    assert_json_close(net_dict, expected_dict_no_results)


def test_from_dict_v2():
    dict_v2 = json.loads(read_json_file("network_json_v2.json"))

    with (
        pytest.warns(UserWarning, match=r"Got an outdated network file \(version 2\)"),
        pytest.warns(
            UserWarning,
            match=(
                r"Starting with version 0.11.0 of roseau-load-flow \(JSON file v3\), `min_voltage` and "
                r"`max_voltage` are replaced with `min_voltage_level`, `max_voltage_level` and "
                r"`nominal_voltage`. The found values of `min_voltage` or `max_voltage` are dropped."
            ),
        ),
    ):
        en = ElectricalNetwork.from_dict(data=dict_v2, include_results=True)
    net_dict = en.to_dict(include_results=True)
    expected_dict = copy.deepcopy(dict_v2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        expected_dict = v2_to_v3_converter(expected_dict)
        expected_dict = v3_to_v4_converter(expected_dict)
        expected_dict = v4_to_v5_converter(expected_dict)

    assert_json_close(net_dict, expected_dict)

    # Test max loading of transformers
    for tr in en.transformers.values():
        tp_data = next(tp_d for tp_d in dict_v2["transformers_params"] if tp_d["id"] == tr.parameters.id)
        assert tr.max_loading.m == tp_data["max_power"] / tp_data["sn"]


def test_from_dict_v3():
    dict_v3 = json.loads(read_json_file("network_json_v3.json"))

    with pytest.warns(UserWarning, match=r"Got an outdated network file \(version 3\)"):
        en = ElectricalNetwork.from_dict(data=dict_v3, include_results=True)
    net_dict = en.to_dict(include_results=True)
    expected_dict = copy.deepcopy(dict_v3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        expected_dict = v3_to_v4_converter(expected_dict)
        expected_dict = v4_to_v5_converter(expected_dict)

    assert_json_close(net_dict, expected_dict)

    # Test vector group of transformers
    for tr in en.transformers.values():
        if tr.phases1 == "abcn":
            assert tr.parameters.whv in ("YN", "ZN")
        if tr.phases2 == "abcn":
            assert tr.parameters.wlv in ("yn", "zn")


@pytest.mark.parametrize("version", list(range(NETWORK_JSON_VERSION)))
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


def test_crs_conversion():
    # No CRS
    bus = Bus(id="bus", phases="an", geometry=Point(0.0, 0.0))
    VoltageSource(id="source", bus=bus, voltages=400)
    PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(bus)
    en_dict = en.to_dict()
    assert en_dict["crs"] == {"data": None, "normalize": False}
    assert en.buses_frame.crs is None
    en2 = ElectricalNetwork.from_dict(en_dict)
    assert en2.crs is None
    assert en2.buses_frame.crs is None

    # CRS like
    bus = Bus(id="bus", phases="an", geometry=Point(0.0, 0.0))
    VoltageSource(id="source", bus=bus, voltages=400)
    PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(bus, crs="WGS84")
    en_dict = en.to_dict()
    assert en_dict["crs"] == {"data": "WGS84", "normalize": False}
    assert en.buses_frame.crs == "WGS84"
    en2 = ElectricalNetwork.from_dict(en_dict)
    assert en2.crs == "WGS84"
    assert en2.buses_frame.crs == "WGS84"

    # CRS object -> WKT format
    bus = Bus(id="bus", phases="an", geometry=Point(0.0, 0.0))
    VoltageSource(id="source", bus=bus, voltages=400)
    PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(bus, crs=CRS("EPSG:4326"))
    en_dict = en.to_dict()
    assert en_dict["crs"]["normalize"] is True
    crs_data = en_dict["crs"]["data"]
    assert isinstance(crs_data, str)
    assert crs_data.startswith("GEOGCRS[")  # WKT format
    assert crs_data.endswith('ID["EPSG",4326]]')
    assert en.buses_frame.crs == "EPSG:4326"
    en2 = ElectricalNetwork.from_dict(en_dict)
    assert isinstance(en2.crs, CRS)
    assert en2.crs == "EPSG:4326"
    assert en2.buses_frame.crs == "EPSG:4326"
