import itertools as it
import warnings
from contextlib import contextmanager
from urllib.parse import urljoin

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import requests_mock
from pandas.testing import assert_frame_equal
from shapely.geometry import LineString, Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import _PHASE_DTYPE, _VOLTAGE_PHASES_DTYPE, ElectricalNetwork
from roseau.load_flow.utils import Q_


@pytest.fixture()
def small_network() -> ElectricalNetwork:
    # Build a small network
    point1 = Point(-1.318375372111463, 48.64794139348595)
    point2 = Point(-1.320149235966572, 48.64971306653889)
    line_string = LineString([point1, point2])

    ground = Ground("ground")
    source_bus = Bus("bus0", phases="abcn", geometry=point1)
    load_bus = Bus("bus1", phases="abcn", geometry=point2)
    ground.connect(load_bus)

    voltages = [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j]
    vs = VoltageSource("vs", source_bus, voltages=voltages, phases="abcn")
    load = PowerLoad("load", load_bus, powers=[100, 100, 100], phases="abcn")
    pref = PotentialRef("pref", element=ground)

    lp = LineParameters("test", z_line=10 * np.eye(4, dtype=complex))
    line = Line("line", source_bus, load_bus, phases="abcn", parameters=lp, length=1.0, geometry=line_string)

    return ElectricalNetwork(
        buses=[source_bus, load_bus],
        branches=[line],
        loads=[load],
        voltage_sources=[vs],
        grounds=[ground],
        potential_refs=[pref],
    )


@pytest.fixture()
def single_phase_network() -> ElectricalNetwork:
    # Build a small single-phase network
    # ----------------------------------

    # Phase "b" is chosen to catch errors where the index of the first phase may be assumed to be 0
    phases = "bn"

    # Network geometry
    point1 = Point(-1.318375372111463, 48.64794139348595)
    point2 = Point(-1.320149235966572, 48.64971306653889)
    line_string = LineString([point1, point2])

    # Network elements
    bus0 = Bus("bus0", phases=phases, geometry=point1)
    bus1 = Bus("bus1", phases=phases, geometry=point2)

    ground = Ground("ground")
    ground.connect(bus1)
    pref = PotentialRef("pref", element=ground)

    vs = VoltageSource("vs", bus0, voltages=[20000.0 + 0.0j], phases=phases)
    load = PowerLoad("load", bus1, powers=[100], phases=phases)

    lp = LineParameters("test", z_line=10 * np.eye(2, dtype=complex))
    line = Line("line", bus0, bus1, phases=phases, parameters=lp, length=1.0, geometry=line_string)

    return ElectricalNetwork(
        buses=[bus0, bus1],
        branches=[line],
        loads=[load],
        voltage_sources=[vs],
        grounds=[ground],
        potential_refs=[pref],
    )


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
                "id": "bus0",
                "phases": "abcn",
                "potentials": [
                    [20000.0, 0.0],
                    [-10000.0, -17320.508076],
                    [-10000.0, 17320.508076],
                    [0.0, 0.0],
                ],
            },
            {
                "id": "bus1",
                "phases": "abcn",
                "potentials": [
                    [19999.949999875, 0.0],
                    [-9999.9749999375, -17320.464774621556],
                    [-9999.9749999375, 17320.464774621556],
                    [1.3476526914363477e-12, 0.0],
                ],
            },
        ],
        "branches": [
            {
                "id": "line",
                "phases1": "abcn",
                "phases2": "abcn",
                "currents1": [
                    [0.005, 0.0],
                    [-0.0025, -0.0043],
                    [-0.0025, 0.0043],
                    [-1.347e-13, 0.0],
                ],
                "currents2": [
                    [0.005, 0.0],
                    [-0.0025, -0.0043],
                    [-0.0025, 0.0043],
                    [-1.347e-13, 0.0],
                ],
            }
        ],
        "loads": [
            {
                "id": "load",
                "phases": "abcn",
                "currents": [
                    [0.005, -0.0],
                    [-0.0025, -0.0043],
                    [-0.0025, 0.0043],
                    [-1.347e-13, 0.0],
                ],
            }
        ],
        "sources": [],
    }


@contextmanager
def check_result_warning(expected_message: str):
    with warnings.catch_warnings(record=True) as records:
        yield
    assert len(records) == 1
    assert records[0].message.args[0] == expected_message
    assert records[0].category == UserWarning


