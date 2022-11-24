from urllib.parse import urljoin

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import requests_mock
from shapely.geometry import LineString, Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    DeltaWyeTransformer,
    Ground,
    Line,
    LineCharacteristics,
    PotentialRef,
    PowerLoad,
    Switch,
    TransformerCharacteristics,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork


@pytest.fixture()
def small_network() -> ElectricalNetwork:
    # Build a small network
    ground = Ground()
    vs = VoltageSource(
        id="vs",
        n=4,
        ground=ground,
        source_voltages=[20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j],
        geometry=Point(-1.318375372111463, 48.64794139348595),
    )
    load_bus = Bus("bus", 4, geometry=Point(-1.320149235966572, 48.64971306653889))
    ground.connect(load_bus)
    load = PowerLoad("load", 4, load_bus, [100, 100, 100])
    pref = PotentialRef(ground)

    lc = LineCharacteristics("test", 10 * np.eye(4, dtype=complex))
    line = Line(
        id="line",
        n=4,
        bus1=vs,
        bus2=load_bus,
        line_characteristics=lc,
        length=1.0,  # km
        geometry=LineString([(-1.318375372111463, 48.64794139348595), (-1.320149235966572, 48.64971306653889)]),
    )

    en = ElectricalNetwork(buses=[vs, load_bus], branches=[line], loads=[load], special_elements=[pref, ground])
    return en


@pytest.fixture
def good_json_results() -> dict:
    return {
        "info": {
            "status": "success",
            "resolutionMethod": "newton",
            "iterations": 1,
            "targetError": 1e-06,
            "finalError": 6.296829377361313e-14,
        },
        "buses": [
            {
                "id": "vs",
                "potentials": {
                    "va": [20000.0, 0.0],
                    "vb": [-10000.0, -17320.508076],
                    "vc": [-10000.0, 17320.508076],
                    "vn": [0.0, 0.0],
                },
            },
            {
                "id": "bus",
                "potentials": {
                    "va": [19999.949999875, 0.0],
                    "vb": [-9999.9749999375, -17320.464774621556],
                    "vc": [-9999.9749999375, 17320.464774621556],
                    "vn": [1.3476526914363477e-12, 0.0],
                },
            },
        ],
        "branches": [
            {
                "id": "line",
                "currents1": {
                    "ia": [0.005, 0.0],
                    "ib": [-0.0025, -0.0043],
                    "ic": [-0.0025, 0.0043],
                    "in": [-1.347e-13, 0.0],
                },
                "currents2": {
                    "ia": [0.005, 0.0],
                    "ib": [-0.0025, -0.0043],
                    "ic": [-0.0025, 0.0043],
                    "in": [-1.347e-13, 0.0],
                },
            }
        ],
        "loads": [
            {
                "id": "load",
                "currents": {
                    "ia": [0.005, -0.0],
                    "ib": [-0.0025, -0.0043],
                    "ic": [-0.0025, 0.0043],
                    "in": [-1.347e-13, 0.0],
                },
            }
        ],
    }


def test_add_and_remove():
    ground = Ground()
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        source_voltages=voltages,
    )
    load_bus = Bus(id="load bus", n=4)
    load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
    line = Line(id="line", n=4, bus1=vs, bus2=load_bus, line_characteristics=line_characteristics, length=10)  # km
    _ = PotentialRef(element=ground)
    en = ElectricalNetwork.from_element(vs)
    en.remove_element(load.id)
    new_load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
    en.add_element(new_load)

    # Bad key
    with pytest.raises(RoseauLoadFlowException) as e:
        en.remove_element("unknown element")
    assert "is not a valid bus, branch or load id" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_ELEMENT_ID

    # Adding ground
    ground2 = Ground()
    with pytest.raises(RoseauLoadFlowException) as e:
        en.add_element(ground2)
    assert e.value.args[0] == "Only lines, loads and buses can be added to the network."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Remove line => 2 separated connected components
    with pytest.raises(RoseauLoadFlowException) as e:
        en.remove_element(line.id)
        en.solve_load_flow(auth=("", ""))
    assert "does not have a potential reference" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE


