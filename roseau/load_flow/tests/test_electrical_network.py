import contextlib
import itertools as it
import json
import re
import warnings
from contextlib import contextmanager

import geopandas as gpd
import networkx as nx
import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    CurrentLoad,
    FlexibleParameter,
    Ground,
    ImpedanceLoad,
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
from roseau.load_flow.utils import LoadTypeDtype, PhaseDtype, VoltagePhaseDtype

# The following networks are generated using the scripts/generate_test_networks.py script


@pytest.fixture
def all_element_network(test_networks_path) -> ElectricalNetwork:
    # Load the network from the JSON file (without results)
    return ElectricalNetwork.from_json(path=test_networks_path / "all_element_network.json", include_results=False)


@pytest.fixture
def all_element_network_with_results(test_networks_path) -> ElectricalNetwork:
    # Load the network from the JSON file (with results, no need to invoke the solver)
    return ElectricalNetwork.from_json(path=test_networks_path / "all_element_network.json", include_results=True)


@pytest.fixture
def small_network(test_networks_path) -> ElectricalNetwork:
    # Load the network from the JSON file (without results)
    return ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=False)


@pytest.fixture
def small_network_with_results(test_networks_path) -> ElectricalNetwork:
    # Load the network from the JSON file (with results, no need to invoke the solver)
    return ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=True)


@pytest.fixture
def single_phase_network(test_networks_path) -> ElectricalNetwork:
    return ElectricalNetwork.from_json(path=test_networks_path / "single_phase_network.json", include_results=True)


@contextmanager
def check_result_warning(expected_message: str | re.Pattern[str]):
    with warnings.catch_warnings(record=True) as records:
        yield
    assert len(records) == 1
    assert re.match(expected_message, records[0].message.args[0])
    assert records[0].category is UserWarning