def test_connect_and_disconnect():
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    vs = VoltageSource(id="vs", phases="abcn", bus=source_bus, voltages=voltages)
    load = PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    lp = LineParameters("test", z_line=np.eye(4, dtype=complex))
    line = Line(id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)
    PotentialRef("pref", element=ground)
    en = ElectricalNetwork.from_element(source_bus)
    assert load.network == en
    load.disconnect()
    assert load.network is None
    assert load.bus is None
    with pytest.raises(RoseauLoadFlowException) as e:
        load.to_dict()
    assert e.value.args[0] == "The load 'power load' is disconnected and can not be used anymore."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT
    new_load = PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    assert new_load.network == en

    # Disconnection of a voltage source
    assert vs.network == en
    vs.disconnect()
    assert vs.network is None
    assert vs.bus is None
    with pytest.raises(RoseauLoadFlowException) as e:
        vs.to_dict()
    assert e.value.args[0] == "The voltage source 'vs' is disconnected and can not be used anymore."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT

    # Bad key
    with pytest.raises(RoseauLoadFlowException) as e:
        en._disconnect_element(Ground("a separate ground element"))
    assert e.value.msg == "Ground(id='a separate ground element') is not a valid load or voltage source."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Adding ground => impossible
    ground2 = Ground("ground2")
    with pytest.raises(RoseauLoadFlowException) as e:
        en._connect_element(ground2)
    assert e.value.msg == "Only lines, loads, buses and voltage sources can be added to the network."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Remove line => impossible
    with pytest.raises(RoseauLoadFlowException) as e:
        en._disconnect_element(line)
    assert (
        e.value.msg
        == "Line(id='line', phases1='abcn', phases2='abcn', bus1='source', bus2='load bus') is a Line and it can not "
        "be disconnected from a network."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT


def test_bad_networks():
    # No voltage source
    ground = Ground("ground")
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abcn")
    ground.connect(bus2)
    lp = LineParameters("test", z_line=np.eye(3, dtype=complex))
    line = Line("line", bus1, bus2, phases="abc", parameters=lp, length=10)
    p_ref = PotentialRef("pref1", element=ground)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(bus1)
    assert e.value.msg == "There is no voltage source provided in the network, you must provide at least one."
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE

    # No network has been assigned
    assert bus1.network is None
    assert line.network is None
    assert ground.network is None
    assert p_ref.network is None

    # Bad constructor
    bus0 = Bus("bus0", phases="abcn")
    ground.connect(bus0)
    voltages = [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j]
    vs = VoltageSource("vs", bus0, phases="abcn", voltages=voltages)
    switch = Switch("switch", bus0, bus1, phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork(
            buses=[bus0, bus1],  # no bus2
            branches=[line, switch],
            loads=[],
            voltage_sources=[vs],
            grounds=[ground],
            potential_refs=[p_ref],
        )
    assert "but has not been added to the network. It must be added with 'add_element'." in e.value.msg
    assert bus2.id in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT

    # No network has been assigned
    assert bus0.network is None
    assert bus1.network is None
    assert line.network is None
    assert switch.network is None
    assert vs.network is None
    assert ground.network is None
    assert p_ref.network is None

    # No potential reference
    bus3 = Bus("bus3", phases="abcn")
    tp = TransformerParameters(
        "t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    t = Transformer("transfo", bus2, bus3, parameters=tp)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(bus0)
    assert "does not have a potential reference" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE

    # No network has been assigned
    assert bus0.network is None
    assert bus1.network is None
    assert line.network is None
    assert switch.network is None
    assert vs.network is None
    assert ground.network is None
    assert p_ref.network is None
    assert bus3.network is None
    assert t.network is None

    # Good network
    ground.connect(bus3)

    # 2 potential reference
    p_ref2 = PotentialRef("pref2", element=bus3)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(vs)
    assert "has 2 potential references, it should have only one." in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SEVERAL_POTENTIAL_REFERENCE

    # No network has been assigned
    assert bus0.network is None
    assert bus1.network is None
    assert line.network is None
    assert switch.network is None
    assert vs.network is None
    assert ground.network is None
    assert p_ref.network is None
    assert bus3.network is None
    assert t.network is None
    assert p_ref2.network is None


def test_solve_load_flow(small_network, good_json_results):
    load: PowerLoad = small_network.loads["load"]
    load_bus = small_network.buses["bus1"]

    # Good result
    # Request the server
    solve_url = urljoin(ElectricalNetwork.DEFAULT_BASE_URL, "solve/")
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=200, json=good_json_results, headers={"content-type": "application/json"})
        small_network.solve_load_flow(auth=("", ""))
    assert len(load_bus.res_potentials) == 4

    # No convergence
    load.powers = [10000000, 100, 100]
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
                "id": "bus0",
                "phases": "abcn",
                "potentials": [
                    [20000.0, 0.0],
                    [-10000.0, -17320.508076],
                    [-10000.0, 17320.508076],
                    [0.0, 0.0],
                ],
            },
            {
                "id": "bus1",
                "phases": "abcn",
                "potentials": [
                    [110753.81558442864, 1.5688245436058308e-26],
                    [-9999.985548801811, -17320.50568183019],
                    [-9999.985548801811, 17320.50568183019],
                    [-90753.844486825, -2.6687106473172017e-26],
                ],
            },
        ],
        "branches": [
            {
                "id": "line",
                "phases1": "abcn",
                "phases2": "abcn",
                "currents1": [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
                "currents2": [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
            }
        ],
        "loads": [
            {
                "id": "load",
                "phases": "abcn",
                "currents": [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
            },
        ],
        "sources": [],
    }
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=200, json=json_result, headers={"content-type": "application/json"})
        with pytest.raises(RoseauLoadFlowException) as e:
            small_network.solve_load_flow(auth=("", ""))
        assert "The load flow did not converge after 50 iterations" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE


def test_solve_load_flow_error(small_network):
    # Solve url
    solve_url = urljoin(ElectricalNetwork.DEFAULT_BASE_URL, "solve/")

    # Parse RLF error
    json_result = {"msg": "toto", "code": "roseau.load_flow.bad_branch_type"}
    with requests_mock.Mocker() as m, pytest.raises(RoseauLoadFlowException) as e:
        m.post(solve_url, status_code=400, json=json_result, headers={"content-type": "application/json"})
        small_network.solve_load_flow(auth=("", ""))
    assert e.value.msg == json_result["msg"]
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BRANCH_TYPE

    # Load flow error (other than official exceptions of RoseauLoadFlowException)
    json_result = {"msg": "Error while solving the load flow", "code": "load_flow_error"}
    with requests_mock.Mocker() as m, pytest.raises(RoseauLoadFlowException) as e:
        m.post(solve_url, status_code=400, json=json_result, headers={"content-type": "application/json"})
        small_network.solve_load_flow(auth=("", ""))
    assert json_result["msg"] in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REQUEST

    # Authentication fail
    json_result = {"detail": "not_authenticated"}
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=401, json=json_result, headers={"content-type": "application/json"})
        with pytest.raises(RoseauLoadFlowException) as e:
            small_network.solve_load_flow(auth=("", ""))
    assert "Authentication failed." in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REQUEST

    # Bad request
    json_result = {"msg": "Error while parsing the provided JSON", "code": "parse_error"}
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=400, json=json_result, headers={"content-type": "application/json"})
        with pytest.raises(RoseauLoadFlowException) as e:
            small_network.solve_load_flow(auth=("", ""))
    assert "There is a problem in the request" in e.value.msg
    assert "Error while parsing the provided JSON" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_REQUEST