def test_bad_networks():
    # No voltage source
    ground = Ground()
    bus1 = Bus("bus1", 3)
    bus2 = Bus("bus2", 3)
    ground.connect(bus2)
    line_characteristics = LineCharacteristics("test", z_line=np.eye(3, dtype=complex))
    line = Line(id="line", n=3, bus1=bus1, bus2=bus2, line_characteristics=line_characteristics, length=10)
    p_ref = PotentialRef(ground)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(bus1)
    assert e.value.args[0] == "There is no voltage source provided in the network, you must provide at least one."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE

    # Bad constructor
    vs = VoltageSource("vs", 4, ground, [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j])
    switch = Switch("switch", 4, vs, bus1)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork([vs, bus1], [line, switch], [], [ground, p_ref])  # no bus2
    assert "but has not been added to the network, you should add it with 'add_element'." in e.value.args[0]
    assert bus2.id in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT

    # No potential reference
    bus3 = Bus("bus3", 4)
    transformer_characteristics = TransformerCharacteristics(
        type_name="t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    _ = DeltaWyeTransformer("transfo", bus2, bus3, transformer_characteristics)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(vs)
    assert "does not have a potential reference" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE

    # Good network
    ground.connect(bus3)

    # 2 potential reference
    _ = PotentialRef(bus3)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(vs)
    assert "has 2 potential references, it should have only one." in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.SEVERAL_POTENTIAL_REFERENCE


def test_solve_load_flow(small_network, good_json_results):
    load: PowerLoad = small_network.loads["load"]
    load_bus = small_network.buses["bus"]

    # Good result
    # Request the server
    solve_url = urljoin(ElectricalNetwork.DEFAULT_BASE_URL, "solve/")
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=200, json=good_json_results, headers={"content-type": "application/json"})
        small_network.solve_load_flow(auth=("", ""))
    assert len(load_bus.potentials) == 4

    # No convergence
    load.update_powers([10000000, 100, 100])
    json_result = {
        "info": {
            "status": "failure",
            "resolutionMethod": "newton",
            "iterations": 50,
            "targetError": 1e-06,
            "finalError": 14037.977318668112,
        },
        "buses": [
            {
                "id": "vs",
                "potentials": {
                    "va": [20000.0, 0.0],
                    "vb": [-10000.0, -17320.508076],
                    "vc": [-10000.0, 17320.508076],
                    "vn": [0.0, 0.0],
                },
            },
            {
                "id": "bus",
                "potentials": {
                    "va": [110753.81558442864, 1.5688245436058308e-26],
                    "vb": [-9999.985548801811, -17320.50568183019],
                    "vc": [-9999.985548801811, 17320.50568183019],
                    "vn": [-90753.844486825, -2.6687106473172017e-26],
                },
            },
        ],
        "branches": [
            {
                "id": "line",
                "currents1": {"ia": [0.0, 0.0], "ib": [0.0, 0.0], "ic": [0.0, 0.0], "in": [0.0, 0.0]},
                "currents2": {"ia": [0.0, 0.0], "ib": [0.0, 0.0], "ic": [0.0, 0.0], "in": [0.0, 0.0]},
            }
        ],
        "loads": [{"id": "load", "currents": {"ia": [0.0, 0.0], "ib": [0.0, 0.0], "ic": [0.0, 0.0], "in": [0.0, 0.0]}}],
    }
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=200, json=json_result, headers={"content-type": "application/json"})
        with pytest.raises(RoseauLoadFlowException) as e:
            small_network.solve_load_flow(auth=("", ""))
        assert "The load flow did not converge after 50 iterations" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE


def test_solve_load_flow_error(small_network):
    # Solve url
    solve_url = urljoin(ElectricalNetwork.DEFAULT_BASE_URL, "solve/")

    # Parse RLF error
    json_result = {"msg": "toto", "code": "roseau.load_flow.bad_branch_type"}
    with requests_mock.Mocker() as m, pytest.raises(RoseauLoadFlowException) as e:
        m.post(solve_url, status_code=400, json=json_result, headers={"content-type": "application/json"})
        small_network.solve_load_flow(auth=("", ""))
    assert e.value.args[0] == json_result["msg"]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE

    # Load flow error (other than official exceptions of RoseauLoadFlowException)
    json_result = {"msg": "Error while solving the load flow", "code": "load_flow_error"}
    with requests_mock.Mocker() as m, pytest.raises(RoseauLoadFlowException) as e:
        m.post(solve_url, status_code=400, json=json_result, headers={"content-type": "application/json"})
        small_network.solve_load_flow(auth=("", ""))
    assert json_result["msg"] in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_REQUEST

    # Authentication fail
    json_result = {"detail": "not_authenticated"}
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=401, json=json_result, headers={"content-type": "application/json"})
        with pytest.raises(RoseauLoadFlowException) as e:
            small_network.solve_load_flow(auth=("", ""))
    assert "Authentication failed." in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_REQUEST

    # Bad request
    json_result = {"msg": "Error while parsing the provided JSON", "code": "parse_error"}
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=400, json=json_result, headers={"content-type": "application/json"})
        with pytest.raises(RoseauLoadFlowException) as e:
            small_network.solve_load_flow(auth=("", ""))
    assert "There is a problem in the request" in e.value.args[0]
    assert "Error while parsing the provided JSON" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_REQUEST