def test_connect_and_disconnect():
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    vs = VoltageSource(id="vs", phases="abcn", bus=source_bus, voltages=vn)
    load = PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    lp = LineParameters(id="test", z_line=np.eye(4, dtype=complex))
    line = Line(id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)
    PotentialRef(id="pref", element=ground)
    en = ElectricalNetwork.from_element(source_bus)

    # Connection of a new connected component
    load_bus2 = Bus(id="load_bus2", phases="abcn")
    ground2 = Ground("ground2")
    ground2.connect(bus=load_bus2)
    tp = TransformerParameters.from_catalogue(name="SE Minera A0Ak 50kVA 15/20kV(20) 410V Yzn11")
    Transformer(id="transfo", bus1=load_bus, bus2=load_bus2, parameters=tp)
    with pytest.raises(RoseauLoadFlowException) as e:
        en._check_validity(constructed=False)
    assert "does not have a potential reference" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE
    PotentialRef(id="pref2", element=ground2)  # Add potential ref
    en._check_validity(constructed=False)

    # Disconnection of a load
    assert load.network == en
    load.disconnect()
    assert load.network is None
    assert load.bus is None
    with pytest.raises(RoseauLoadFlowException) as e:
        load.to_dict()
    assert e.value.msg == "The load 'power load' is disconnected and cannot be used anymore."
    assert e.value.code == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT
    new_load = PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    assert new_load.network == en

    # Disconnection of a source
    assert vs.network == en
    vs.disconnect()
    assert vs.network is None
    assert vs.bus is None
    with pytest.raises(RoseauLoadFlowException) as e:
        vs.to_dict()
    assert e.value.msg == "The voltage source 'vs' is disconnected and cannot be used anymore."
    assert e.value.code == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT

    # Bad key
    with pytest.raises(RoseauLoadFlowException) as e:
        en._disconnect_element(Ground("a separate ground element"))
    assert e.value.msg == "Ground(id='a separate ground element') is not a valid load or source."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Adding unknown element
    with pytest.raises(RoseauLoadFlowException) as e:
        en._connect_element(3)
    assert "Unknown element" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Remove line => impossible
    with pytest.raises(RoseauLoadFlowException) as e:
        en._disconnect_element(line)
    assert e.value.msg == (
        "<Line: id='line', bus1='source', bus2='load bus', phases1='abcn', phases2='abcn', length=10.0, "
        "max_loading=1.0> is a Line and it cannot be disconnected from a network."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT


def test_recursive_connect_disconnect():
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    VoltageSource(id="vs", phases="abcn", bus=source_bus, voltages=vn)
    load = PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    lp = LineParameters(id="test", z_line=np.eye(4, dtype=complex))
    line = Line(id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)
    PotentialRef(id="pref", element=ground)
    en = ElectricalNetwork.from_element(source_bus)

    # Create new elements (without connecting them to the existing network)
    ground = en.grounds["ground"]
    new_bus2 = Bus(id="new_bus2", phases="abcn")
    new_load2 = PowerLoad(id="new_load2", bus=new_bus2, phases="abcn", powers=Q_([100, 0, 0], "VA"))
    new_bus = Bus(id="new_bus", phases="abcn")
    new_load = PowerLoad(id="new_load", bus=new_bus, phases="abcn", powers=Q_([100, 0, 0], "VA"))
    lp = LineParameters(id="U_AL_240_without_shunt", z_line=Q_(0.1 * np.eye(4), "ohm/km"), y_shunt=None)
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
    assert new_line2.id not in en.lines
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
    assert new_line.id in en.lines
    assert new_load.network == en
    assert new_load._connected_elements == [new_bus]
    assert new_load.id in en.loads
    assert new_bus2.network == en
    assert new_bus2._connected_elements == [new_load2, new_line2]
    assert new_bus2.id in en.buses
    assert new_line2.network == en
    assert new_line2._connected_elements == [new_bus2, new_bus]
    assert new_line2.id in en.lines
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
    assert new_line.id in en.lines
    assert new_load.network is None
    assert new_load._connected_elements == []
    assert new_load.id not in en.loads
    assert new_bus2.network == en
    assert new_bus2._connected_elements == [new_load2, new_line2]
    assert new_bus2.id in en.buses
    assert new_line2.network == en
    assert new_line2._connected_elements == [new_bus2, new_bus]
    assert new_line2.id in en.lines
    assert new_load2.network == en
    assert new_load2._connected_elements == [new_bus2]
    assert new_load2.id in en.loads


def test_recursive_connect_disconnect_ground():
    #
    # The same but with a "ground connection" from a line with shunt
    #
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    VoltageSource(id="vs", phases="abcn", bus=source_bus, voltages=vn)
    PowerLoad(id="power load", phases="abcn", bus=load_bus, powers=[100 + 0j, 100 + 0j, 100 + 0j])
    lp = LineParameters(id="test", z_line=np.eye(4, dtype=complex))
    Line(id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)
    PotentialRef(id="pref", element=ground)
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
        id="U_AL_240_with_shunt", z_line=Q_(0.1 * np.eye(4), "ohm/km"), y_shunt=Q_(0.1 * np.eye(4), "S/km")
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
    assert new_line2.id in en.lines
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
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    ground.connect(bus2)
    lp = LineParameters(id="test", z_line=np.eye(3, dtype=complex))
    line = Line(id="line", bus1=bus1, bus2=bus2, phases="abc", parameters=lp, length=10)
    p_ref = PotentialRef(id="pref1", element=ground)
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
    bus0 = Bus(id="bus0", phases="abcn")
    ground.connect(bus0)
    voltages = [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j]
    vs = VoltageSource(id="vs", bus=bus0, phases="abcn", voltages=voltages)
    switch = Switch(id="switch", bus1=bus0, bus2=bus1, phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork(
            buses=[bus0, bus1],  # no bus2
            lines=[line],
            transformers=[],
            switches=[switch],
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
    bus3 = Bus(id="bus3", phases="abcn")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="t", vg="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    t = Transformer(id="transfo", bus1=bus2, bus2=bus3, parameters=tp)
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
    p_ref2 = PotentialRef(id="pref2", element=bus3)
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
    src_bus = Bus(id="sb", phases="abcn")
    load_bus = Bus(id="lb", phases="abcn")
    ground = Ground(id="g")
    pref = PotentialRef(id="pr", element=ground)
    ground.connect(src_bus)
    lp = LineParameters(id="test", z_line=np.eye(4, dtype=complex))
    line = Line(id="ln", bus1=src_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)
    vs = VoltageSource(id="vs", bus=src_bus, phases="abcn", voltages=[230, 120 + 150j, 120 - 150j])
    load = PowerLoad(id="pl", bus=load_bus, phases="abcn", powers=[1000, 500, 1000])
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork(
            buses={"foo": src_bus, "lb": load_bus},  # <-- ID of src_bus is wrong
            lines={"ln": line},
            transformers={},
            switches={},
            loads={"pl": load},
            sources={"vs": vs},
            grounds={"g": ground},
            potential_refs={"pr": pref},
        )
    assert e.value.msg == "Bus ID 'sb' does not match its key in the dictionary 'foo'."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BUS_ID


def test_poorly_connected_elements():
    bus1 = Bus(id="b1", phases="abc")
    bus2 = Bus(id="b2", phases="abc")
    bus3 = Bus(id="b3", phases="abc")
    bus4 = Bus(id="b4", phases="abc")
    lp = LineParameters.from_catalogue(name="U_AL_150")
    ground = Ground(id="g1")
    Line(id="l1", bus1=bus1, bus2=bus2, parameters=lp, phases="abc", length=1, ground=ground)
    Line(id="l2", bus1=bus3, bus2=bus4, parameters=lp, phases="abc", length=1, ground=ground)
    VoltageSource(id="vs1", bus=bus1, voltages=20e3)
    PotentialRef(id="pr1", element=ground)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(initial_bus=bus1)
    assert (
        e.value.msg
        == "The elements [\"Bus('b4'), Bus('b3'), Line('l2')\"] are not electrically connected to a voltage source."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.POORLY_CONNECTED_ELEMENT


def test_invalid_element_overrides():
    bus1 = Bus(id="bus1", phases="an")
    bus2 = Bus(id="bus2", phases="an")
    PotentialRef(id="pr", element=bus1)
    lp = LineParameters(id="lp", z_line=np.eye(2, dtype=complex))
    Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=1)
    VoltageSource(id="source", bus=bus1, voltages=[230])
    old_load = PowerLoad(id="load", bus=bus2, powers=[1000])
    ElectricalNetwork.from_element(bus1)

    # Case of a different load type on a different bus
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad(id="load", bus=bus1, currents=[1])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == (
        "A load of ID 'load' is already connected to the network. Disconnect the old load first "
        "if you meant to replace it."
    )

    # Disconnect the old element first: OK
    old_load.disconnect()
    ImpedanceLoad(id="load", bus=bus1, impedances=[500])

    # Case of a source (also suggests disconnecting first)
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource(id="source", bus=bus2, voltages=[230])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == (
        "A source of ID 'source' is already connected to the network. Disconnect the old source first "
        "if you meant to replace it."
    )


def test_frame(small_network: ElectricalNetwork):
    # Buses
    buses_gdf = small_network.buses_frame
    assert isinstance(buses_gdf, gpd.GeoDataFrame)
    assert buses_gdf.shape == (2, 5)
    assert buses_gdf.columns.tolist() == [
        "phases",
        "nominal_voltage",
        "min_voltage_level",
        "max_voltage_level",
        "geometry",
    ]
    assert buses_gdf.index.name == "id"

    # Lines
    lines_gdf = small_network.lines_frame
    assert isinstance(lines_gdf, gpd.GeoDataFrame)
    assert lines_gdf.shape == (1, 7)
    assert lines_gdf.columns.tolist() == [
        "phases",
        "bus1_id",
        "bus2_id",
        "parameters_id",
        "length",
        "max_loading",
        "geometry",
    ]

    # Transformers
    transformers_gdf = small_network.transformers_frame
    assert isinstance(transformers_gdf, gpd.GeoDataFrame)
    assert transformers_gdf.shape == (0, 7)
    assert transformers_gdf.columns.tolist() == [
        "phases1",
        "phases2",
        "bus1_id",
        "bus2_id",
        "parameters_id",
        "max_loading",
        "geometry",
    ]
    assert transformers_gdf.index.name == "id"

    # Switches
    switches_gdf = small_network.switches_frame
    assert isinstance(switches_gdf, gpd.GeoDataFrame)
    assert switches_gdf.shape == (0, 4)
    assert switches_gdf.columns.tolist() == ["phases", "bus1_id", "bus2_id", "geometry"]

    # Loads
    loads_df = small_network.loads_frame
    assert isinstance(loads_df, pd.DataFrame)
    assert loads_df.shape == (1, 4)
    assert loads_df.columns.tolist() == ["type", "phases", "bus_id", "flexible"]
    assert loads_df.index.name == "id"

    # Sources
    sources_df = small_network.sources_frame
    assert isinstance(sources_df, pd.DataFrame)
    assert sources_df.shape == (1, 2)
    assert sources_df.columns.tolist() == ["phases", "bus_id"]
    assert sources_df.index.name == "id"


def test_empty_network():
    with pytest.raises(RoseauLoadFlowException) as exc_info:
        ElectricalNetwork(
            buses={},
            lines={},
            transformers={},
            switches={},
            loads={},
            sources={},
            grounds={},
            potential_refs={},
        )
    assert exc_info.value.code == RoseauLoadFlowExceptionCode.EMPTY_NETWORK
    assert exc_info.value.msg == "Cannot create a network without elements."


def test_buses_voltages(small_network_with_results):
    assert isinstance(small_network_with_results, ElectricalNetwork)
    en = small_network_with_results
    # Multiply by sqrt(3) because a neutral exists in the small network
    nominal_voltage = 20_000 * np.sqrt(3)
    en.buses["bus0"].nominal_voltage = nominal_voltage
    en.buses["bus1"].nominal_voltage = nominal_voltage
    en.buses["bus0"].max_voltage_level = 1.05
    en.buses["bus1"].min_voltage_level = 1.0

    voltage_records = [
        {
            "bus_id": "bus0",
            "phase": "an",
            "voltage": 20000.0 + 0.0j,
            "violated": False,
            "voltage_level": 1.0,
            "min_voltage_level": np.nan,
            "max_voltage_level": 1.05,
            "nominal_voltage": nominal_voltage,
        },
        {
            "bus_id": "bus0",
            "phase": "bn",
            "voltage": -10000.0 + -17320.508076j,
            "violated": False,
            "voltage_level": 1.0000000000134766,
            "min_voltage_level": np.nan,
            "max_voltage_level": 1.05,
            "nominal_voltage": nominal_voltage,
        },
        {
            "bus_id": "bus0",
            "phase": "cn",
            "voltage": -10000.0 + 17320.508076j,
            "violated": False,
            "voltage_level": 1.0000000000134766,
            "min_voltage_level": np.nan,
            "max_voltage_level": 1.05,
            "nominal_voltage": nominal_voltage,
        },
        {
            "bus_id": "bus1",
            "phase": "an",
            "voltage": 19999.949999875 + 0.0j,
            "violated": True,
            "voltage_level": 0.99999749999375,
            "min_voltage_level": 1.0,
            "max_voltage_level": np.nan,
            "nominal_voltage": nominal_voltage,
        },
        {
            "bus_id": "bus1",
            "phase": "bn",
            "voltage": -9999.9749999375 + -17320.464774621556j,
            "violated": True,
            "voltage_level": 0.9999975000072265,
            "min_voltage_level": 1.0,
            "max_voltage_level": np.nan,
            "nominal_voltage": nominal_voltage,
        },
        {
            "bus_id": "bus1",
            "phase": "cn",
            "voltage": -9999.9749999375 + 17320.464774621556j,
            "violated": True,
            "voltage_level": 0.9999975000072265,
            "min_voltage_level": 1.0,
            "max_voltage_level": np.nan,
            "nominal_voltage": nominal_voltage,
        },
    ]

    buses_voltages = en.res_buses_voltages
    expected_buses_voltages = (
        pd.DataFrame.from_records(voltage_records)
        .astype(
            {
                "bus_id": str,
                "phase": VoltagePhaseDtype,
                "voltage": complex,
                "voltage_level": float,
                "min_voltage_level": float,
                "max_voltage_level": float,
                "violated": pd.BooleanDtype(),
            }
        )
        .set_index(["bus_id", "phase"])
    )

    assert isinstance(buses_voltages, pd.DataFrame)
    assert buses_voltages.shape == (6, 6)
    assert buses_voltages.index.names == ["bus_id", "phase"]
    assert list(buses_voltages.columns) == [
        "voltage",
        "violated",
        "voltage_level",
        "min_voltage_level",
        "max_voltage_level",
        "nominal_voltage",
    ]
    assert_frame_equal(buses_voltages, expected_buses_voltages, check_exact=False)


def test_to_from_dict_roundtrip(small_network: ElectricalNetwork):
    net_dict = small_network.to_dict()
    new_net = ElectricalNetwork.from_dict(net_dict)
    assert_frame_equal(small_network.buses_frame, new_net.buses_frame)
    assert_frame_equal(small_network.lines_frame, new_net.lines_frame)
    assert_frame_equal(small_network.transformers_frame, new_net.transformers_frame)
    assert_frame_equal(small_network.switches_frame, new_net.switches_frame)
    assert_frame_equal(small_network.loads_frame, new_net.loads_frame)
    assert_frame_equal(small_network.sources_frame, new_net.sources_frame)


def test_single_phase_network(single_phase_network: ElectricalNetwork):
    # Test dict conversion
    # ====================
    net_dict = single_phase_network.to_dict()
    new_net = ElectricalNetwork.from_dict(net_dict)
    assert_frame_equal(single_phase_network.buses_frame, new_net.buses_frame)
    assert_frame_equal(single_phase_network.transformers_frame, new_net.transformers_frame)
    assert_frame_equal(single_phase_network.lines_frame, new_net.lines_frame)
    assert_frame_equal(single_phase_network.switches_frame, new_net.switches_frame)
    assert_frame_equal(single_phase_network.loads_frame, new_net.loads_frame)
    assert_frame_equal(single_phase_network.sources_frame, new_net.sources_frame)

    # Test load flow results
    # ======================
    source_bus = single_phase_network.buses["bus0"]
    load_bus = single_phase_network.buses["bus1"]
    line = single_phase_network.lines["line"]
    load = single_phase_network.loads["load"]

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
    assert_frame_equal(
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
    assert_frame_equal(
        single_phase_network.res_buses_voltages,
        pd.DataFrame.from_records(
            [
                {
                    "bus_id": "bus0",
                    "phase": "bn",
                    "voltage": (19999.94999975 + 0j) - (-0.050000250001249996 + 0j),
                    "violated": None,
                    "voltage_level": np.nan,
                    "min_voltage_level": np.nan,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": np.nan,
                },
                {
                    "bus_id": "bus1",
                    "phase": "bn",
                    "voltage": (19999.899999499998 + 0j) - (0j),
                    "violated": None,
                    "voltage_level": np.nan,
                    "min_voltage_level": np.nan,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": np.nan,
                },
            ]
        )
        .astype(
            {
                "phase": VoltagePhaseDtype,
                "voltage": complex,
                "voltage_level": float,
                "min_voltage_level": float,
                "max_voltage_level": float,
                "violated": pd.BooleanDtype(),
                "nominal_voltage": float,
            }
        )
        .set_index(["bus_id", "phase"]),
    )

    # Transformers results
    assert_frame_equal(
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
                "violated",
                "loading",
                "max_loading",
                "sn",
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
                "violated": pd.BooleanDtype(),
                "loading": float,
                "max_loading": float,
                "sn": float,
            }
        )
        .set_index(["transformer_id", "phase"]),
    )
    # Lines results
    assert_frame_equal(
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
                    "violated": None,
                    "loading": np.nan,
                    "max_loading": 1.0,
                    "ampacity": np.nan,
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
                    "violated": None,
                    "loading": np.nan,
                    "max_loading": 1.0,
                    "ampacity": np.nan,
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
                "violated": pd.BooleanDtype(),
                "loading": float,
                "max_loading": float,
                "ampacity": float,
            }
        )
        .set_index(["line_id", "phase"]),
        check_exact=False,
    )
    # Switches results
    assert_frame_equal(
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
    assert_frame_equal(
        single_phase_network.res_loads,
        pd.DataFrame.from_records(
            [
                {
                    "load_id": "load",
                    "phase": "b",
                    "type": "power",
                    "current": 0.005000025000250002 - 0j,
                    "power": (19999.899999499998 + 0j) * (0.005000025000250002 - 0j).conjugate(),
                    "potential": 19999.899999499998 + 0j,
                },
                {
                    "load_id": "load",
                    "phase": "n",
                    "type": "power",
                    "current": -0.005000025000250002 - 0j,
                    "power": (0j) * (-0.005000025000250002 - 0j).conjugate(),
                    "potential": 0j,
                },
            ]
        )
        .astype(
            {"phase": PhaseDtype, "type": LoadTypeDtype, "current": complex, "power": complex, "potential": complex}
        )
        .set_index(["load_id", "phase"]),
    )

    # Buses voltage_level is computed when nominal_voltage is defined, even if missing min/max levels
    source_bus.nominal_voltage = 20_000 * np.sqrt(3)
    assert source_bus.min_voltage_level is None
    assert source_bus.max_voltage_level is None
    npt.assert_allclose(single_phase_network.res_buses_voltages.loc[("bus0", np.s_[:]), "voltage_level"], 1.0)
    assert single_phase_network.res_buses_voltages.loc[("bus1", np.s_[:]), "voltage_level"].isna().all()


def test_network_elements(small_network: ElectricalNetwork):
    # Add a line to the network ("bus2" constructor belongs to the network)
    bus1 = small_network.buses["bus1"]
    bus2 = Bus(id="bus2", phases="abcn")
    assert bus2.network is None
    lp = LineParameters(id="test", z_line=10 * np.eye(4, dtype=complex))
    l2 = Line(id="line2", bus1=bus2, bus2=bus1, parameters=lp, length=Q_(0.3, "km"))
    assert l2.network == small_network
    assert bus2.network == small_network

    # Add a switch ("bus1" constructor belongs to the network)
    bus3 = Bus(id="bus3", phases="abcn")
    assert bus3.network is None
    s = Switch(id="switch", bus1=bus2, bus2=bus3)
    assert s.network == small_network
    assert bus3.network == small_network

    # Create a second network
    bus_vs = Bus(id="bus_vs", phases="abcn")
    VoltageSource(id="vs2", bus=bus_vs, voltages=15e3)
    ground = Ground(id="ground2")
    ground.connect(bus=bus_vs, phase="a")
    PotentialRef(id="pref2", element=ground)
    small_network_2 = ElectricalNetwork.from_element(initial_bus=bus_vs)

    # Connect the two networks
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch2", bus1=bus2, bus2=bus_vs)
    assert e.value.msg == "The Bus 'bus_vs' is already assigned to another network."
    assert e.value.code == RoseauLoadFlowExceptionCode.SEVERAL_NETWORKS

    # Every object have their good network after this failure
    for element in it.chain(
        small_network.buses.values(),
        small_network.lines.values(),
        small_network.transformers.values(),
        small_network.switches.values(),
        small_network.loads.values(),
        small_network.grounds.values(),
        small_network.potential_refs.values(),
    ):
        assert element.network == small_network
    for element in it.chain(
        small_network_2.buses.values(),
        small_network_2.lines.values(),
        small_network_2.transformers.values(),
        small_network_2.switches.values(),
        small_network_2.loads.values(),
        small_network_2.grounds.values(),
        small_network_2.potential_refs.values(),
    ):
        assert element.network == small_network_2


def test_network_results_warning(small_network, small_network_with_results, recwarn):  # noqa: C901
    en = small_network
    # network well-defined using the constructor
    for bus in en.buses.values():
        assert bus.network == en
    for load in en.loads.values():
        assert load.network == en
    for source in en.sources.values():
        assert source.network == en
    for line in en.lines.values():
        assert line.network == en
    for transformer in en.transformers.values():
        assert transformer.network == en
    for switch in en.switches.values():
        assert switch.network == en
    for ground in en.grounds.values():
        assert ground.network == en
    for p_ref in en.potential_refs.values():
        assert p_ref.network == en

    # All the results function raises an exception
    result_field_names_dict = {
        "buses": ("res_potentials", "res_voltages", "res_violated"),
        "lines": (
            "res_currents",
            "res_violated",
            "res_voltages",
            "res_power_losses",
            "res_potentials",
            "res_powers",
            "res_series_currents",
            "res_series_power_losses",
            "res_shunt_currents",
            "res_shunt_power_losses",
        ),
        "transformers": (
            "res_currents",
            "res_powers",
            "res_potentials",
            "res_power_losses",
            "res_violated",
            "res_voltages",
        ),
        "switches": ("res_currents", "res_potentials", "res_powers", "res_voltages"),
        "loads": ("res_currents", "res_powers", "res_potentials", "res_voltages"),
        "sources": ("res_currents", "res_potentials", "res_powers"),
    }
    for bus in en.buses.values():
        for result_field_name in result_field_names_dict["buses"]:
            if result_field_name == "res_violated" and bus.min_voltage is None and bus.max_voltage is None:
                continue  # No min or max voltages so no call to results
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = getattr(bus, result_field_name)
            assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for line in en.lines.values():
        for result_field_name in result_field_names_dict["lines"]:
            if result_field_name == "res_violated":
                continue  # No ampacities
            if not line.with_shunt and "shunt" in result_field_name:
                continue  # No results if no shunt
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = getattr(line, result_field_name)
            assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for transformer in en.transformers.values():
        for result_field_name in result_field_names_dict["transformers"]:
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = getattr(transformer, result_field_name)
            assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for switch in en.switches.values():
        for result_field_name in result_field_names_dict["switches"]:
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = getattr(switch, result_field_name)
            assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for load in en.loads.values():
        for result_field_name in result_field_names_dict["loads"]:
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = getattr(load, result_field_name)
            assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
        if load.is_flexible and isinstance(load, PowerLoad):
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = load.res_flexible_powers
            assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for source in en.sources.values():
        for result_field_name in result_field_names_dict["sources"]:
            with pytest.raises(RoseauLoadFlowException) as e:
                _ = getattr(source, result_field_name)
            assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for ground in en.grounds.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = ground.res_potential
        assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
    for p_ref in en.potential_refs.values():
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = p_ref.res_current
        assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN

    # Network with results
    en = small_network_with_results

    # No warning when getting results (they are up-to-date)
    recwarn.clear()
    for bus in en.buses.values():
        for result_field_name in result_field_names_dict["buses"]:
            if result_field_name == "res_violated" and bus.min_voltage is None and bus.max_voltage is None:
                continue  # No min or max voltages so no call to results
            _ = getattr(bus, result_field_name)
    for line in en.lines.values():
        for result_field_name in result_field_names_dict["lines"]:
            if result_field_name == "res_violated":
                continue  # No ampacities
            if not line.with_shunt and "shunt" in result_field_name:
                continue  # No results if no shunt
            _ = getattr(line, result_field_name)
    for transformer in en.transformers.values():
        for result_field_name in result_field_names_dict["transformers"]:
            _ = getattr(transformer, result_field_name)
    for switch in en.switches.values():
        for result_field_name in result_field_names_dict["switches"]:
            _ = getattr(switch, result_field_name)
    for load in en.loads.values():
        for result_field_name in result_field_names_dict["loads"]:
            _ = getattr(load, result_field_name)
        if load.is_flexible and isinstance(load, PowerLoad):
            _ = load.res_flexible_powers
    for source in en.sources.values():
        for result_field_name in result_field_names_dict["sources"]:
            _ = getattr(source, result_field_name)
    for ground in en.grounds.values():
        _ = ground.res_potential
    for p_ref in en.potential_refs.values():
        _ = p_ref.res_current
    assert len(recwarn) == 0

    # Modify something
    load = en.loads["load"]
    load.powers = [200, 200, 200]  # VA

    # Ensure that a warning is raised no matter which result is requested
    expected_message = (
        r"The results of \w+ '\w+' may be outdated. Please re-run a load flow to ensure the validity of results."
    )
    for bus in en.buses.values():
        for result_field_name in result_field_names_dict["buses"]:
            if result_field_name == "res_violated" and bus.min_voltage is None and bus.max_voltage is None:
                continue  # No min or max voltages so no call to results
            with check_result_warning(expected_message=expected_message):
                _ = getattr(bus, result_field_name)
    for line in en.lines.values():
        for result_field_name in result_field_names_dict["lines"]:
            if result_field_name == "res_violated":
                continue  # No ampacities
            if not line.with_shunt and "shunt" in result_field_name:
                continue  # No results if no shunt
            with check_result_warning(expected_message=expected_message):
                _ = getattr(line, result_field_name)
    for transformer in en.transformers.values():
        for result_field_name in result_field_names_dict["transformers"]:
            with check_result_warning(expected_message=expected_message):
                _ = getattr(transformer, result_field_name)
    for switch in en.switches.values():
        for result_field_name in result_field_names_dict["switches"]:
            with check_result_warning(expected_message=expected_message):
                _ = getattr(switch, result_field_name)
    for load in en.loads.values():
        for result_field_name in result_field_names_dict["loads"]:
            with check_result_warning(expected_message=expected_message):
                _ = getattr(load, result_field_name)
        if load.is_flexible and isinstance(load, PowerLoad):
            with check_result_warning(expected_message=expected_message):
                _ = load.res_flexible_powers
    for source in en.sources.values():
        for result_field_name in result_field_names_dict["sources"]:
            with check_result_warning(expected_message=expected_message):
                _ = getattr(source, result_field_name)
    for ground in en.grounds.values():
        with check_result_warning(expected_message=expected_message):
            _ = ground.res_potential
    for p_ref in en.potential_refs.values():
        with check_result_warning(expected_message=expected_message):
            _ = p_ref.res_current

    # Ensure that a single warning is raised when having a data frame result
    expected_message = (
        "The results of this network may be outdated. Please re-run a load flow to ensure the validity of results."
    )
    with check_result_warning(expected_message=expected_message):
        _ = en.res_buses
    with check_result_warning(expected_message=expected_message):
        _ = en.res_buses_voltages
    with check_result_warning(expected_message=expected_message):
        _ = en.res_lines
    with check_result_warning(expected_message=expected_message):
        _ = en.res_transformers
    with check_result_warning(expected_message=expected_message):
        _ = en.res_switches
    with check_result_warning(expected_message=expected_message):
        _ = en.res_loads
    with check_result_warning(expected_message=expected_message):
        _ = en.res_sources
    with check_result_warning(expected_message=expected_message):
        _ = en.res_loads_flexible_powers


def test_network_results_error(small_network):
    en = small_network

    # Test all results
    for attr_name in dir(en):
        if not attr_name.startswith("res_"):
            continue
        with pytest.raises(RoseauLoadFlowException) as e:
            getattr(en, attr_name)
        assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN
        assert e.value.msg == "The load flow results are not available because the load flow has not been run yet."


def test_load_flow_results_frames(small_network_with_results):
    en = small_network_with_results
    # Multiply by sqrt(3) because a neutral exists in the small network
    nominal_voltage = 20_000 * np.sqrt(3)
    en.buses["bus0"].nominal_voltage = nominal_voltage
    en.buses["bus0"].min_voltage_level = 1.05

    # Buses results
    expected_res_buses = (
        pd.DataFrame.from_records(
            [
                {"bus_id": "bus0", "phase": "a", "potential": 20000 + 2.89120338e-18j},
                {"bus_id": "bus0", "phase": "b", "potential": -10000.000000 - 17320.508076j},
                {"bus_id": "bus0", "phase": "c", "potential": -10000.000000 + 17320.508076j},
                {"bus_id": "bus0", "phase": "n", "potential": -1.347648e-12 + 2.891203e-18j},
                {"bus_id": "bus1", "phase": "a", "potential": 19999.949999875 + 2.891196e-18j},
                {"bus_id": "bus1", "phase": "b", "potential": -9999.97499993 - 17320.4647746j},
                {"bus_id": "bus1", "phase": "c", "potential": -9999.97499993 + 17320.4647746j},
                {"bus_id": "bus1", "phase": "n", "potential": 0j},
            ]
        )
        .astype({"bus_id": object, "phase": PhaseDtype, "potential": complex})
        .set_index(["bus_id", "phase"])
    )
    assert_frame_equal(en.res_buses, expected_res_buses, rtol=1e-5)

    # Buses voltages results
    expected_res_buses_voltages = (
        pd.DataFrame.from_records(
            [
                {
                    "bus_id": "bus0",
                    "phase": "an",
                    "voltage": (20000 + 2.89120e-18j) - (-1.34764e-12 + 2.89120e-18j),
                    "violated": True,
                    "voltage_level": 1.0,
                    "min_voltage_level": 1.05,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": nominal_voltage,
                },
                {
                    "bus_id": "bus0",
                    "phase": "bn",
                    "voltage": (-10000.00000 - 17320.50807j) - (-1.34764e-12 + 2.89120e-18j),
                    "violated": True,
                    "voltage_level": 1.0000000000134766,
                    "min_voltage_level": 1.05,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": nominal_voltage,
                },
                {
                    "bus_id": "bus0",
                    "phase": "cn",
                    "voltage": (-10000.00000 + 17320.50807j) - (-1.34764e-12 + 2.89120e-18j),
                    "violated": True,
                    "voltage_level": 1.0000000000134766,
                    "min_voltage_level": 1.05,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": nominal_voltage,
                },
                {
                    "bus_id": "bus1",
                    "phase": "an",
                    "voltage": (19999.94999 + 2.89119e-18j) - (0j),
                    "violated": None,
                    "voltage_level": np.nan,
                    "min_voltage_level": np.nan,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": np.nan,
                },
                {
                    "bus_id": "bus1",
                    "phase": "bn",
                    "voltage": (-9999.97499 - 17320.46477j) - (0j),
                    "violated": None,
                    "voltage_level": np.nan,
                    "min_voltage_level": np.nan,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": np.nan,
                },
                {
                    "bus_id": "bus1",
                    "phase": "cn",
                    "voltage": (-9999.97499 + 17320.46477j) - (0j),
                    "violated": None,
                    "voltage_level": np.nan,
                    "min_voltage_level": np.nan,
                    "max_voltage_level": np.nan,
                    "nominal_voltage": np.nan,
                },
            ]
        )
        .astype(
            {
                "bus_id": object,
                "phase": VoltagePhaseDtype,
                "voltage": complex,
                "violated": pd.BooleanDtype(),
                "voltage_level": float,
                "min_voltage_level": float,
                "max_voltage_level": float,
                "nominal_voltage": float,
            }
        )
        .set_index(["bus_id", "phase"])
    )
    assert_frame_equal(en.res_buses_voltages, expected_res_buses_voltages, rtol=1e-5)

    # Transformers results
    expected_res_transformers = (
        pd.DataFrame.from_records(
            data=[],
            columns=[
                "transformer_id",
                "phase",
                "current1",
                "current2",
                "power1",
                "power2",
                "potential1",
                "potential2",
                "violated",
                "loading",
                "max_loading",
                "sn",
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
                "loading": float,
                "violated": pd.BooleanDtype(),
                "max_loading": float,
                "sn": float,
            }
        )
        .set_index(["transformer_id", "phase"])
    )
    assert_frame_equal(en.res_transformers, expected_res_transformers)

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
            "violated": None,
            "loading": np.nan,
            "max_loading": 1.0,
            "ampacity": np.nan,
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
            "violated": None,
            "loading": np.nan,
            "max_loading": 1.0,
            "ampacity": np.nan,
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
            "violated": None,
            "loading": np.nan,
            "max_loading": 1.0,
            "ampacity": np.nan,
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
            "violated": None,
            "loading": np.nan,
            "max_loading": 1.0,
            "ampacity": np.nan,
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
        "violated": pd.BooleanDtype(),
        "loading": float,
        "max_loading": float,
        "ampacity": float,
    }
    expected_res_lines = (
        pd.DataFrame.from_records(expected_res_lines_records)
        .astype(expected_res_lines_dtypes)
        .set_index(["line_id", "phase"])
    )
    assert_frame_equal(en.res_lines, expected_res_lines, rtol=1e-4, atol=1e-5)

    # Lines with violated max current
    en.lines["line"].parameters.ampacities = 0.002
    expected_res_lines_violated_records = []
    for d in expected_res_lines_records:
        if d["phase"] == "n":
            expected_res_lines_violated_records.append(
                d | {"ampacity": 0.002, "violated": False, "loading": 6.738240607860843e-11}
            )
        else:
            expected_res_lines_violated_records.append(
                d | {"ampacity": 0.002, "violated": True, "loading": 2.500006250011211}
            )
    expected_res_violated_lines = (
        pd.DataFrame.from_records(expected_res_lines_violated_records)
        .astype(expected_res_lines_dtypes)
        .set_index(["line_id", "phase"])
    )
    assert_frame_equal(en.res_lines, expected_res_violated_lines, rtol=1e-4, atol=1e-5)

    # Switches results
    expected_res_switches = (
        pd.DataFrame.from_records(
            data=[],
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
    assert_frame_equal(en.res_switches, expected_res_switches)

    # Loads results
    expected_res_loads = (
        pd.DataFrame.from_records(
            [
                {
                    "load_id": "load",
                    "phase": "a",
                    "type": "power",
                    "current": 0.00500 + 7.22802e-25j,
                    "power": (19999.94999 + 2.89119e-18j) * (0.00500 + 7.22802e-25j).conjugate(),
                    "potential": 19999.94999 + 2.89119e-18j,
                },
                {
                    "load_id": "load",
                    "phase": "b",
                    "type": "power",
                    "current": -0.00250 - 0.00433j,
                    "power": (-9999.97499 - 17320.46477j) * (-0.00250 - 0.00433j).conjugate(),
                    "potential": -9999.97499 - 17320.46477j,
                },
                {
                    "load_id": "load",
                    "phase": "c",
                    "type": "power",
                    "current": -0.00250 + 0.00433j,
                    "power": (-9999.97499 + 17320.46477j) * (-0.00250 + 0.00433j).conjugate(),
                    "potential": -9999.97499 + 17320.46477j,
                },
                {
                    "load_id": "load",
                    "phase": "n",
                    "type": "power",
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
                "type": LoadTypeDtype,
                "current": complex,
                "power": complex,
                "potential": complex,
            }
        )
        .set_index(["load_id", "phase"])
    )
    assert_frame_equal(en.res_loads, expected_res_loads, rtol=1e-4)

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
    assert_frame_equal(en.res_sources, expected_res_sources, rtol=1e-4)

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
    assert_frame_equal(en.res_grounds, expected_res_grounds)

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
    assert_frame_equal(en.res_potential_refs, expected_res_potential_refs, check_exact=False)

    # No flexible loads
    assert en.res_loads_flexible_powers.empty

    # Let's add a flexible load
    fp = FlexibleParameter.p_max_u_consumption(u_min=16000, u_down=17000, s_max=1000)
    load = en.loads["load"]
    assert isinstance(load, PowerLoad)
    load._flexible_params = [fp, fp, fp]
    load._res_flexible_powers = 100 * np.ones(3, dtype=np.complex128)
    load._fetch_results = False
    expected_res_flex_powers = (
        pd.DataFrame.from_records(
            [
                {
                    "load_id": "load",
                    "phase": "an",
                    "flexible_power": 99.99999999999994 + 0j,
                },
                {
                    "load_id": "load",
                    "phase": "bn",
                    "flexible_power": 99.99999999999994 + 0j,
                },
                {
                    "load_id": "load",
                    "phase": "cn",
                    "flexible_power": 99.99999999999994 + 0j,
                },
            ]
        )
        .astype({"load_id": object, "phase": VoltagePhaseDtype, "flexible_power": complex})
        .set_index(["load_id", "phase"])
    )
    assert_frame_equal(en.res_loads_flexible_powers, expected_res_flex_powers, rtol=1e-5)


def test_solver_warm_start(small_network: ElectricalNetwork, monkeypatch):
    load: PowerLoad = small_network.loads["load"]
    load_bus = small_network.buses["bus1"]

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
    monkeypatch.setattr(small_network._solver, "solve_load_flow", lambda *_, **__: (1, 1e-20))

    # First case: network is valid, no results yet -> no warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    assert small_network._valid
    assert not small_network._results_valid  # Results are not valid by default
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=True)
    assert not propagate_potentials_called  # Is not called because it was already called in the constructor
    assert not reset_inputs_called

    # Second case: the user requested no warm start (even though the network and results are valid)
    propagate_potentials_called = False
    reset_inputs_called = False
    assert small_network._valid
    assert small_network._results_valid
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=False)
    assert not propagate_potentials_called
    assert reset_inputs_called

    # Third case: network is valid, results are valid -> warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    assert small_network._valid
    assert small_network._results_valid
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=True)
    assert not propagate_potentials_called
    assert not reset_inputs_called

    # Fourth case (load powers changes): network is valid, results are not valid -> warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    load.powers = load.powers + Q_(1 + 1j, "VA")
    assert small_network._valid
    assert not small_network._results_valid
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=True)
    assert not propagate_potentials_called
    assert not reset_inputs_called

    # Fifth case: network is not valid -> no warm start
    propagate_potentials_called = False
    reset_inputs_called = False
    new_load = PowerLoad("new_load", load_bus, powers=[100, 200, 300], phases=load.phases)
    assert new_load.network is small_network
    assert not small_network._valid
    assert not small_network._results_valid
    with warnings.catch_warnings():
        # We could warn here that the user requested warm start but the network is not valid
        # but this will be disruptive for the user especially that warm start is the default
        warnings.simplefilter("error")  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=True)
    assert propagate_potentials_called
    assert not reset_inputs_called