def test_frame(small_network):
    # Buses
    buses_gdf = small_network.buses_frame
    assert isinstance(buses_gdf, gpd.GeoDataFrame)
    assert buses_gdf.shape == (2, 2)
    assert set(buses_gdf.columns) == {"phases", "geometry"}
    assert buses_gdf.index.name == "id"

    # Branches
    branches_gdf = small_network.branches_frame
    assert isinstance(branches_gdf, gpd.GeoDataFrame)
    assert branches_gdf.shape == (1, 6)
    assert set(branches_gdf.columns) == {"branch_type", "phases1", "phases2", "bus1_id", "bus2_id", "geometry"}
    assert branches_gdf.index.name == "id"

    # Loads
    loads_df = small_network.loads_frame
    assert isinstance(loads_df, pd.DataFrame)
    assert loads_df.shape == (1, 2)
    assert set(loads_df.columns) == {"phases", "bus_id"}
    assert loads_df.index.name == "id"

    # Sources
    sources_df = small_network.voltage_sources_frame
    assert isinstance(sources_df, pd.DataFrame)
    assert sources_df.shape == (1, 2)
    assert set(sources_df.columns) == {"phases", "bus_id"}
    assert sources_df.index.name == "id"


def test_buses_voltages(small_network, good_json_results):
    assert isinstance(small_network, ElectricalNetwork)
    small_network._dispatch_results(good_json_results)

    voltage_records = [
        {"bus_id": "bus0", "phase": "an", "voltage": 20000.0 + 0.0j},
        {"bus_id": "bus0", "phase": "bn", "voltage": -10000.0 + -17320.508076j},
        {"bus_id": "bus0", "phase": "cn", "voltage": -10000.0 + 17320.508076j},
        {"bus_id": "bus1", "phase": "an", "voltage": 19999.949999875 + 0.0j},
        {"bus_id": "bus1", "phase": "bn", "voltage": -9999.9749999375 + -17320.464774621556j},
        {"bus_id": "bus1", "phase": "cn", "voltage": -9999.9749999375 + 17320.464774621556j},
    ]

    def set_index_dtype(idx: pd.MultiIndex) -> pd.MultiIndex:
        return idx.set_levels(idx.levels[1].astype(_VOLTAGE_PHASES_DTYPE), level=1)

    buses_voltages = small_network.res_buses_voltages
    expected_buses_voltages = pd.DataFrame.from_records(voltage_records, index=["bus_id", "phase"])
    expected_buses_voltages.index = set_index_dtype(expected_buses_voltages.index)

    assert isinstance(buses_voltages, pd.DataFrame)
    assert buses_voltages.shape == (6, 1)
    assert buses_voltages.index.names == ["bus_id", "phase"]
    assert list(buses_voltages.columns) == ["voltage"]
    assert_frame_equal(buses_voltages, expected_buses_voltages)


