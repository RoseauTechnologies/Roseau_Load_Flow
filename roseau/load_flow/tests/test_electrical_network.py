import itertools as it
import re
import warnings
from contextlib import contextmanager

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from shapely import LineString, Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    FlexibleParameter,
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
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.units import Q_
from roseau.load_flow.utils import BranchTypeDtype, PhaseDtype, VoltagePhaseDtype, console


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
        sources=[vs],
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
        sources=[vs],
        grounds=[ground],
        potential_refs=[pref],
    )


@pytest.fixture()
def good_json_results() -> dict:
    return {
        "info": {
            "solver": "newton_goldstein",
            "solver_params": {"m1": 0.1, "m2": 0.9},
            "tolerance": 1e-06,
            "max_iterations": 20,
            "warm_start": True,
            "status": "success",
            "iterations": 1,
            "residual": 6.296829377361313e-14,
            "warm_started": True,
        },
        "buses": [
            {
                "id": "bus0",
                "phases": "abcn",
                "potentials": [
                    [20000.0, 2.891203383964549e-18],
                    [-10000.000000000002, -17320.508076],
                    [-10000.000000000002, 17320.508076],
                    [-1.3476481215690672e-12, 2.891203383964549e-18],
                ],
            },
            {
                "id": "bus1",
                "phases": "abcn",
                "potentials": [
                    [19999.949999875, 2.8911961559741588e-18],
                    [-9999.974999937502, -17320.464774621556],
                    [-9999.974999937502, 17320.464774621556],
                    [0.0, 0.0],
                ],
            },
        ],
        "branches": [
            {
                "id": "line",
                "phases1": "abcn",
                "phases2": "abcn",
                "currents1": [
                    [0.005000012500022422, 7.227990390093038e-25],
                    [-0.002500006250011211, -0.004330137844226556],
                    [-0.002500006250011211, 0.004330137844226556],
                    [-1.3476481215690672e-13, 2.891203383964549e-19],
                ],
                "currents2": [
                    [-0.005000012500022422, -7.227990390093038e-25],
                    [0.002500006250011211, 0.004330137844226556],
                    [0.002500006250011211, -0.004330137844226556],
                    [1.3476481215690672e-13, -2.891203383964549e-19],
                ],
            }
        ],
        "loads": [
            {
                "id": "load",
                "phases": "abcn",
                "currents": [
                    [0.0050000125000625, 7.228026530113222e-25],
                    [-0.002500006249963868, -0.004330137844254964],
                    [-0.002500006249963868, 0.004330137844254964],
                    [-1.3476372795473424e-13, 0.0],
                ],
            }
        ],
        "sources": [
            {
                "id": "vs",
                "phases": "abcn",
                "currents": [
                    [-0.00500001250003125, -8.673617379884035e-19],
                    [0.0025000062499482426, 0.004330137844227901],
                    [0.0025000062499482426, -0.0043301378442279],
                    [1.3476481215690672e-13, -2.891203383964549e-19],
                ],
            }
        ],
        "grounds": [
            {"id": "ground", "potential": [0.0, 0.0]},
        ],
        "potential_refs": [
            {"id": "pref", "current": [1.0842021724855044e-18, -2.891203383964549e-19]},
        ],
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
    assert e.value.args[0] == "The load 'power load' is disconnected and cannot be used anymore."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT
    new_load = PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    assert new_load.network == en

    # Disconnection of a source
    assert vs.network == en
    vs.disconnect()
    assert vs.network is None
    assert vs.bus is None
    with pytest.raises(RoseauLoadFlowException) as e:
        vs.to_dict()
    assert e.value.args[0] == "The voltage source 'vs' is disconnected and cannot be used anymore."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT

    # Bad key
    with pytest.raises(RoseauLoadFlowException) as e:
        en._disconnect_element(Ground("a separate ground element"))
    assert e.value.msg == "Ground(id='a separate ground element') is not a valid load or source."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Adding ground => impossible
    ground2 = Ground("ground2")
    with pytest.raises(RoseauLoadFlowException) as e:
        en._connect_element(ground2)
    assert e.value.msg == "Only lines, loads, buses and sources can be added to the network."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Remove line => impossible
    with pytest.raises(RoseauLoadFlowException) as e:
        en._disconnect_element(line)
    assert (
        e.value.msg
        == "Line(id='line', phases1='abcn', phases2='abcn', bus1='source', bus2='load bus') is a Line and it cannot "
        "be disconnected from a network."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT


def test_recursive_connect_disconnect():
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    VoltageSource(id="vs", phases="abcn", bus=source_bus, voltages=voltages)
    load = PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    lp = LineParameters("test", z_line=np.eye(4, dtype=complex))
    line = Line(id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)
    PotentialRef("pref", element=ground)
    en = ElectricalNetwork.from_element(source_bus)

    # Create new elements (without connecting them to the existing network)
    ground = en.grounds["ground"]
    new_bus2 = Bus(id="new_bus2", phases="abcn")
    new_load2 = PowerLoad(id="new_load2", bus=new_bus2, phases="abcn", powers=Q_([100, 0, 0], "VA"))
    new_bus = Bus(id="new_bus", phases="abcn")
    new_load = PowerLoad(id="new_load", bus=new_bus, phases="abcn", powers=Q_([100, 0, 0], "VA"))
    lp = LineParameters("S_AL_240_without_shunt", z_line=Q_(0.1 * np.eye(4), "ohm/km"), y_shunt=None)
    new_line2 = Line(
        id="new_line2",
        bus1=new_bus2,
        bus2=new_bus,
        phases="abcn",
        parameters=lp,
        length=0.5,
    )
    assert new_bus.network is None
    assert new_bus.id not in en.buses
    assert new_load.network is None
    assert new_load.id not in en.loads
    assert new_bus2.network is None
    assert new_bus2.id not in en.buses
    assert new_line2.network is None
    assert new_line2.id not in en.branches
    assert new_load2.network is None
    assert new_load2.id not in en.loads

    # Connect them to the first part of the network using a Line
    new_line = Line(
        id="new_line",
        bus1=new_bus,  # new part of the network
        bus2=load_bus,  # first part of the network
        phases="abcn",
        parameters=lp,
        length=0.5,
    )
    assert load_bus._connected_elements == [ground, load, line, new_line]
    assert new_bus.network == en
    assert new_bus._connected_elements == [new_load, new_line2, new_line]
    assert new_bus.id in en.buses
    assert new_line.network == en
    assert new_line._connected_elements == [new_bus, load_bus]
    assert new_line.id in en.branches
    assert new_load.network == en
    assert new_load._connected_elements == [new_bus]
    assert new_load.id in en.loads
    assert new_bus2.network == en
    assert new_bus2._connected_elements == [new_load2, new_line2]
    assert new_bus2.id in en.buses
    assert new_line2.network == en
    assert new_line2._connected_elements == [new_bus2, new_bus]
    assert new_line2.id in en.branches
    assert new_load2.network == en
    assert new_load2._connected_elements == [new_bus2]
    assert new_load2.id in en.loads

    # Disconnect a load
    new_load.disconnect()
    assert load_bus._connected_elements == [ground, load, line, new_line]
    assert new_bus.network == en
    assert new_bus._connected_elements == [new_line2, new_line]
    assert new_bus.id in en.buses
    assert new_line.network == en
    assert new_line._connected_elements == [new_bus, load_bus]
    assert new_line.id in en.branches
    assert new_load.network is None
    assert new_load._connected_elements == []
    assert new_load.id not in en.loads
    assert new_bus2.network == en
    assert new_bus2._connected_elements == [new_load2, new_line2]
    assert new_bus2.id in en.buses
    assert new_line2.network == en
    assert new_line2._connected_elements == [new_bus2, new_bus]
    assert new_line2.id in en.branches
    assert new_load2.network == en
    assert new_load2._connected_elements == [new_bus2]
    assert new_load2.id in en.loads


def test_recursive_connect_disconnect_ground():
    #
    # The same but with a "ground connection" from a line with shunt
    #
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    VoltageSource(id="vs", phases="abcn", bus=source_bus, voltages=voltages)
    PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    lp = LineParameters("test", z_line=np.eye(4, dtype=complex))
    Line(id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)
    PotentialRef("pref", element=ground)
    en = ElectricalNetwork.from_element(source_bus)

    # Create new elements (without connecting them to the existing network)
    ground = en.grounds["ground"]
    new_bus2 = Bus(id="new_bus2", phases="abcn")
    new_load2 = PowerLoad(id="new_load2", bus=new_bus2, phases="abcn", powers=Q_([100, 0, 0], "VA"))
    new_bus = Bus(id="new_bus", phases="abcn")
    new_load = PowerLoad(id="new_load", bus=new_bus, phases="abcn", powers=Q_([100, 0, 0], "VA"))
    assert new_bus.network is None
    assert new_bus.id not in en.buses
    assert new_load.network is None
    assert new_load.id not in en.loads
    assert new_bus2.network is None
    assert new_bus2.id not in en.buses
    assert new_load2.network is None
    assert new_load2.id not in en.loads

    lp = LineParameters(
        "S_AL_240_with_shunt", z_line=Q_(0.1 * np.eye(4), "ohm/km"), y_shunt=Q_(0.1 * np.eye(4), "S/km")
    )
    new_line2 = Line(
        id="new_line2",
        bus1=new_bus2,
        bus2=new_bus,
        phases="abcn",
        parameters=lp,
        ground=ground,  # Here, I connect a ground to the new_line2. The ground belongs to the previous network
        length=0.5,
    )
    assert new_line2.network == en
    assert new_line2.id in en.branches
    assert new_bus.network == en
    assert new_bus.id in en.buses
    assert new_load.network == en
    assert new_load.id in en.loads
    assert new_bus2.network == en
    assert new_bus2.id in en.buses
    assert new_load2.network == en
    assert new_load2.id in en.loads


def test_bad_networks():
    # No source
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
            sources=[vs],
            grounds=[ground],
            potential_refs=[p_ref],
        )
    assert "but has not been added to the network. It must be added with 'connect'." in e.value.msg
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
        "t", type="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
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

    # Bad ID
    src_bus = Bus("sb", phases="abcn")
    load_bus = Bus("lb", phases="abcn")
    ground = Ground("g")
    pref = PotentialRef("pr", element=ground)
    ground.connect(src_bus)
    lp = LineParameters("test", z_line=np.eye(4, dtype=complex))
    line = Line("ln", src_bus, load_bus, phases="abcn", parameters=lp, length=10)
    vs = VoltageSource("vs", src_bus, phases="abcn", voltages=[230, 120 + 150j, 120 - 150j])
    load = PowerLoad("pl", load_bus, phases="abcn", powers=[1000, 500, 1000])
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork(
            buses={"foo": src_bus, "lb": load_bus},  # <-- ID of src_bus is wrong
            branches={"ln": line},
            loads={"pl": load},
            sources={"vs": vs},
            grounds={"g": ground},
            potential_refs={"pr": pref},
        )
    assert e.value.msg == "Bus ID mismatch: 'foo' != 'sb'."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BUS_ID


def test_frame(small_network: ElectricalNetwork):
    # Buses
    buses_gdf = small_network.buses_frame
    assert isinstance(buses_gdf, gpd.GeoDataFrame)
    assert buses_gdf.shape == (2, 4)
    assert set(buses_gdf.columns) == {"phases", "min_voltage", "max_voltage", "geometry"}
    assert buses_gdf.index.name == "id"

    # Branches
    branches_gdf = small_network.branches_frame
    assert isinstance(branches_gdf, gpd.GeoDataFrame)
    assert branches_gdf.shape == (1, 6)
    assert set(branches_gdf.columns) == {"branch_type", "phases1", "phases2", "bus1_id", "bus2_id", "geometry"}
    assert branches_gdf.index.name == "id"

    # Transformers
    transformers_gdf = small_network.transformers_frame
    assert isinstance(transformers_gdf, gpd.GeoDataFrame)
    assert transformers_gdf.shape == (0, 7)
    assert set(transformers_gdf.columns) == {
        "phases1",
        "phases2",
        "bus1_id",
        "bus2_id",
        "parameters_id",
        "max_power",
        "geometry",
    }
    assert transformers_gdf.index.name == "id"

    # Lines
    lines_gdf = small_network.lines_frame
    assert isinstance(lines_gdf, gpd.GeoDataFrame)
    assert lines_gdf.shape == (1, 6)
    assert set(lines_gdf.columns) == {"phases", "bus1_id", "bus2_id", "parameters_id", "max_current", "geometry"}

    # Switches
    switches_gdf = small_network.switches_frame
    assert isinstance(switches_gdf, gpd.GeoDataFrame)
    assert switches_gdf.shape == (0, 4)
    assert set(switches_gdf.columns) == {"phases", "bus1_id", "bus2_id", "geometry"}

    # Loads
    loads_df = small_network.loads_frame
    assert isinstance(loads_df, pd.DataFrame)
    assert loads_df.shape == (1, 2)
    assert set(loads_df.columns) == {"phases", "bus_id"}
    assert loads_df.index.name == "id"

    # Sources
    sources_df = small_network.sources_frame
    assert isinstance(sources_df, pd.DataFrame)
    assert sources_df.shape == (1, 2)
    assert set(sources_df.columns) == {"phases", "bus_id"}
    assert sources_df.index.name == "id"


def test_empty_network():
    with pytest.raises(RoseauLoadFlowException) as exc_info:
        ElectricalNetwork(
            buses={},
            branches={},
            loads={},
            sources={},
            grounds={},
            potential_refs={},
        )
    assert exc_info.value.code == RoseauLoadFlowExceptionCode.EMPTY_NETWORK
    assert exc_info.value.msg == "Cannot create a network without elements."


def test_buses_voltages(small_network: ElectricalNetwork, good_json_results):
    assert isinstance(small_network, ElectricalNetwork)
    small_network.results_from_dict(good_json_results)
    small_network.buses["bus0"].max_voltage = 21_000
    small_network.buses["bus1"].min_voltage = 20_000

    voltage_records = [
        {
            "bus_id": "bus0",
            "phase": "an",
            "voltage": 20000.0 + 0.0j,
            "min_voltage": np.nan,
            "max_voltage": 21000,
            "violated": False,
        },
        {
            "bus_id": "bus0",
            "phase": "bn",
            "voltage": -10000.0 + -17320.508076j,
            "min_voltage": np.nan,
            "max_voltage": 21000,
            "violated": False,
        },
        {
            "bus_id": "bus0",
            "phase": "cn",
            "voltage": -10000.0 + 17320.508076j,
            "min_voltage": np.nan,
            "max_voltage": 21000,
            "violated": False,
        },
        {
            "bus_id": "bus1",
            "phase": "an",
            "voltage": 19999.949999875 + 0.0j,
            "min_voltage": 20000,
            "max_voltage": np.nan,
            "violated": True,
        },
        {
            "bus_id": "bus1",
            "phase": "bn",
            "voltage": -9999.9749999375 + -17320.464774621556j,
            "min_voltage": 20000,
            "max_voltage": np.nan,
            "violated": True,
        },
        {
            "bus_id": "bus1",
            "phase": "cn",
            "voltage": -9999.9749999375 + 17320.464774621556j,
            "min_voltage": 20000,
            "max_voltage": np.nan,
            "violated": True,
        },
    ]

    buses_voltages = small_network.res_buses_voltages
    expected_buses_voltages = (
        pd.DataFrame.from_records(voltage_records)
        .astype(
            {
                "bus_id": str,
                "phase": VoltagePhaseDtype,
                "voltage": complex,
                "min_voltage": float,
                "max_voltage": float,
                "violated": pd.BooleanDtype(),
            }
        )
        .set_index(["bus_id", "phase"])
    )

    assert isinstance(buses_voltages, pd.DataFrame)
    assert buses_voltages.shape == (6, 4)
    assert buses_voltages.index.names == ["bus_id", "phase"]
    assert list(buses_voltages.columns) == ["voltage", "min_voltage", "max_voltage", "violated"]
    assert_frame_equal(buses_voltages, expected_buses_voltages)


def test_to_from_dict_roundtrip(small_network: ElectricalNetwork):
    net_dict = small_network.to_dict()
    new_net = ElectricalNetwork.from_dict(net_dict)
    assert_frame_equal(small_network.buses_frame, new_net.buses_frame)
    assert_frame_equal(small_network.branches_frame, new_net.branches_frame)
    assert_frame_equal(small_network.loads_frame, new_net.loads_frame)
    assert_frame_equal(small_network.sources_frame, new_net.sources_frame)


def test_single_phase_network(single_phase_network: ElectricalNetwork):
    # Test dict conversion
    # ====================
    net_dict = single_phase_network.to_dict()
    new_net = ElectricalNetwork.from_dict(net_dict)
    assert_frame_equal(single_phase_network.buses_frame, new_net.buses_frame)
    assert_frame_equal(single_phase_network.branches_frame, new_net.branches_frame)
    assert_frame_equal(single_phase_network.transformers_frame, new_net.transformers_frame)
    assert_frame_equal(single_phase_network.lines_frame, new_net.lines_frame)
    assert_frame_equal(single_phase_network.switches_frame, new_net.switches_frame)
    assert_frame_equal(single_phase_network.loads_frame, new_net.loads_frame)
    assert_frame_equal(single_phase_network.sources_frame, new_net.sources_frame)

    # Test load flow results
    # ======================
    source_bus = single_phase_network.buses["bus0"]
    load_bus = single_phase_network.buses["bus1"]
    line = single_phase_network.branches["line"]
    load = single_phase_network.loads["load"]

    single_phase_network.solve_load_flow()

    # Test results of elements
    # ------------------------
    assert np.allclose(source_bus.res_potentials.m_as("V"), [19999.94999975 + 0j, -0.050000250001249996 + 0j])
    assert np.allclose(load_bus.res_potentials.m_as("V"), [19999.899999499998 + 0j, 0j])
    assert np.allclose(line.res_currents[0].m_as("A"), [0.005000025000117603 + 0j, -0.005000025000125 + 0j])
    assert np.allclose(line.res_currents[1].m_as("A"), [-0.005000025000117603 - 0j, 0.005000025000125 - 0j])
    assert np.allclose(load.res_currents.m_as("A"), [0.005000025000250002 - 0j, -0.005000025000250002 - 0j])

    # Test results of network
    # -----------------------
    # Buses results
    pd.testing.assert_frame_equal(
        single_phase_network.res_buses,
        pd.DataFrame.from_records(
            [
                {"bus_id": "bus0", "phase": "b", "potential": 19999.94999975 + 0j},
                {"bus_id": "bus0", "phase": "n", "potential": -0.050000250001249996 + 0j},
                {"bus_id": "bus1", "phase": "b", "potential": 19999.899999499998 + 0j},
                {"bus_id": "bus1", "phase": "n", "potential": 0j},
            ]
        )
        .astype({"phase": PhaseDtype, "potential": complex})
        .set_index(["bus_id", "phase"]),
    )
    # Buses voltages results
    pd.testing.assert_frame_equal(
        single_phase_network.res_buses_voltages,
        pd.DataFrame.from_records(
            [
                {
                    "bus_id": "bus0",
                    "phase": "bn",
                    "voltage": (19999.94999975 + 0j) - (-0.050000250001249996 + 0j),
                    "min_voltage": np.nan,
                    "max_voltage": np.nan,
                    "violated": None,
                },
                {
                    "bus_id": "bus1",
                    "phase": "bn",
                    "voltage": (19999.899999499998 + 0j) - (0j),
                    "min_voltage": np.nan,
                    "max_voltage": np.nan,
                    "violated": None,
                },
            ]
        )
        .astype(
            {
                "phase": VoltagePhaseDtype,
                "voltage": complex,
                "min_voltage": float,
                "max_voltage": float,
                "violated": pd.BooleanDtype(),
            }
        )
        .set_index(["bus_id", "phase"]),
    )
    # Branches results
    pd.testing.assert_frame_equal(
        single_phase_network.res_branches,
        pd.DataFrame.from_records(
            [
                {
                    "branch_id": "line",
                    "phase": "b",
                    "branch_type": "line",
                    "current1": 0.005000025000117603 + 0j,
                    "current2": -0.005000025000117603 - 0j,
                    "power1": (19999.94999975 + 0j) * (0.005000025000117603 + 0j).conjugate(),
                    "power2": (19999.899999499998 + 0j) * (-0.005000025000117603 - 0j).conjugate(),
                    "potential1": 19999.94999975 + 0j,
                    "potential2": 19999.899999499998 + 0j,
                },
                {
                    "branch_id": "line",
                    "phase": "n",
                    "branch_type": "line",
                    "current1": -0.005000025000125 + 0j,
                    "current2": 0.005000025000125 - 0j,
                    "power1": (-0.050000250001249996 + 0j) * (-0.005000025000125 + 0j).conjugate(),
                    "power2": (0j) * (0.005000025000125 - 0j).conjugate(),
                    "potential1": -0.050000250001249996 + 0j,
                    "potential2": 0j,
                },
            ]
        )
        .astype(
            {
                "phase": PhaseDtype,
                "branch_type": BranchTypeDtype,
                "current1": complex,
                "current2": complex,
                "power1": complex,
                "power2": complex,
                "potential1": complex,
                "potential2": complex,
            }
        )
        .set_index(["branch_id", "phase"]),
    )

    # Transformers results
    pd.testing.assert_frame_equal(
        single_phase_network.res_transformers,
        pd.DataFrame.from_records(
            [],
            columns=[
                "transformer_id",
                "phase",
                "current1",
                "current2",
                "power1",
                "power2",
                "potential1",
                "potential2",
                "max_power",
                "violated",
            ],
        )
        .astype(
            {
                "phase": PhaseDtype,
                "current1": complex,
                "current2": complex,
                "power1": complex,
                "power2": complex,
                "potential1": complex,
                "potential2": complex,
                "max_power": float,
                "violated": pd.BooleanDtype(),
            }
        )
        .set_index(["transformer_id", "phase"]),
    )
    # Lines results
    pd.testing.assert_frame_equal(
        single_phase_network.res_lines,
        pd.DataFrame.from_records(
            [
                {
                    "line_id": "line",
                    "phase": "b",
                    "current1": 0.005000025000117603 + 0j,
                    "current2": -0.005000025000117603 - 0j,
                    "power1": (19999.94999975 + 0j) * (0.005000025000117603 + 0j).conjugate(),
                    "power2": (19999.899999499998 + 0j) * (-0.005000025000117603 - 0j).conjugate(),
                    "potential1": 19999.94999975 + 0j,
                    "potential2": 19999.899999499998 + 0j,
                    "series_losses": (
                        (19999.94999975 + 0j) * (0.005000025000117603 + 0j).conjugate()
                        + (19999.899999499998 + 0j) * (-0.005000025000117603 - 0j).conjugate()
                    ),
                    "series_current": 0.005000025000117603 + 0j,
                    "max_current": np.nan,
                    "violated": None,
                },
                {
                    "line_id": "line",
                    "phase": "n",
                    "current1": -0.005000025000125 + 0j,
                    "current2": 0.005000025000125 - 0j,
                    "power1": (-0.050000250001249996 + 0j) * (-0.005000025000125 + 0j).conjugate(),
                    "power2": (0j) * (0.005000025000125 - 0j).conjugate(),
                    "potential1": -0.050000250001249996 + 0j,
                    "potential2": 0j,
                    "series_losses": (
                        (-0.050000250001249996 + 0j) * (-0.005000025000125 + 0j).conjugate()
                        + (0j) * (0.005000025000125 - 0j).conjugate()
                    ),
                    "series_current": -0.005000025000125 + 0j,
                    "max_current": np.nan,
                    "violated": None,
                },
            ]
        )
        .astype(
            {
                "phase": PhaseDtype,
                "current1": complex,
                "current2": complex,
                "power1": complex,
                "power2": complex,
                "potential1": complex,
                "potential2": complex,
                "series_losses": complex,
                "series_current": complex,
                "max_current": float,
                "violated": pd.BooleanDtype(),
            }
        )
        .set_index(["line_id", "phase"]),
    )
    # Switches results
    pd.testing.assert_frame_equal(
        single_phase_network.res_switches,
        pd.DataFrame.from_records(
            [],
            columns=[
                "switch_id",
                "phase",
                "current1",
                "current2",
                "power1",
                "power2",
                "potential1",
                "potential2",
            ],
        )
        .astype(
            {
                "phase": PhaseDtype,
                "current1": complex,
                "current2": complex,
                "power1": complex,
                "power2": complex,
                "potential1": complex,
                "potential2": complex,
            }
        )
        .set_index(["switch_id", "phase"]),
    )
    # Loads results
    pd.testing.assert_frame_equal(
        single_phase_network.res_loads,
        pd.DataFrame.from_records(
            [
                {
                    "load_id": "load",
                    "phase": "b",
                    "current": 0.005000025000250002 - 0j,
                    "power": (19999.899999499998 + 0j) * (0.005000025000250002 - 0j).conjugate(),
                    "potential": 19999.899999499998 + 0j,
                },
                {
                    "load_id": "load",
                    "phase": "n",
                    "current": -0.005000025000250002 - 0j,
                    "power": (0j) * (-0.005000025000250002 - 0j).conjugate(),
                    "potential": 0j,
                },
            ]
        )
        .astype({"phase": PhaseDtype, "current": complex, "power": complex, "potential": complex})
        .set_index(["load_id", "phase"]),
    )


def test_network_elements(small_network: ElectricalNetwork):
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


def test_network_results_warning(small_network: ElectricalNetwork, recwarn):  # noqa: C901
    # network well-defined using the constructor
    for bus in small_network.buses.values():
        assert bus.network == small_network
    for load in small_network.loads.values():
        assert load.network == small_network
    for source in small_network.sources.values():
        assert source.network == small_network
    for branch in small_network.branches.values():
        assert branch.network == small_network
    for ground in small_network.grounds.values():
        assert ground.network == small_network
    for p_ref in small_network.potential_refs.values():
        assert p_ref.network == small_network

    # All the results function raises an exception
    for bus in small_network.buses.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = bus.res_potentials
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = bus.res_voltages
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for branch in small_network.branches.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = branch.res_currents
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for load in small_network.loads.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = load.res_currents
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
        if load.is_flexible and isinstance(load, PowerLoad):
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = load.res_flexible_powers
            assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for source in small_network.sources.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = source.res_currents
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for ground in small_network.grounds.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = ground.res_potential
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for p_ref in small_network.potential_refs.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = p_ref.res_current
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN

    # Solve a load flow
    small_network.solve_load_flow()

    # No warning when getting results (they are up-to-date)
    recwarn.clear()
    for bus in small_network.buses.values():
        _ = bus.res_potentials
        _ = bus.res_voltages
    for branch in small_network.branches.values():
        _ = branch.res_currents
    for load in small_network.loads.values():
        _ = load.res_currents
        if load.is_flexible and isinstance(load, PowerLoad):
            _ = load.res_flexible_powers
    for source in small_network.sources.values():
        _ = source.res_currents
    for ground in small_network.grounds.values():
        _ = ground.res_potential
    for p_ref in small_network.potential_refs.values():
        _ = p_ref.res_current
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
            _ = bus.res_potentials
        with check_result_warning(expected_message=expected_message):
            _ = bus.res_voltages
    for branch in small_network.branches.values():
        with check_result_warning(expected_message=expected_message):
            _ = branch.res_currents
    for load in small_network.loads.values():
        with check_result_warning(expected_message=expected_message):
            _ = load.res_currents
        if load.is_flexible and isinstance(load, PowerLoad):
            with check_result_warning(expected_message=expected_message):
                _ = load.res_flexible_powers
    for source in small_network.sources.values():
        with check_result_warning(expected_message=expected_message):
            _ = source.res_currents
    for ground in small_network.grounds.values():
        with check_result_warning(expected_message=expected_message):
            _ = ground.res_potential
    for p_ref in small_network.potential_refs.values():
        with check_result_warning(expected_message=expected_message):
            _ = p_ref.res_current

    # Ensure that a single warning is raised when having a data frame result
    expected_message = (
        "The results of this network may be outdated. Please re-run a load flow to ensure the validity of results."
    )
    with check_result_warning(expected_message=expected_message):
        _ = small_network.res_buses
    with check_result_warning(expected_message=expected_message):
        _ = small_network.res_buses_voltages
    with check_result_warning(expected_message=expected_message):
        _ = small_network.res_branches
    with check_result_warning(expected_message=expected_message):
        _ = small_network.res_loads
    with check_result_warning(expected_message=expected_message):
        _ = small_network.res_sources
    with check_result_warning(expected_message=expected_message):
        _ = small_network.res_loads_flexible_powers


def test_load_flow_results_frames(small_network: ElectricalNetwork, good_json_results: dict):
    small_network.results_from_dict(good_json_results)
    small_network.buses["bus0"].min_voltage = 21_000

    # Buses results
    expected_res_buses = (
        pd.DataFrame.from_records(
            [
                {"bus_id": "bus0", "phase": "a", "potential": 20000 + 2.89120e-18j},
                {"bus_id": "bus0", "phase": "b", "potential": -10000.00000 - 17320.50807j},
                {"bus_id": "bus0", "phase": "c", "potential": -10000.00000 + 17320.50807j},
                {"bus_id": "bus0", "phase": "n", "potential": -1.34764e-12 + 2.89120e-18j},
                {"bus_id": "bus1", "phase": "a", "potential": 19999.94999 + 2.89119e-18j},
                {"bus_id": "bus1", "phase": "b", "potential": -9999.97499 - 17320.46477j},
                {"bus_id": "bus1", "phase": "c", "potential": -9999.97499 + 17320.46477j},
                {"bus_id": "bus1", "phase": "n", "potential": 0j},
            ]
        )
        .astype({"bus_id": object, "phase": PhaseDtype, "potential": complex})
        .set_index(["bus_id", "phase"])
    )
    assert_frame_equal(small_network.res_buses, expected_res_buses, rtol=1e-4)

    # Buses voltages results
    expected_res_buses_voltages = (
        pd.DataFrame.from_records(
            [
                {
                    "bus_id": "bus0",
                    "phase": "an",
                    "voltage": (20000 + 2.89120e-18j) - (-1.34764e-12 + 2.89120e-18j),
                    "min_voltage": 21_000,
                    "max_voltage": np.nan,
                    "violated": True,
                },
                {
                    "bus_id": "bus0",
                    "phase": "bn",
                    "voltage": (-10000.00000 - 17320.50807j) - (-1.34764e-12 + 2.89120e-18j),
                    "min_voltage": 21_000,
                    "max_voltage": np.nan,
                    "violated": True,
                },
                {
                    "bus_id": "bus0",
                    "phase": "cn",
                    "voltage": (-10000.00000 + 17320.50807j) - (-1.34764e-12 + 2.89120e-18j),
                    "min_voltage": 21_000,
                    "max_voltage": np.nan,
                    "violated": True,
                },
                {
                    "bus_id": "bus1",
                    "phase": "an",
                    "voltage": (19999.94999 + 2.89119e-18j) - (0j),
                    "min_voltage": np.nan,
                    "max_voltage": np.nan,
                    "violated": None,
                },
                {
                    "bus_id": "bus1",
                    "phase": "bn",
                    "voltage": (-9999.97499 - 17320.46477j) - (0j),
                    "min_voltage": np.nan,
                    "max_voltage": np.nan,
                    "violated": None,
                },
                {
                    "bus_id": "bus1",
                    "phase": "cn",
                    "voltage": (-9999.97499 + 17320.46477j) - (0j),
                    "min_voltage": np.nan,
                    "max_voltage": np.nan,
                    "violated": None,
                },
            ]
        )
        .astype(
            {
                "bus_id": object,
                "phase": VoltagePhaseDtype,
                "voltage": complex,
                "min_voltage": float,
                "max_voltage": float,
                "violated": pd.BooleanDtype(),
            }
        )
        .set_index(["bus_id", "phase"])
    )
    assert_frame_equal(small_network.res_buses_voltages, expected_res_buses_voltages, rtol=1e-4)

    # Branches results
    expected_res_branches = (
        pd.DataFrame.from_records(
            [
                {
                    "branch_id": "line",
                    "phase": "a",
                    "branch_type": "line",
                    "current1": 0.00500 + 7.22799e-25j,
                    "current2": -0.00500 - 7.22799e-25j,
                    "power1": (20000 + 2.89120e-18j) * (0.00500 + 7.22799e-25j).conjugate(),
                    "power2": (19999.94999 + 2.89119e-18j) * (-0.00500 - 7.22799e-25j).conjugate(),
                    "potential1": 20000 + 2.89120e-18j,
                    "potential2": 19999.94999 + 2.89119e-18j,
                },
                {
                    "branch_id": "line",
                    "phase": "b",
                    "branch_type": "line",
                    "current1": -0.00250 - 0.00433j,
                    "current2": 0.00250 + 0.00433j,
                    "power1": (-10000.00000 - 17320.50807j) * (-0.00250 - 0.00433j).conjugate(),
                    "power2": (-9999.97499 - 17320.46477j) * (0.00250 + 0.00433j).conjugate(),
                    "potential1": -10000.00000 - 17320.50807j,
                    "potential2": -9999.97499 - 17320.46477j,
                },
                {
                    "branch_id": "line",
                    "phase": "c",
                    "branch_type": "line",
                    "current1": -0.00250 + 0.00433j,
                    "current2": 0.00250 - 0.00433j,
                    "power1": (-10000.00000 + 17320.50807j) * (-0.00250 + 0.00433j).conjugate(),
                    "power2": (-9999.97499 + 17320.46477j) * (0.00250 - 0.00433j).conjugate(),
                    "potential1": -10000.00000 + 17320.50807j,
                    "potential2": -9999.97499 + 17320.46477j,
                },
                {
                    "branch_id": "line",
                    "phase": "n",
                    "branch_type": "line",
                    "current1": -1.34764e-13 + 2.89120e-19j,
                    "current2": 1.34764e-13 - 2.89120e-19j,
                    "power1": (-1.34764e-12 + 2.89120e-18j) * (-1.34764e-13 + 2.89120e-19j).conjugate(),
                    "power2": (0j) * (1.34764e-13 - 2.89120e-19j).conjugate(),
                    "potential1": -1.34764e-12 + 2.89120e-18j,
                    "potential2": 0j,
                },
            ],
        )
        .astype(
            {
                "branch_id": object,
                "phase": PhaseDtype,
                "branch_type": BranchTypeDtype,
                "current1": complex,
                "current2": complex,
                "power1": complex,
                "power2": complex,
                "potential1": complex,
                "potential2": complex,
            }
        )
        .set_index(["branch_id", "phase"])
    )
    assert_frame_equal(small_network.res_branches, expected_res_branches, rtol=1e-4)

    # Transformers results
    expected_res_transformers = (
        pd.DataFrame.from_records(
            [],
            columns=[
                "transformer_id",
                "phase",
                "current1",
                "current2",
                "power1",
                "power2",
                "potential1",
                "potential2",
                "max_power",
                "violated",
            ],
        )
        .astype(
            {
                "transformer_id": object,
                "phase": PhaseDtype,
                "current1": complex,
                "current2": complex,
                "power1": complex,
                "power2": complex,
                "potential1": complex,
                "potential2": complex,
                "max_power": float,
                "violated": pd.BooleanDtype(),
            }
        )
        .set_index(["transformer_id", "phase"])
    )
    assert_frame_equal(small_network.res_transformers, expected_res_transformers)

    # Lines results
    expected_res_lines_records = [
        {
            "line_id": "line",
            "phase": "a",
            "current1": 0.00500 + 7.22799e-25j,
            "current2": -0.00500 - 7.22799e-25j,
            "power1": (20000 + 2.89120e-18j) * (0.00500 + 7.22799e-25j).conjugate(),
            "power2": (19999.94999 + 2.89119e-18j) * (-0.00500 - 7.22799e-25j).conjugate(),
            "potential1": 20000 + 2.89120e-18j,
            "potential2": 19999.94999 + 2.89119e-18j,
            "series_losses": (
                (20000 + 2.89120e-18j) * (0.00500 + 7.22799e-25j).conjugate()
                + (19999.94999 + 2.89119e-18j) * (-0.00500 - 7.22799e-25j).conjugate()
            ),
            "series_current": 0.00500 + 7.22799e-25j,
            "max_current": np.nan,
            "violated": None,
        },
        {
            "line_id": "line",
            "phase": "b",
            "current1": -0.00250 - 0.00433j,
            "current2": 0.00250 + 0.00433j,
            "power1": (-10000.00000 - 17320.50807j) * (-0.00250 - 0.00433j).conjugate(),
            "power2": (-9999.97499 - 17320.46477j) * (0.00250 + 0.00433j).conjugate(),
            "potential1": -10000.00000 - 17320.50807j,
            "potential2": -9999.97499 - 17320.46477j,
            "series_losses": (
                (-10000.00000 - 17320.50807j) * (-0.00250 - 0.00433j).conjugate()
                + (-9999.97499 - 17320.46477j) * (0.00250 + 0.00433j).conjugate()
            ),
            "series_current": -0.00250 - 0.00433j,
            "max_current": np.nan,
            "violated": None,
        },
        {
            "line_id": "line",
            "phase": "c",
            "current1": -0.00250 + 0.00433j,
            "current2": 0.00250 - 0.00433j,
            "power1": (-10000.00000 + 17320.50807j) * (-0.00250 + 0.00433j).conjugate(),
            "power2": (-9999.97499 + 17320.46477j) * (0.00250 - 0.00433j).conjugate(),
            "potential1": -10000.00000 + 17320.50807j,
            "potential2": -9999.97499 + 17320.46477j,
            "series_losses": (
                (-10000.00000 + 17320.50807j) * (-0.00250 + 0.00433j).conjugate()
                + (-9999.97499 + 17320.46477j) * (0.00250 - 0.00433j).conjugate()
            ),
            "series_current": -0.00250 + 0.00433j,
            "max_current": np.nan,
            "violated": None,
        },
        {
            "line_id": "line",
            "phase": "n",
            "current1": -1.34764e-13 + 2.89120e-19j,
            "current2": 1.34764e-13 - 2.89120e-19j,
            "power1": (-1.34764e-12 + 2.89120e-18j) * (-1.34764e-13 + 2.89120e-19j).conjugate(),
            "power2": (0j) * (1.34764e-13 - 2.89120e-19j).conjugate(),
            "potential1": -1.34764e-12 + 2.89120e-18j,
            "potential2": 0j,
            "series_losses": (
                (-1.34764e-12 + 2.89120e-18j) * (-1.34764e-13 + 2.89120e-19j).conjugate()
                + (0j) * (1.34764e-13 - 2.89120e-19j).conjugate()
            ),
            "series_current": -1.34764e-13 + 2.89120e-19j,
            "max_current": np.nan,
            "violated": None,
        },
    ]
    expected_res_lines_dtypes = {
        "line_id": object,
        "phase": PhaseDtype,
        "current1": complex,
        "current2": complex,
        "power1": complex,
        "power2": complex,
        "potential1": complex,
        "potential2": complex,
        "series_losses": complex,
        "series_current": complex,
        "max_current": float,
        "violated": pd.BooleanDtype(),
    }
    expected_res_lines = (
        pd.DataFrame.from_records(expected_res_lines_records)
        .astype(expected_res_lines_dtypes)
        .set_index(["line_id", "phase"])
    )
    assert_frame_equal(small_network.res_lines, expected_res_lines, rtol=1e-4, atol=1e-5)

    # Lines with violated max current
    small_network.branches["line"].parameters.max_current = 0.002
    expected_res_lines_violated_records = [
        d | {"max_current": 0.002, "violated": d["phase"] != "n"} for d in expected_res_lines_records
    ]
    expected_res_violated_lines = (
        pd.DataFrame.from_records(expected_res_lines_violated_records)
        .astype(expected_res_lines_dtypes)
        .set_index(["line_id", "phase"])
    )
    assert_frame_equal(small_network.res_lines, expected_res_violated_lines, rtol=1e-4, atol=1e-5)

    # Switches results
    expected_res_switches = (
        pd.DataFrame.from_records(
            [],
            columns=[
                "switch_id",
                "phase",
                "current1",
                "current2",
                "power1",
                "power2",
                "potential1",
                "potential2",
            ],
        )
        .astype(
            {
                "switch_id": object,
                "phase": PhaseDtype,
                "current1": complex,
                "current2": complex,
                "power1": complex,
                "power2": complex,
                "potential1": complex,
                "potential2": complex,
            }
        )
        .set_index(["switch_id", "phase"])
    )
    assert_frame_equal(small_network.res_switches, expected_res_switches)

    # Loads results
    expected_res_loads = (
        pd.DataFrame.from_records(
            [
                {
                    "load_id": "load",
                    "phase": "a",
                    "current": 0.00500 + 7.22802e-25j,
                    "power": (19999.94999 + 2.89119e-18j) * (0.00500 + 7.22802e-25j).conjugate(),
                    "potential": 19999.94999 + 2.89119e-18j,
                },
                {
                    "load_id": "load",
                    "phase": "b",
                    "current": -0.00250 - 0.00433j,
                    "power": (-9999.97499 - 17320.46477j) * (-0.00250 - 0.00433j).conjugate(),
                    "potential": -9999.97499 - 17320.46477j,
                },
                {
                    "load_id": "load",
                    "phase": "c",
                    "current": -0.00250 + 0.00433j,
                    "power": (-9999.97499 + 17320.46477j) * (-0.00250 + 0.00433j).conjugate(),
                    "potential": -9999.97499 + 17320.46477j,
                },
                {
                    "load_id": "load",
                    "phase": "n",
                    "current": -1.34763e-13 + 0j,
                    "power": (0j) * (-1.34763e-13 + 0j).conjugate(),
                    "potential": 0j,
                },
            ]
        )
        .astype(
            {
                "load_id": object,
                "phase": PhaseDtype,
                "current": complex,
                "power": complex,
                "potential": complex,
            }
        )
        .set_index(["load_id", "phase"])
    )
    assert_frame_equal(small_network.res_loads, expected_res_loads, rtol=1e-4)

    # Sources results
    expected_res_sources = (
        pd.DataFrame.from_records(
            [
                {
                    "source_id": "vs",
                    "phase": "a",
                    "current": -0.00500 + 0j,
                    "power": (20000 + 2.89120e-18j) * (-0.00500 + 0j).conjugate(),
                    "potential": 20000 + 2.89120e-18j,
                },
                {
                    "source_id": "vs",
                    "phase": "b",
                    "current": 0.00250 + 0.00433j,
                    "power": (-10000.00000 - 17320.50807j) * (0.00250 + 0.00433j).conjugate(),
                    "potential": -10000.00000 - 17320.50807j,
                },
                {
                    "source_id": "vs",
                    "phase": "c",
                    "current": 0.00250 - 0.00433j,
                    "power": (-10000.00000 + 17320.50807j) * (0.00250 - 0.00433j).conjugate(),
                    "potential": -10000.00000 + 17320.50807j,
                },
                {
                    "source_id": "vs",
                    "phase": "n",
                    "current": 1.34764e-13 - 2.89121e-19j,
                    "power": (-1.34764e-12 + 2.89120e-18j) * (1.34764e-13 - 2.89121e-19j).conjugate(),
                    "potential": -1.34764e-12 + 2.89120e-18j,
                },
            ]
        )
        .astype(
            {
                "source_id": object,
                "phase": PhaseDtype,
                "current": complex,
                "power": complex,
                "potential": complex,
            }
        )
        .set_index(["source_id", "phase"])
    )
    assert_frame_equal(small_network.res_sources, expected_res_sources, rtol=1e-4)

    # Grounds results
    expected_res_grounds = (
        pd.DataFrame.from_records(
            [
                {"ground_id": "ground", "potential": 0j},
            ]
        )
        .astype({"ground_id": object, "potential": complex})
        .set_index(["ground_id"])
    )
    assert_frame_equal(small_network.res_grounds, expected_res_grounds)

    # Potential refs results
    expected_res_potential_refs = (
        pd.DataFrame.from_records(
            [
                {"potential_ref_id": "pref", "current": 1.08420e-18 - 2.89120e-19j},
            ]
        )
        .astype({"potential_ref_id": object, "current": complex})
        .set_index(["potential_ref_id"])
    )
    assert_frame_equal(small_network.res_potential_refs, expected_res_potential_refs)

    # No flexible loads
    assert small_network.res_loads_flexible_powers.empty

    # Let's add a flexible load
    fp = FlexibleParameter.p_max_u_consumption(u_min=16000, u_down=17000, s_max=1000)
    load = small_network.loads["load"]
    assert isinstance(load, PowerLoad)
    load._flexible_params = [fp, fp, fp]
    good_json_results = good_json_results.copy()
    good_json_results["loads"][0]["powers"] = [
        [99.99999999999994, 0.0],
        [99.99999999999994, 0.0],
        [99.99999999999994, 0.0],
    ]
    small_network.results_from_dict(good_json_results)
    expected_res_flex_powers = (
        pd.DataFrame.from_records(
            [
                {
                    "load_id": "load",
                    "phase": "an",
                    "power": 99.99999999999994 + 0j,
                },
                {
                    "load_id": "load",
                    "phase": "bn",
                    "power": 99.99999999999994 + 0j,
                },
                {
                    "load_id": "load",
                    "phase": "cn",
                    "power": 99.99999999999994 + 0j,
                },
            ]
        )
        .astype({"load_id": object, "phase": VoltagePhaseDtype, "power": complex})
        .set_index(["load_id", "phase"])
    )
    assert_frame_equal(small_network.res_loads_flexible_powers, expected_res_flex_powers, rtol=1e-4)


def test_solver_warm_start(small_network: ElectricalNetwork, good_json_results, monkeypatch):
    load: PowerLoad = small_network.loads["load"]
    load_bus = small_network.buses["bus1"]

    def compare_results(expected, obtained):
        if isinstance(expected, dict):
            assert isinstance(obtained, dict)
            for key, value in expected.items():
                assert key in obtained
                compare_results(value, obtained[key])
        elif isinstance(expected, list | tuple):
            assert isinstance(obtained, list | tuple)
            for i, item in enumerate(expected):
                compare_results(item, obtained[i])
        elif isinstance(expected, bool):
            assert isinstance(obtained, bool)
            assert expected == obtained
        elif isinstance(expected, complex | float | int):
            assert isinstance(obtained, complex | float | int)
            assert np.isclose(expected, obtained, atol=1e-1)
        else:
            assert isinstance(obtained, type(expected))
            assert expected == obtained

    original_propagate_potentials = small_network._propagate_potentials
    original_reset_inputs = small_network._reset_inputs

    def _propagate_potentials():
        nonlocal propagate_potentials_called
        propagate_potentials_called = True
        return original_propagate_potentials()

    def _reset_inputs():
        nonlocal reset_inputs_called
        reset_inputs_called = True
        return original_reset_inputs()

    monkeypatch.setattr(small_network, "_propagate_potentials", _propagate_potentials)
    monkeypatch.setattr(small_network, "_reset_inputs", _reset_inputs)

    # First case: network is valid, no results yet -> no warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    good_json_results["info"]["warm_start"] = True
    good_json_results["info"]["warm_started"] = False
    assert small_network._valid
    assert not small_network.res_info  # No results
    assert not small_network._results_valid  # Results are not valid by default
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        good_json_results["info"]["iterations"] = small_network.solve_load_flow(warm_start=True)
    compare_results(good_json_results, small_network.results_to_dict())
    assert not propagate_potentials_called  # Is not called because it was already called in the constructor
    assert not reset_inputs_called

    # Second case: the user requested no warm start (even though the network and results are valid)
    propagate_potentials_called = False
    reset_inputs_called = False
    good_json_results["info"]["warm_start"] = False
    good_json_results["info"]["warm_started"] = False
    assert small_network._valid
    assert small_network._results_valid
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        good_json_results["info"]["iterations"] = small_network.solve_load_flow(warm_start=False)
    compare_results(good_json_results, small_network.results_to_dict())
    assert not propagate_potentials_called
    assert reset_inputs_called

    # Third case: network is valid, results are valid -> warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    good_json_results["info"]["warm_start"] = True
    good_json_results["info"]["warm_started"] = True
    assert small_network._valid
    assert small_network._results_valid
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        good_json_results["info"]["iterations"] = small_network.solve_load_flow(warm_start=True)
    compare_results(good_json_results, small_network.results_to_dict())
    assert not propagate_potentials_called
    assert not reset_inputs_called

    # Fourth case (load powers changes): network is valid, results are not valid -> warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    good_json_results["info"]["warm_start"] = True
    good_json_results["info"]["warm_started"] = True
    load.powers = load.powers + Q_(1 + 1j, "VA")
    assert small_network._valid
    assert not small_network._results_valid
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        good_json_results["info"]["iterations"] = small_network.solve_load_flow(warm_start=True)
    compare_results(good_json_results, small_network.results_to_dict())
    assert not propagate_potentials_called
    assert not reset_inputs_called

    # Fifth case: network is not valid -> no warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    good_json_results["info"]["warm_start"] = True
    good_json_results["info"]["warm_started"] = False
    new_load = PowerLoad("new_load", load_bus, powers=[100, 200, 300], phases=load.phases)
    new_load_result = good_json_results["loads"][0].copy()
    new_load_result["id"] = "new_load"
    good_json_results["loads"].append(new_load_result)
    assert new_load.network is small_network
    assert not small_network._valid
    assert not small_network._results_valid
    with warnings.catch_warnings():
        # We could warn here that the user requested warm start but the network is not valid
        # but this will be disruptive for the user especially that warm start is the default
        warnings.simplefilter("error")  # Make sure there is no warning
        assert not small_network._valid
        assert not small_network._results_valid
        good_json_results["info"]["iterations"] = small_network.solve_load_flow(warm_start=True)
    compare_results(good_json_results, small_network.results_to_dict())
    assert propagate_potentials_called
    assert not reset_inputs_called


def test_short_circuits():
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    bus = Bus("bus", phases="abcn")
    bus.add_short_circuit("a", "n")
    _ = VoltageSource(id="vs", bus=bus, voltages=voltages)
    _ = PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(initial_bus=bus)
    df = pd.DataFrame.from_records(
        data=[("bus", "abcn", "an", None)],
        columns=["bus_id", "phases", "short_circuit", "ground"],
    )
    assert_frame_equal(en.short_circuits_frame, df)

    assert bus.short_circuits


def test_catalogue_data():
    # The catalogue data path exists
    catalogue_path = ElectricalNetwork.catalogue_path()
    assert catalogue_path.exists()

    # Read it and copy it
    catalogue_data = ElectricalNetwork.catalogue_data().copy()

    # Iterate over the folder and ensure that the elements are in the catalogue data
    error_message = (
        "Something changed in the network catalogue. Please regenerate the Catalogue.json file for the "
        "network catalogues by using the python file `scripts/generate_network_catalogue_data.py`."
    )
    for p in catalogue_path.glob("*.json"):
        if p.stem == "Catalogue":
            continue

        # Check that the network exists in the catalogue data
        network_name, load_point_name = p.stem.split("_")
        assert network_name in catalogue_data, error_message

        # Check the counts
        en = ElectricalNetwork.from_json(p)
        c_data = catalogue_data[network_name]
        assert len(c_data) == 7
        assert c_data["nb_buses"] == len(en.buses)
        assert c_data["nb_branches"] == len(en.branches)
        assert c_data["nb_loads"] == len(en.loads)
        assert c_data["nb_sources"] == len(en.sources)
        assert c_data["nb_grounds"] == len(en.grounds)
        assert c_data["nb_potential_refs"] == len(en.potential_refs)

        # Check the load point
        remaining_load_points: list[str] = c_data["load_points"]
        assert load_point_name in remaining_load_points, error_message
        remaining_load_points.remove(load_point_name)
        if not remaining_load_points:
            catalogue_data.pop(network_name)

    # At the end of the process, the copy of the catalogue data should be empty
    assert len(catalogue_data) == 0, error_message


def test_from_catalogue():
    # Unknown network name
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_catalogue(name="unknown", load_point_name="winter")
    assert (
        e.value.args[0]
        == "No network matching the name 'unknown' has been found. Please look at the catalogue using the "
        "`print_catalogue` class method."
    )
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Unknown load point name
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_catalogue(name="MVFeeder004", load_point_name="unknown")
    assert (
        e.value.args[0]
        == "No load point matching the name 'unknown' has been found for the network 'MVFeeder004'. Available "
        "load points are 'Summer', 'Winter'."
    )
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Several network name matched
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_catalogue(name="MVFeeder", load_point_name="winter")
    assert e.value.args[0] == (
        "Several networks matching the name 'MVFeeder' have been found: 'MVFeeder004', "
        "'MVFeeder011', 'MVFeeder015', 'MVFeeder032', 'MVFeeder041', 'MVFeeder063', 'MVFeeder078', 'MVFeeder115', "
        "'MVFeeder128', 'MVFeeder151', 'MVFeeder159', 'MVFeeder176', 'MVFeeder210', 'MVFeeder217', 'MVFeeder232',"
        " 'MVFeeder251', 'MVFeeder290', 'MVFeeder312', 'MVFeeder320', 'MVFeeder339'."
    )
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND

    # Several load point name matched
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_catalogue(name="MVFeeder004", load_point_name=r".*")
    assert e.value.args[0] == (
        "Several load points matching the name '.*' have been found for the network 'MVFeeder004': 'Summer', 'Winter'."
    )
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND

    # Both known
    ElectricalNetwork.from_catalogue(name="MVFeeder004", load_point_name="winter")


def test_print_catalogue():
    # Print the entire catalogue
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue()
    assert len(capture.get().split("\n")) == 46

    # Filter on the network name
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(name="MV")
    assert len(capture.get().split("\n")) == 26
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(name=re.compile(r"^MV"))
    assert len(capture.get().split("\n")) == 26

    # Filter on the load point name
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(load_point_name="winter")
    assert len(capture.get().split("\n")) == 46
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(load_point_name=re.compile(r"^Winter"))
    assert len(capture.get().split("\n")) == 46

    # Filter on both
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(name="MV", load_point_name="winter")
    assert len(capture.get().split("\n")) == 26
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(name="MV", load_point_name=re.compile(r"^Winter"))
    assert len(capture.get().split("\n")) == 26
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(name=re.compile(r"^MV"), load_point_name="winter")
    assert len(capture.get().split("\n")) == 26
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(name=re.compile(r"^MV"), load_point_name=re.compile(r"^Winter"))
    assert len(capture.get().split("\n")) == 26

    # Regexp error
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(name=r"^MV[0-")
    assert len(capture.get().split("\n")) == 2
    with console.capture() as capture:
        ElectricalNetwork.print_catalogue(load_point_name=r"^winter[0-]")
    assert len(capture.get().split("\n")) == 2


def test_to_graph(small_network: ElectricalNetwork):
    g = small_network.to_graph()
    assert isinstance(g, nx.Graph)
    assert sorted(g.nodes) == sorted(small_network.buses)
    assert sorted(g.edges) == sorted((b.bus1.id, b.bus2.id) for b in small_network.branches.values())

    for bus in small_network.buses.values():
        node_data = g.nodes[bus.id]
        assert node_data["geom"] == bus.geometry

    for branch in small_network.branches.values():
        edge_data = g.edges[branch.bus1.id, branch.bus2.id]
        assert edge_data == {"id": branch.id, "type": branch.branch_type, "geom": branch.geometry}