def test_propagate_potentials():
    # Delta source
    source_bus = Bus(id="source_bus", phases="abc")
    _ = VoltageSource(id="source", bus=source_bus, voltages=20e3 * np.array([np.exp(1j * np.pi / 6), -1j, 0.0]))
    _ = PotentialRef(id="pref", element=source_bus)
    load_bus = Bus(id="load_bus", phases="abc")
    _ = Switch(id="switch", bus1=source_bus, bus2=load_bus)

    assert not load_bus._initialized
    assert not source_bus._initialized
    _ = ElectricalNetwork.from_element(source_bus)
    assert load_bus._initialized
    assert source_bus._initialized
    un = 20e3 / np.sqrt(3)
    expected_potentials = un * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3)])
    assert np.allclose(load_bus.potentials.m, expected_potentials)
    assert np.allclose(source_bus.potentials.m, expected_potentials)

    # Multiple sources
    source_bus = Bus(id="source_bus", phases="abcn")
    _ = VoltageSource(id="VSa", bus=source_bus, voltages=[100], phases="an")
    _ = VoltageSource(id="VSbc", bus=source_bus, voltages=[200, 300], phases="bcn")
    _ = PotentialRef(id="pref", element=source_bus)
    load_bus = Bus(id="load_bus", phases="abcn")
    _ = Switch(id="switch", bus1=source_bus, bus2=load_bus)

    assert not load_bus._initialized
    _ = ElectricalNetwork.from_element(source_bus)
    assert load_bus._initialized
    assert np.allclose(load_bus.potentials.m, [100, 200, 300, 0])

    # Do not define a source for all phases
    source_bus = Bus(id="source_bus", phases="abcn")
    _ = VoltageSource(id="VSa", bus=source_bus, voltages=[100], phases="an")
    _ = PotentialRef(id="pref", element=source_bus)
    load_bus = Bus(id="load_bus", phases="abcn")
    _ = Switch(id="switch", bus1=source_bus, bus2=load_bus)

    assert not load_bus._initialized
    _ = ElectricalNetwork.from_element(source_bus)
    assert load_bus._initialized
    assert np.allclose(load_bus.potentials.m, 100 * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3), 0]))