def test_to_from_dict_roundtrip(small_network: ElectricalNetwork):
    net_dict = small_network.to_dict()
    new_net = ElectricalNetwork.from_dict(net_dict)
    assert_frame_equal(small_network.buses_frame, new_net.buses_frame)
    assert_frame_equal(small_network.branches_frame, new_net.branches_frame)
    assert_frame_equal(small_network.loads_frame, new_net.loads_frame)
    assert_frame_equal(small_network.voltage_sources_frame, new_net.voltage_sources_frame)


def test_single_phase_network(single_phase_network: ElectricalNetwork):
    # Test dict conversion
    # ====================
    net_dict = single_phase_network.to_dict()
    new_net = ElectricalNetwork.from_dict(net_dict)
    assert_frame_equal(single_phase_network.buses_frame, new_net.buses_frame)
    assert_frame_equal(single_phase_network.branches_frame, new_net.branches_frame)
    assert_frame_equal(single_phase_network.loads_frame, new_net.loads_frame)
    assert_frame_equal(single_phase_network.voltage_sources_frame, new_net.voltage_sources_frame)

    # Test load flow results
    # ======================
    source_bus = single_phase_network.buses["bus0"]
    load_bus = single_phase_network.buses["bus1"]
    line = single_phase_network.branches["line"]
    load = single_phase_network.loads["load"]

    json_results = {
        "info": {
            "status": "success",
            "resolutionMethod": "newton",
            "iterations": 1,
            "targetError": 1e-06,
            "finalError": 6.29e-14,
        },
        "buses": [
            {"id": "bus0", "phases": "bn", "potentials": [[-10000.0, -17320.508], [0.0, 0.0]]},
            {"id": "bus1", "phases": "bn", "potentials": [[-9999.974, -17320.464], [1.347e-12, 0.0]]},
        ],
        "branches": [
            {
                "id": "line",
                "phases1": "bn",
                "phases2": "bn",
                "currents1": [[-0.0025, -0.0043], [-1.347e-13, 0.0]],
                "currents2": [[-0.0025, -0.0043], [-1.347e-13, 0.0]],
            }
        ],
        "loads": [
            {"id": "load", "phases": "bn", "currents": [[-0.0025, -0.0043], [1.347e-13, 0.0]]},
        ],
        "sources": [],
    }
    solve_url = urljoin(ElectricalNetwork.DEFAULT_BASE_URL, "solve/")
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=200, json=json_results, headers={"content-type": "application/json"})
        single_phase_network.solve_load_flow(auth=("", ""))

    # Test results of elements
    # ------------------------
    assert np.allclose(source_bus.res_potentials, [-10000.0 - 17320.508j, 0j])
    assert np.allclose(load_bus.res_potentials, [-9999.974 - 17320.464j, 1.347e-12 + 0j])
    assert np.allclose(line.res_currents[0], [-0.0025 - 0.0043j, -1.347e-13 + 0j])
    assert np.allclose(line.res_currents[1], [-0.0025 - 0.0043j, -1.347e-13 + 0j])
    assert np.allclose(load.res_currents, [-0.0025 - 0.0043j, -1.347e-13 + 0j])

    # Test results of network
    # -----------------------
    # Buses potentials frame
    pd.testing.assert_frame_equal(
        single_phase_network.res_buses_potentials,
        pd.DataFrame.from_records(
            [
                {"bus_id": "bus0", "phase": "b", "potential": -10000.0 - 17320.508j},
                {"bus_id": "bus0", "phase": "n", "potential": 0j},
                {"bus_id": "bus1", "phase": "b", "potential": -9999.974 - 17320.464j},
                {"bus_id": "bus1", "phase": "n", "potential": 0j},
            ]
        )
        .astype({"phase": _PHASE_DTYPE, "potential": complex})
        .set_index(["bus_id", "phase"]),
    )
    # Buses voltages frame
    pd.testing.assert_frame_equal(
        single_phase_network.res_buses_voltages,
        pd.DataFrame.from_records(
            [
                {"bus_id": "bus0", "phase": "bn", "voltage": -10000.0 - 17320.508j},
                {"bus_id": "bus1", "phase": "bn", "voltage": -9999.974 - 17320.464j},
            ]
        )
        .astype({"phase": _VOLTAGE_PHASES_DTYPE, "voltage": complex})
        .set_index(["bus_id", "phase"]),
    )
    # Branches currents frame
    pd.testing.assert_frame_equal(
        single_phase_network.res_branches_currents,
        pd.DataFrame.from_records(
            [
                {"branch_id": "line", "phase": "b", "current1": -0.0025 - 0.0043j, "current2": -0.0025 - 0.0043j},
                {"branch_id": "line", "phase": "n", "current1": -1.347e-13 + 0j, "current2": -1.347e-13 + 0j},
            ]
        )
        .astype({"phase": _PHASE_DTYPE, "current1": complex, "current2": complex})
        .set_index(["branch_id", "phase"]),
    )
    # Loads currents frame
    pd.testing.assert_frame_equal(
        single_phase_network.res_loads_currents,
        pd.DataFrame.from_records(
            [
                {"load_id": "load", "phase": "b", "current": -0.0025 - 0.0043j},
                {"load_id": "load", "phase": "n", "current": -1.347e-13 + 0j},
            ]
        )
        .astype({"phase": _PHASE_DTYPE, "current": complex})
        .set_index(["load_id", "phase"]),
    )