def test_frame(small_network):
    # Buses
    buses_gdf = small_network.buses_frame
    assert isinstance(buses_gdf, gpd.GeoDataFrame)
    assert buses_gdf.shape == (2, 2)
    assert set(buses_gdf.columns) == {"n", "geometry"}
    assert buses_gdf.index.name == "id"

    # Branches
    branches_gdf = small_network.branches_frame
    assert isinstance(branches_gdf, gpd.GeoDataFrame)
    assert branches_gdf.shape == (1, 6)
    assert set(branches_gdf.columns) == {"branch_type", "n1", "n2", "bus1_id", "bus2_id", "geometry"}
    assert branches_gdf.index.name == "id"

    # Loads
    loads_gdf = small_network.loads_frame
    assert isinstance(loads_gdf, pd.DataFrame)
    assert loads_gdf.shape == (1, 2)
    assert set(loads_gdf.columns) == {"n", "bus_id"}
    assert loads_gdf.index.name == "id"


def test_buses_voltages(small_network, good_json_results):
    assert isinstance(small_network, ElectricalNetwork)
    small_network._dispatch_results(good_json_results)

    voltage_records = [
        {"bus_id": "vs", "phase": "an", "voltage": 20000.0 + 0.0j},
        {"bus_id": "vs", "phase": "bn", "voltage": -10000.0 + -17320.508076j},
        {"bus_id": "vs", "phase": "cn", "voltage": -10000.0 + 17320.508076j},
        {"bus_id": "bus", "phase": "an", "voltage": 19999.949999875 + 0.0j},
        {"bus_id": "bus", "phase": "bn", "voltage": -9999.9749999375 + -17320.464774621556j},
        {"bus_id": "bus", "phase": "cn", "voltage": -9999.9749999375 + 17320.464774621556j},
    ]

    def fix_index_type(idx: pd.MultiIndex) -> pd.MultiIndex:
        return idx.set_levels(
            idx.levels[1].astype(pd.CategoricalDtype(["an", "bn", "cn", "ab", "bc", "ca"], ordered=True)),
            level=1,
        )

    # Complex voltages
    buses_voltages = small_network.buses_voltages()
    expected_buses_voltages = pd.DataFrame.from_records(voltage_records, index=["bus_id", "phase"])
    expected_buses_voltages.index = fix_index_type(expected_buses_voltages.index)

    assert isinstance(buses_voltages, pd.DataFrame)
    assert buses_voltages.shape == (6, 1)
    assert buses_voltages.index.names == ["bus_id", "phase"]
    assert list(buses_voltages.columns) == ["voltage"]
    pd.testing.assert_frame_equal(buses_voltages, expected_buses_voltages)

    # Magnitude and Angle voltages
    buses_voltages = small_network.buses_voltages(as_magnitude_angle=True)
    expected_buses_voltages = pd.DataFrame.from_records(
        [
            {
                "bus_id": record["bus_id"],
                "phase": record["phase"],
                "voltage_magnitude": np.abs(record["voltage"]),
                "voltage_angle": np.angle(record["voltage"], deg=True),
            }
            for record in voltage_records
        ],
        index=["bus_id", "phase"],
    )
    expected_buses_voltages.index = fix_index_type(expected_buses_voltages.index)

    assert isinstance(buses_voltages, pd.DataFrame)
    assert buses_voltages.shape == (6, 2)
    assert buses_voltages.index.names == ["bus_id", "phase"]
    assert list(buses_voltages.columns) == ["voltage_magnitude", "voltage_angle"]
    pd.testing.assert_frame_equal(buses_voltages, expected_buses_voltages)