def test_short_circuits():
    vn = 400 / np.sqrt(3)
    bus = Bus(id="bus", phases="abcn")
    bus.add_short_circuit("a", "n")
    _ = VoltageSource(id="vs", bus=bus, voltages=vn)
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
        assert len(c_data) == 9
        assert c_data["nb_buses"] == len(en.buses)
        assert c_data["nb_lines"] == len(en.lines)
        assert c_data["nb_switches"] == len(en.switches)
        assert c_data["nb_transformers"] == len(en.transformers)
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
    assert e.value.msg == (
        "No networks matching the query (name='unknown') have been found. Please look at the "
        "catalogue using the `get_catalogue` class method."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Unknown load point name
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_catalogue(name="MVFeeder004", load_point_name="unknown")
    assert e.value.msg == (
        "No load points for network 'MVFeeder004' matching the query (load_point_name='unknown') have "
        "been found. Please look at the catalogue using the `get_catalogue` class method."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Several network name matched
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_catalogue(name=r"MVFeeder.*", load_point_name="winter")
    assert e.value.msg == (
        "Several networks matching the query (name='MVFeeder.*') have been found: 'MVFeeder004', "
        "'MVFeeder011', 'MVFeeder015', 'MVFeeder032', 'MVFeeder041', 'MVFeeder063', 'MVFeeder078', "
        "'MVFeeder115', 'MVFeeder128', 'MVFeeder151', 'MVFeeder159', 'MVFeeder176', 'MVFeeder210', "
        "'MVFeeder217', 'MVFeeder232', 'MVFeeder251', 'MVFeeder290', 'MVFeeder312', 'MVFeeder320', "
        "'MVFeeder339'."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND

    # Several load point name matched
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_catalogue(name="MVFeeder004", load_point_name=r".*")
    assert e.value.msg == (
        "Several load points for network 'MVFeeder004' matching the query (load_point_name='.*') have "
        "been found: 'Summer', 'Winter'."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND

    # Both known
    ElectricalNetwork.from_catalogue(name="MVFeeder004", load_point_name="winter")


def test_get_catalogue():
    # Get the entire catalogue
    catalogue = ElectricalNetwork.get_catalogue()
    assert catalogue.shape == (40, 9)

    # Filter on the network name
    catalogue = ElectricalNetwork.get_catalogue(name=r"MV.*")
    assert catalogue.shape == (20, 9)
    catalogue = ElectricalNetwork.get_catalogue(name=re.compile(r"^MV.*"))
    assert catalogue.shape == (20, 9)

    # Filter on the load point name
    catalogue = ElectricalNetwork.get_catalogue(load_point_name="winter")
    assert catalogue.shape == (40, 9)
    catalogue = ElectricalNetwork.get_catalogue(load_point_name=re.compile(r"^Winter"))
    assert catalogue.shape == (40, 9)

    # Filter on both
    catalogue = ElectricalNetwork.get_catalogue(name=r"MV.*", load_point_name="winter")
    assert catalogue.shape == (20, 9)
    catalogue = ElectricalNetwork.get_catalogue(name=r"MV.*", load_point_name=re.compile(r"^Winter"))
    assert catalogue.shape == (20, 9)
    catalogue = ElectricalNetwork.get_catalogue(name=re.compile(r"^MV.*"), load_point_name="winter")
    assert catalogue.shape == (20, 9)
    catalogue = ElectricalNetwork.get_catalogue(name=re.compile(r"^MV.*"), load_point_name=re.compile(r"^Winter"))
    assert catalogue.shape == (20, 9)

    # Regexp error
    catalogue = ElectricalNetwork.get_catalogue(name=r"^MV[0-")
    assert catalogue.empty
    catalogue = ElectricalNetwork.get_catalogue(load_point_name=r"^winter[0-]")
    assert catalogue.empty


def test_to_graph(all_element_network: ElectricalNetwork):
    g = all_element_network.to_graph()
    assert isinstance(g, nx.Graph)
    assert sorted(g.nodes) == sorted(all_element_network.buses)
    assert sorted(g.edges) == sorted(
        (b.bus1.id, b.bus2.id)
        for b in it.chain(
            all_element_network.lines.values(),
            all_element_network.transformers.values(),
            all_element_network.switches.values(),
        )
    )

    for bus in all_element_network.buses.values():
        node_data = g.nodes[bus.id]
        assert node_data["geom"] == bus.geometry

    for line in all_element_network.lines.values():
        edge_data = g.edges[line.bus1.id, line.bus2.id]
        ampacities = line.ampacities.magnitude.tolist() if line.ampacities is not None else None
        assert edge_data == {
            "id": line.id,
            "type": "line",
            "phases": line.phases,
            "length": line.length.m,
            "parameters_id": line.parameters.id,
            "ampacities": ampacities,
            "max_loading": line._max_loading,
            "geom": line.geometry,
        }

    for transformer in all_element_network.transformers.values():
        edge_data = g.edges[transformer.bus1.id, transformer.bus2.id]
        max_loading = transformer.max_loading.magnitude if transformer.max_loading is not None else None
        assert edge_data == {
            "id": transformer.id,
            "type": "transformer",
            "phases1": transformer.phases1,
            "phases2": transformer.phases2,
            "parameters_id": transformer.parameters.id,
            "max_loading": max_loading,
            "sn": transformer.sn.magnitude,
            "geom": transformer.geometry,
        }

    for switch in all_element_network.switches.values():
        edge_data = g.edges[switch.bus1.id, switch.bus2.id]
        assert edge_data == {"id": switch.id, "type": "switch", "phases": switch.phases, "geom": switch.geometry}


def test_serialization(all_element_network, all_element_network_with_results):
    def assert_results(en_dict: dict, included: bool):
        for bus_data in en_dict["buses"]:
            assert ("results" in bus_data) == included
        for line_data in en_dict["lines"]:
            assert ("results" in line_data) == included
        for transformer_data in en_dict["transformers"]:
            assert ("results" in transformer_data) == included
        for switch_data in en_dict["switches"]:
            assert ("results" in switch_data) == included
        for source_data in en_dict["sources"]:
            assert ("results" in source_data) == included
        for load_data in en_dict["loads"]:
            assert ("results" in load_data) == included
        for ground_data in en_dict["grounds"]:
            assert ("results" in ground_data) == included
        for p_ref_data in en_dict["potential_refs"]:
            assert ("results" in p_ref_data) == included

    # No results: include_results is ignored
    en = all_element_network
    en_dict_with_results = en.to_dict(include_results=True)
    en_dict_without_results = en.to_dict(include_results=False)
    assert_results(en_dict_with_results, included=False)
    assert_results(en_dict_without_results, included=False)
    assert en_dict_with_results == en_dict_without_results
    new_en = ElectricalNetwork.from_dict(en_dict_without_results)
    assert new_en.to_dict() == en_dict_without_results

    # Has results: include_results is respected
    en = all_element_network_with_results
    en_dict_with_results = en.to_dict(include_results=True)
    en_dict_without_results = en.to_dict(include_results=False)
    assert_results(en_dict_with_results, included=True)
    assert_results(en_dict_without_results, included=False)
    assert en_dict_with_results != en_dict_without_results
    # round tripping
    assert ElectricalNetwork.from_dict(en_dict_with_results).to_dict() == en_dict_with_results
    assert ElectricalNetwork.from_dict(en_dict_without_results).to_dict() == en_dict_without_results
    # default is to include the results
    assert en.to_dict() == en_dict_with_results

    # Has invalid results: cannot include them
    en.loads["load0"].powers += Q_(1, "VA")  # <- invalidate the results
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict(include_results=True)
    assert e.value.msg == (
        "Trying to convert ElectricalNetwork with invalid results to a dict. Either call "
        "`en.solve_load_flow()` before converting or pass `include_results=False`."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_FLOW_RESULT
    en_dict_without_results = en.to_dict(include_results=False)
    # round tripping without the results should still work
    assert ElectricalNetwork.from_dict(en_dict_without_results).to_dict() == en_dict_without_results


def test_results_to_dict(all_element_network_with_results):
    en = all_element_network_with_results

    # By default full=False
    res_network = en.results_to_dict()
    assert set(res_network) == {
        "buses",
        "lines",
        "transformers",
        "switches",
        "loads",
        "sources",
        "grounds",
        "potential_refs",
    }
    for v in res_network.values():
        assert isinstance(v, list)
    for res_bus in res_network["buses"]:
        bus = en.buses[res_bus["id"]]
        assert res_bus["phases"] == bus.phases
        complex_potentials = [v_r + 1j * v_i for v_r, v_i in res_bus["potentials"]]
        np.testing.assert_allclose(complex_potentials, bus.res_potentials.m)
    for res_line in res_network["lines"]:
        line = en.lines[res_line["id"]]
        assert res_line["phases"] == line.phases
        complex_currents1 = [i_r + 1j * i_i for i_r, i_i in res_line["currents1"]]
        np.testing.assert_allclose(complex_currents1, line.res_currents[0].m)
        complex_currents2 = [i_r + 1j * i_i for i_r, i_i in res_line["currents2"]]
        np.testing.assert_allclose(complex_currents2, line.res_currents[1].m)
    for res_transformer in res_network["transformers"]:
        transformer = en.transformers[res_transformer["id"]]
        assert res_transformer["phases1"] == transformer.phases1
        assert res_transformer["phases2"] == transformer.phases2
        complex_currents1 = [i_r + 1j * i_i for i_r, i_i in res_transformer["currents1"]]
        np.testing.assert_allclose(complex_currents1, transformer.res_currents[0].m)
        complex_currents2 = [i_r + 1j * i_i for i_r, i_i in res_transformer["currents2"]]
        np.testing.assert_allclose(complex_currents2, transformer.res_currents[1].m)
    for res_switch in res_network["switches"]:
        switch = en.switches[res_switch["id"]]
        assert res_switch["phases"] == switch.phases
        complex_currents1 = [i_r + 1j * i_i for i_r, i_i in res_switch["currents1"]]
        np.testing.assert_allclose(complex_currents1, switch.res_currents[0].m)
        complex_currents2 = [i_r + 1j * i_i for i_r, i_i in res_switch["currents2"]]
        np.testing.assert_allclose(complex_currents2, switch.res_currents[1].m)
    for res_load in res_network["loads"]:
        load = en.loads[res_load["id"]]
        assert res_load["phases"] == load.phases
        complex_currents = [i_r + 1j * i_i for i_r, i_i in res_load["currents"]]
        np.testing.assert_allclose(complex_currents, load.res_currents.m)
    for res_source in res_network["sources"]:
        source = en.sources[res_source["id"]]
        assert res_source["phases"] == source.phases
        complex_currents = [i_r + 1j * i_i for i_r, i_i in res_source["currents"]]
        np.testing.assert_allclose(complex_currents, source.res_currents.m)
    for res_ground in res_network["grounds"]:
        ground = en.grounds[res_ground["id"]]
        complex_potential = complex(*res_ground["potential"])
        np.testing.assert_allclose(complex_potential, ground.res_potential.m)
    for res_potential_ref in res_network["potential_refs"]:
        potential_ref = en.potential_refs[res_potential_ref["id"]]
        complex_current = complex(*res_potential_ref["current"])
        np.testing.assert_allclose(complex_current, potential_ref.res_current.m)


def test_results_to_dict_full(all_element_network_with_results):
    en = all_element_network_with_results

    # Here, `full` is True
    res_network = en.results_to_dict(full=True)
    assert set(res_network) == {
        "buses",
        "lines",
        "transformers",
        "switches",
        "loads",
        "sources",
        "grounds",
        "potential_refs",
    }
    for v in res_network.values():
        assert isinstance(v, list)
    for res_bus in res_network["buses"]:
        bus = en.buses[res_bus["id"]]
        assert res_bus["phases"] == bus.phases
        complex_potentials = [v_r + 1j * v_i for v_r, v_i in res_bus["potentials"]]
        np.testing.assert_allclose(complex_potentials, bus.res_potentials.m)
        complex_voltages = [v_r + 1j * v_i for v_r, v_i in res_bus["voltages"]]
        np.testing.assert_allclose(complex_voltages, bus.res_voltages.m)
    for res_line in res_network["lines"]:
        line = en.lines[res_line["id"]]
        assert res_line["phases"] == line.phases
        # Currents
        complex_currents1 = [i_r + 1j * i_i for i_r, i_i in res_line["currents1"]]
        np.testing.assert_allclose(complex_currents1, line.res_currents[0].m)
        complex_currents2 = [i_r + 1j * i_i for i_r, i_i in res_line["currents2"]]
        np.testing.assert_allclose(complex_currents2, line.res_currents[1].m)
        # Potentials
        complex_potentials1 = [i_r + 1j * i_i for i_r, i_i in res_line["potentials1"]]
        np.testing.assert_allclose(complex_potentials1, line.res_potentials[0].m)
        complex_potentials2 = [i_r + 1j * i_i for i_r, i_i in res_line["potentials2"]]
        np.testing.assert_allclose(complex_potentials2, line.res_potentials[1].m)
        # Powers
        complex_powers1 = [i_r + 1j * i_i for i_r, i_i in res_line["powers1"]]
        np.testing.assert_allclose(complex_powers1, line.res_powers[0].m)
        complex_powers2 = [i_r + 1j * i_i for i_r, i_i in res_line["powers2"]]
        np.testing.assert_allclose(complex_powers2, line.res_powers[1].m)
        # Voltages
        complex_voltages1 = [i_r + 1j * i_i for i_r, i_i in res_line["voltages1"]]
        np.testing.assert_allclose(complex_voltages1, line.res_voltages[0].m)
        complex_voltages2 = [i_r + 1j * i_i for i_r, i_i in res_line["voltages2"]]
        np.testing.assert_allclose(complex_voltages2, line.res_voltages[1].m)
        # Power losses
        complex_power_losses = [i_r + 1j * i_i for i_r, i_i in res_line["power_losses"]]
        np.testing.assert_allclose(complex_power_losses, line.res_power_losses.m)
        # Series currents
        complex_series_currents = [i_r + 1j * i_i for i_r, i_i in res_line["series_currents"]]
        np.testing.assert_allclose(complex_series_currents, line.res_series_currents.m)
        # Shunt currents
        complex_shunt_currents1 = [i_r + 1j * i_i for i_r, i_i in res_line["shunt_currents1"]]
        np.testing.assert_allclose(complex_shunt_currents1, line.res_shunt_currents[0].m)
        complex_shunt_currents2 = [i_r + 1j * i_i for i_r, i_i in res_line["shunt_currents2"]]
        np.testing.assert_allclose(complex_shunt_currents2, line.res_shunt_currents[1].m)
        # Shunt power losses
        complex_shunt_power_losses = [i_r + 1j * i_i for i_r, i_i in res_line["shunt_power_losses"]]
        np.testing.assert_allclose(complex_shunt_power_losses, line.res_shunt_power_losses.m)

    for res_transformer in res_network["transformers"]:
        transformer = en.transformers[res_transformer["id"]]
        assert res_transformer["phases1"] == transformer.phases1
        assert res_transformer["phases2"] == transformer.phases2
        # Currents
        complex_currents1 = [i_r + 1j * i_i for i_r, i_i in res_transformer["currents1"]]
        np.testing.assert_allclose(complex_currents1, transformer.res_currents[0].m)
        complex_currents2 = [i_r + 1j * i_i for i_r, i_i in res_transformer["currents2"]]
        np.testing.assert_allclose(complex_currents2, transformer.res_currents[1].m)
        # Power losses
        complex_power_losses = complex(*res_transformer["power_losses"])
        np.testing.assert_allclose(complex_power_losses, transformer.res_power_losses.m)
    for res_switch in res_network["switches"]:
        switch = en.switches[res_switch["id"]]
        assert res_switch["phases"] == switch.phases
        # Currents
        complex_currents1 = [i_r + 1j * i_i for i_r, i_i in res_switch["currents1"]]
        np.testing.assert_allclose(complex_currents1, switch.res_currents[0].m)
        complex_currents2 = [i_r + 1j * i_i for i_r, i_i in res_switch["currents2"]]
        np.testing.assert_allclose(complex_currents2, switch.res_currents[1].m)
        # Potentials
        complex_potentials1 = [i_r + 1j * i_i for i_r, i_i in res_switch["potentials1"]]
        np.testing.assert_allclose(complex_potentials1, switch.res_potentials[0].m)
        complex_potentials2 = [i_r + 1j * i_i for i_r, i_i in res_switch["potentials2"]]
        np.testing.assert_allclose(complex_potentials2, switch.res_potentials[1].m)
        # Powers
        complex_powers1 = [i_r + 1j * i_i for i_r, i_i in res_switch["powers1"]]
        np.testing.assert_allclose(complex_powers1, switch.res_powers[0].m)
        complex_powers2 = [i_r + 1j * i_i for i_r, i_i in res_switch["powers2"]]
        np.testing.assert_allclose(complex_powers2, switch.res_powers[1].m)
        # Voltages
        complex_voltages1 = [i_r + 1j * i_i for i_r, i_i in res_switch["voltages1"]]
        np.testing.assert_allclose(complex_voltages1, switch.res_voltages[0].m)
        complex_voltages2 = [i_r + 1j * i_i for i_r, i_i in res_switch["voltages2"]]
        np.testing.assert_allclose(complex_voltages2, switch.res_voltages[1].m)
    for res_load in res_network["loads"]:
        load = en.loads[res_load["id"]]
        assert res_load["phases"] == load.phases
        # Currents
        complex_currents = [i_r + 1j * i_i for i_r, i_i in res_load["currents"]]
        np.testing.assert_allclose(complex_currents, load.res_currents.m)
        # Powers
        complex_powers = [i_r + 1j * i_i for i_r, i_i in res_load["powers"]]
        np.testing.assert_allclose(complex_powers, load.res_powers.m)
        # Potentials
        if "potentials" in res_load:
            complex_potentials = [i_r + 1j * i_i for i_r, i_i in res_load["potentials"]]
            np.testing.assert_allclose(complex_potentials, load.res_potentials.m)
        # Flexible powers
        if "flexible_powers" in res_load:
            complex_flexible_powers = [i_r + 1j * i_i for i_r, i_i in res_load["flexible_powers"]]
            np.testing.assert_allclose(complex_flexible_powers, load.res_flexible_powers.m)
    for res_source in res_network["sources"]:
        source = en.sources[res_source["id"]]
        assert res_source["phases"] == source.phases
        # Currents
        complex_currents = [i_r + 1j * i_i for i_r, i_i in res_source["currents"]]
        np.testing.assert_allclose(complex_currents, source.res_currents.m)
        # Powers
        complex_powers = [i_r + 1j * i_i for i_r, i_i in res_source["powers"]]
        np.testing.assert_allclose(complex_powers, source.res_powers.m)
        # Potentials
        if "potentials" in res_source:
            complex_potentials = [i_r + 1j * i_i for i_r, i_i in res_source["potentials"]]
            np.testing.assert_allclose(complex_potentials, source.res_potentials.m)
    for res_ground in res_network["grounds"]:
        ground = en.grounds[res_ground["id"]]
        complex_potential = complex(*res_ground["potential"])
        np.testing.assert_allclose(complex_potential, ground.res_potential.m)
    for res_potential_ref in res_network["potential_refs"]:
        potential_ref = en.potential_refs[res_potential_ref["id"]]
        complex_current = complex(*res_potential_ref["current"])
        np.testing.assert_allclose(complex_current, potential_ref.res_current.m)


def test_results_to_json(small_network_with_results, tmp_path):
    en = small_network_with_results
    res_network_expected = en.results_to_dict()
    tmp_file = tmp_path / "results.json"
    en.results_to_json(tmp_file)

    with tmp_file.open() as fp:
        res_network = json.load(fp)

    assert res_network == res_network_expected


def test_propagate_potentials_center_transformers():
    # Source is located at the primary side of the transformer
    bus1 = Bus(id="bus1", phases="ab")
    PotentialRef(id="pref", element=bus1)
    VoltageSource(id="vs", bus=bus1, voltages=20000)
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="test", vg="Iii0", sn=160000, uhv=20000.0, ulv=400.0, i0=0.023, p0=460.0, psc=2350.0, vsc=0.04
    )
    bus2 = Bus(id="bus2", phases="abn")
    PotentialRef(id="pref2", element=bus2)
    Transformer(id="transfo", bus1=bus1, bus2=bus2, parameters=tp)
    en = ElectricalNetwork.from_element(bus2)
    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow()  # propagate the potentials
    npt.assert_allclose(bus2.potentials.m_as("V"), np.array([200, -200, 0], dtype=np.complex128))