def test_network_elements(small_network):
    # Add a line to the network ("bus2" constructor belongs to the network)
    bus1 = small_network.buses["bus1"]
    bus2 = Bus("bus2", phases="abcn")
    assert bus2.network is None
    lp = LineParameters("test", z_line=10 * np.eye(4, dtype=complex))
    l2 = Line(id="line2", bus1=bus2, bus2=bus1, parameters=lp, length=Q_(0.3, "km"))
    assert l2.network == small_network
    assert bus2.network == small_network

    # Add a switch ("bus1" constructor belongs to the network)
    bus3 = Bus("bus2", phases="abcn")
    assert bus3.network is None
    s = Switch(id="switch", bus1=bus2, bus2=bus3)
    assert s.network == small_network
    assert bus3.network == small_network

    # Create a second network
    bus_vs = Bus("bus_vs", phases="abcn")
    VoltageSource("vs2", bus=bus_vs, voltages=15e3 * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3)]))
    ground = Ground("ground2")
    ground.connect(bus=bus_vs, phase="a")
    PotentialRef("pref2", element=ground)
    small_network_2 = ElectricalNetwork.from_element(initial_bus=bus_vs)

    # Connect the two networks
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch2", bus1=bus2, bus2=bus_vs)
    assert e.value.args[0] == "The Bus 'bus_vs' is already assigned to another network."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.SEVERAL_NETWORKS

    # Every object have their good network after this failure
    for element in it.chain(
        small_network.buses.values(),
        small_network.branches.values(),
        small_network.loads.values(),
        small_network.grounds.values(),
        small_network.potential_refs.values(),
    ):
        assert element.network == small_network
    for element in it.chain(
        small_network_2.buses.values(),
        small_network_2.branches.values(),
        small_network_2.loads.values(),
        small_network_2.grounds.values(),
        small_network_2.potential_refs.values(),
    ):
        assert element.network == small_network_2


def test_network_results_warning(small_network, good_json_results, recwarn):  # noqa: C901
    # network well-defined using the constructor
    for bus in small_network.buses.values():
        assert bus.network == small_network
    for load in small_network.loads.values():
        assert load.network == small_network
    for branch in small_network.branches.values():
        assert branch.network == small_network
    for ground in small_network.grounds.values():
        assert ground.network == small_network
    for p_ref in small_network.potential_refs.values():
        assert p_ref.network == small_network

    # All the results function raises an exception
    for bus in small_network.buses.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            bus.res_potentials
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
        with pytest.raises(RoseauLoadFlowException) as e:
            bus.res_voltages
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for branch in small_network.branches.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            branch.res_currents
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for load in small_network.loads.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            load.res_currents
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
        if load.is_flexible and isinstance(load, PowerLoad):
            with pytest.raises(RoseauLoadFlowException) as e:
                load.res_flexible_powers
            assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    # for p_ref in small_network.potential_refs.values():
    #     with pytest.raises(RoseauLoadFlowException) as e:
    #         p_ref.res_current
    # assert e.value.args[1]==RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN

    # Solve a load flow
    solve_url = urljoin(ElectricalNetwork.DEFAULT_BASE_URL, "solve/")
    with requests_mock.Mocker() as m:
        m.post(solve_url, status_code=200, json=good_json_results, headers={"content-type": "application/json"})
        small_network.solve_load_flow(auth=("", ""))

    # No warning when getting results (they are up-to-date)
    recwarn.clear()
    for bus in small_network.buses.values():
        bus.res_potentials
        bus.res_voltages
    for branch in small_network.branches.values():
        branch.res_currents
    for load in small_network.loads.values():
        load.res_currents
        if load.is_flexible and isinstance(load, PowerLoad):
            load.res_flexible_powers
    # for p_ref in small_network.potential_refs.values():
    #     p_ref.res_current
    assert len(recwarn) == 0

    # Modify something
    load = small_network.loads["load"]
    load.powers = [200, 200, 200]  # VA

    # Ensure that a warning is raised no matter which result is requested
    expected_message = (
        "The results of this element may be outdated. Please re-run a load flow to ensure the validity of results."
    )
    for bus in small_network.buses.values():
        with check_result_warning(expected_message=expected_message):
            bus.res_potentials
        with check_result_warning(expected_message=expected_message):
            bus.res_voltages
    for branch in small_network.branches.values():
        with check_result_warning(expected_message=expected_message):
            branch.res_currents
    for load in small_network.loads.values():
        with check_result_warning(expected_message=expected_message):
            load.res_currents
        if load.is_flexible and isinstance(load, PowerLoad):
            with check_result_warning(expected_message=expected_message):
                load.res_flexible_powers
    # for p_ref in small_network.potential_refs.values():
    #     with check_result_warning(expected_message=expected_message):
    #         p_ref.res_current

    # Ensure that a single warning is raised when having a data frame result
    expected_message = (
        "The results of this network may be outdated. Please re-run a load flow to ensure the validity of results."
    )
    with check_result_warning(expected_message=expected_message):
        small_network.res_buses_potentials
    with check_result_warning(expected_message=expected_message):
        small_network.res_buses_voltages
    with check_result_warning(expected_message=expected_message):
        small_network.res_branches_currents
    with check_result_warning(expected_message=expected_message):
        small_network.res_loads_currents
    with check_result_warning(expected_message=expected_message):
        small_network.res_loads_flexible_powers
