import cmath
import itertools as it
import json
import warnings
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow.utils import LoadTypeDtype
from roseau.load_flow.utils.testing import (
    access_elements_results,
    check_result_warning,
    get_result_names,
    invoke_result_access,
)
from roseau.load_flow_single.models import (
    Bus,
    CurrentLoad,
    ImpedanceLoad,
    Line,
    LineParameters,
    PowerLoad,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow_single.network import ElectricalNetwork


# The following networks are generated using the scripts/generate_test_networks.py script
@pytest.fixture
def all_elements_network_path(test_networks_path) -> Path:
    return test_networks_path / "all_elements_network.json"


@pytest.fixture
def all_elements_network(all_elements_network_path) -> ElectricalNetwork:
    """Load the network from the JSON file (without results)."""
    return ElectricalNetwork.from_json(path=all_elements_network_path, include_results=False)


@pytest.fixture
def all_elements_network_with_results(all_elements_network_path) -> ElectricalNetwork:
    """Load the network from the JSON file (with results, no need to invoke the solver)."""
    return ElectricalNetwork.from_json(path=all_elements_network_path, include_results=True)


@pytest.fixture
def small_network(test_networks_path) -> ElectricalNetwork:
    """Load the network from the JSON file (without results)."""
    return ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=False)


@pytest.fixture
def small_network_with_results(test_networks_path) -> ElectricalNetwork:
    """Load the network from the JSON file (with results, no need to invoke the solver)."""
    return ElectricalNetwork.from_json(path=test_networks_path / "small_network.json", include_results=True)


def strip_q(value):
    return None if value is None else value.m


def test_connect_and_disconnect():
    vn = 400
    source_bus = Bus(id="source")
    load_bus = Bus(id="load bus")
    vs = VoltageSource(id="vs", bus=source_bus, voltage=vn)
    load = PowerLoad(id="power load", bus=load_bus, power=100 + 0j)
    lp = LineParameters(id="test", z_line=1.0)
    line = Line(id="line", bus1=source_bus, bus2=load_bus, parameters=lp, length=10)
    en = ElectricalNetwork.from_element(source_bus)

    # Connection of a new connected component
    load_bus2 = Bus(id="load_bus2")
    tp = TransformerParameters(id="630kVA", vg="Dyn11", sn=630e3, uhv=20e3, ulv=400, z2=0.02, ym=1e-7)
    Transformer(id="transfo", bus_hv=load_bus, bus_lv=load_bus2, parameters=tp)

    # Disconnection of a load
    assert load.network == en
    load.disconnect()
    assert load.network is None
    assert load.bus is None
    with pytest.raises(RoseauLoadFlowException) as e:
        load.to_dict()
    assert e.value.msg == "The load 'power load' is disconnected and cannot be used anymore."
    assert e.value.code == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT
    new_load = PowerLoad(id="power load", bus=load_bus, power=100 + 0j)
    assert new_load.network == en

    # Disconnection of a source
    assert vs.network == en
    vs.disconnect()
    assert vs.network is None
    assert vs.bus is None
    with pytest.raises(RoseauLoadFlowException) as e:
        vs.to_dict()
    assert e.value.msg == "The source 'vs' is disconnected and cannot be used anymore."
    assert e.value.code == RoseauLoadFlowExceptionCode.DISCONNECTED_ELEMENT

    # Adding unknown element
    with pytest.raises(RoseauLoadFlowException) as e:
        en._connect_element(3)  # type: ignore
    assert "Unknown element" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Remove line => impossible
    with pytest.raises(RoseauLoadFlowException) as e:
        en._disconnect_element(line)
    assert e.value.msg == (
        "<Line: id='line', bus1='source', bus2='load bus'> is a line and cannot be disconnected from a network."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT


def test_recursive_connect_disconnect():
    vn = 400
    source_bus = Bus(id="source")
    load_bus = Bus(id="load bus")
    VoltageSource(id="vs", bus=source_bus, voltage=vn)
    load = PowerLoad(id="power load", bus=load_bus, power=100 + 0j)
    lp = LineParameters(id="test", z_line=1.0)
    line = Line(id="line", bus1=source_bus, bus2=load_bus, parameters=lp, length=10)
    en = ElectricalNetwork.from_element(source_bus)

    # Create new elements (without connecting them to the existing network)
    new_bus2 = Bus(id="new_bus2")
    new_load2 = PowerLoad(id="new_load2", bus=new_bus2, power=Q_(100, "VA"))
    new_bus = Bus(id="new_bus")
    new_load = PowerLoad(id="new_load", bus=new_bus, power=Q_(100, "VA"))
    lp = LineParameters(id="U_AL_240_without_shunt", z_line=Q_(0.1, "ohm/km"), y_shunt=None)
    new_line2 = Line(
        id="new_line2",
        bus1=new_bus2,
        bus2=new_bus,
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
        parameters=lp,
        length=0.5,
    )
    assert load_bus._connected_elements == [load, line, new_line]
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
    assert load_bus._connected_elements == [load, line, new_line]
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


def test_bad_networks():
    # No source
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    lp = LineParameters(id="test", z_line=1.0)
    line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=10)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(bus1)
    assert e.value.msg == "There is no voltage source provided in the network, you must provide at least one."
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE

    # No network has been assigned
    assert bus1.network is None
    assert line.network is None

    # Bad constructor
    bus0 = Bus(id="bus0")
    vs = VoltageSource(id="vs", bus=bus0, voltage=20e3)
    switch = Switch(id="switch", bus1=bus0, bus2=bus1)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork(
            buses=[bus0, bus1],  # no bus2
            lines=[line],
            transformers=[],
            switches=[switch],
            loads=[],
            sources=[vs],
        )
    assert "but was not passed to the ElectricalNetwork constructor." in e.value.msg
    assert bus2.id in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT

    # No network has been assigned
    assert bus0.network is None
    assert bus1.network is None
    assert line.network is None
    assert switch.network is None
    assert vs.network is None

    # No potential reference
    bus3 = Bus(id="bus3")
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="t", vg="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    t = Transformer(id="transfo", bus_hv=bus2, bus_lv=bus3, parameters=tp)

    # No network has been assigned
    assert bus0.network is None
    assert bus1.network is None
    assert line.network is None
    assert switch.network is None
    assert vs.network is None
    assert bus3.network is None
    assert t.network is None

    # Bad ID
    src_bus = Bus(id="sb")
    load_bus = Bus(id="lb")
    lp = LineParameters(id="test", z_line=1.0)
    line = Line(id="ln", bus1=src_bus, bus2=load_bus, parameters=lp, length=10)
    vs = VoltageSource(id="vs", bus=src_bus, voltage=400)
    load = PowerLoad(id="pl", bus=load_bus, power=1000)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork(
            buses={"foo": src_bus, "lb": load_bus},  # <-- ID of src_bus is wrong
            lines={"ln": line},
            transformers={},
            switches={},
            loads={"pl": load},
            sources={"vs": vs},
        )
    assert e.value.msg == "Bus ID 'sb' does not match its key in the dictionary 'foo'."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BUS_ID


def test_poorly_connected_elements():
    bus1 = Bus(id="b1")
    bus2 = Bus(id="b2")
    bus3 = Bus(id="b3")
    bus4 = Bus(id="b4")
    lp = LineParameters.from_catalogue(name="U_AL_150")
    line1 = Line(id="l1", bus1=bus1, bus2=bus2, parameters=lp, length=1)
    line2 = Line(id="l2", bus1=bus3, bus2=bus4, parameters=lp, length=1)
    vs = VoltageSource(id="vs1", bus=bus1, voltage=20e3)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork(
            buses=[bus1, bus2, bus3, bus4],
            lines=[line1, line2],
            transformers={},
            switches={},
            loads={},
            sources=[vs],
        )
    assert (
        e.value.msg
        == "The elements [\"Bus('b3'), Bus('b4'), Line('l2')\"] are not electrically connected to a voltage source."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.POORLY_CONNECTED_ELEMENT


def test_invalid_element_overrides():
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    lp = LineParameters(id="lp", z_line=1.0)
    Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=1)
    VoltageSource(id="source", bus=bus1, voltage=400)
    old_load = PowerLoad(id="load", bus=bus2, power=1000)
    ElectricalNetwork.from_element(bus1)

    # Case of a different load type on a different bus
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad(id="load", bus=bus1, current=1)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == (
        "A PowerLoad of ID 'load' is already connected to the network. Disconnect the old element "
        "first if you meant to replace it."
    )

    # Disconnect the old element first: OK
    old_load.disconnect()
    ImpedanceLoad(id="load", bus=bus1, impedance=500)

    # Case of a source (also suggests disconnecting first)
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource(id="source", bus=bus2, voltage=400)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == (
        "A VoltageSource of ID 'source' is already connected to the network. Disconnect the old "
        "element first if you meant to replace it."
    )


def test_network_frames(small_network: ElectricalNetwork):
    # Buses
    buses_gdf = small_network.buses_frame
    assert isinstance(buses_gdf, gpd.GeoDataFrame)
    assert buses_gdf.shape == (5, 4)
    assert buses_gdf.columns.tolist() == ["nominal_voltage", "min_voltage_level", "max_voltage_level", "geometry"]
    assert buses_gdf.index.name == "id"

    # Lines
    lines_gdf = small_network.lines_frame
    assert isinstance(lines_gdf, gpd.GeoDataFrame)
    assert lines_gdf.shape == (2, 6)
    assert lines_gdf.columns.tolist() == [
        "bus1_id",
        "bus2_id",
        "parameters_id",
        "length",
        "max_loading",
        "geometry",
    ]
    assert lines_gdf.index.name == "id"

    # Transformers
    transformers_gdf = small_network.transformers_frame
    assert isinstance(transformers_gdf, gpd.GeoDataFrame)
    assert transformers_gdf.shape == (1, 6)
    assert transformers_gdf.columns.tolist() == [
        "bus_hv_id",
        "bus_lv_id",
        "parameters_id",
        "tap",
        "max_loading",
        "geometry",
    ]
    assert transformers_gdf.index.name == "id"

    # Switches
    switches_gdf = small_network.switches_frame
    assert isinstance(switches_gdf, gpd.GeoDataFrame)
    assert switches_gdf.shape == (1, 3)
    assert switches_gdf.columns.tolist() == ["bus1_id", "bus2_id", "geometry"]
    assert switches_gdf.index.name == "id"

    # Loads
    loads_df = small_network.loads_frame
    assert isinstance(loads_df, pd.DataFrame)
    assert loads_df.shape == (1, 3)
    assert loads_df.columns.tolist() == ["type", "bus_id", "flexible"]
    assert loads_df.index.name == "id"

    # Sources
    sources_df = small_network.sources_frame
    assert isinstance(sources_df, pd.DataFrame)
    assert sources_df.shape == (1, 1)
    assert sources_df.columns.tolist() == ["bus_id"]
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
        )
    assert exc_info.value.code == RoseauLoadFlowExceptionCode.EMPTY_NETWORK
    assert exc_info.value.msg == "Cannot create a network without elements."


def test_to_from_dict_roundtrip(all_elements_network_with_results: ElectricalNetwork, all_elements_network_path):
    en = all_elements_network_with_results
    net_dict = en.to_dict()
    new_net = ElectricalNetwork.from_dict(net_dict)

    assert_frame_equal(en.buses_frame, new_net.buses_frame)
    assert_frame_equal(en.lines_frame, new_net.lines_frame)
    assert_frame_equal(en.transformers_frame, new_net.transformers_frame)
    assert_frame_equal(en.switches_frame, new_net.switches_frame)
    assert_frame_equal(en.loads_frame, new_net.loads_frame)
    assert_frame_equal(en.sources_frame, new_net.sources_frame)


def test_network_elements(small_network: ElectricalNetwork):
    # Add a line to the network ("New Bus 1" belongs to the network)
    bus1 = next(iter(small_network.buses.values()))
    new_bus1 = Bus(id="New Bus 1")
    assert new_bus1.network is None
    lp = LineParameters(id="test 2", z_line=10 * 1.0)
    l2 = Line(id="line2", bus1=new_bus1, bus2=bus1, parameters=lp, length=Q_(0.3, "km"))
    assert l2.network == small_network
    assert new_bus1.network == small_network

    # Add a switch ("New Bus 2" belongs to the network)
    new_bus2 = Bus(id="New Bus 2")
    assert new_bus2.network is None
    s = Switch(id="switch", bus1=new_bus1, bus2=new_bus2)
    assert s.network == small_network
    assert new_bus2.network == small_network

    # Create a second network
    bus_vs = Bus(id="bus_vs")
    VoltageSource(id="vs2", bus=bus_vs, voltage=15e3)
    small_network_2 = ElectricalNetwork.from_element(initial_bus=bus_vs)

    # Connect the two networks
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch2", bus1=new_bus1, bus2=bus_vs)
    assert e.value.msg == "The Bus 'bus_vs' is already assigned to another network."
    assert e.value.code == RoseauLoadFlowExceptionCode.SEVERAL_NETWORKS

    # Every object have their good network after this failure
    for element in it.chain(
        small_network.buses.values(),
        small_network.lines.values(),
        small_network.transformers.values(),
        small_network.switches.values(),
        small_network.loads.values(),
    ):
        assert element.network == small_network
    for element in it.chain(
        small_network_2.buses.values(),
        small_network_2.lines.values(),
        small_network_2.transformers.values(),
        small_network_2.switches.values(),
        small_network_2.loads.values(),
    ):
        assert element.network == small_network_2


def test_elements_network_attribute(small_network):
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


def test_network_results_missing(small_network):
    # Network without results
    en = small_network

    # Ensure that an exception is raised when trying to access the results on the network
    for res_name in get_result_names(type(en)):
        e = invoke_result_access(
            en, res_name, pytest.raises, RoseauLoadFlowException, match=r"The load flow results are not available"
        )
        assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN

    # Ensure that an exception is raised when trying to access the results of the elements
    for e in access_elements_results(
        en, pytest.raises, RoseauLoadFlowException, match=r"Results for \w+ '[^']+' are not available"
    ):
        assert e.value.code == RoseauLoadFlowExceptionCode.LOAD_FLOW_NOT_RUN


def test_network_results_ok(small_network_with_results):
    # Network with results
    en = small_network_with_results

    # No warning when accessing the results on the network (they are up-to-date)
    for res_name in get_result_names(type(en)):
        invoke_result_access(en, res_name, warnings.catch_warnings, action="error")

    # No warning when accessing the results of the elements
    for _ in access_elements_results(en, warnings.catch_warnings, action="error"):
        pass


def test_network_results_outdated(small_network_with_results):
    # Network with results
    en = small_network_with_results

    # Modify something to invalidate the results
    load = next(load for load in en.loads.values() if isinstance(load, PowerLoad))
    load.power = 200

    # Ensure that a warning is emitted when trying to access the results on the network
    for res_name in get_result_names(type(en)):
        invoke_result_access(en, res_name, check_result_warning, match=r"The results of this network may be outdated")

    # Ensure that a warning is emitted when trying to access the results of the elements
    for _ in access_elements_results(en, check_result_warning, match=r"The results of \w+ '[^']+' may be outdated"):
        pass


def test_network_res_buses(small_network_with_results: ElectricalNetwork):
    en = small_network_with_results
    expected_dtypes = {  # in the expected order
        "bus_id": object,
        "voltage": complex,
        "violated": pd.BooleanDtype(),
        "voltage_level": float,
        "min_voltage_level": float,
        "max_voltage_level": float,
        "nominal_voltage": float,
    }

    def assert_res_buses():
        expected_results = [
            {
                "bus_id": bus.id,
                "voltage": strip_q(bus.res_voltage),
                "violated": bus.res_violated,
                "voltage_level": strip_q(bus.res_voltage_level),
                "min_voltage_level": strip_q(bus.min_voltage_level),
                "max_voltage_level": strip_q(bus.max_voltage_level),
                "nominal_voltage": strip_q(bus.nominal_voltage),
            }
            for bus in en.buses.values()
        ]
        expected_frame = (
            pd.DataFrame.from_records(expected_results, columns=list(expected_dtypes))
            .astype(expected_dtypes)
            .set_index("bus_id")
        )
        assert_frame_equal(en.res_buses, expected_frame)

    bus0 = en.buses["Bus 0"]
    bus1 = en.buses["Bus 1"]

    # Violations not defined
    assert bus0.res_violated is None
    assert bus1.res_violated is None
    assert_res_buses()

    # Violated because u < u_min
    bus0._min_voltage_level = 1.05
    bus0._nominal_voltage = 20e3
    assert bus0.res_violated is True
    assert_res_buses()

    # Not violated
    bus1._nominal_voltage = 20e3
    bus1._min_voltage_level = 0.95
    bus1._max_voltage_level = 1.05
    assert bus1.res_violated is False
    assert_res_buses()


def test_network_res_transformers(small_network_with_results: ElectricalNetwork):
    en = small_network_with_results
    expected_dtypes = {  # in the expected order
        "transformer_id": object,
        "current_hv": complex,
        "current_lv": complex,
        "power_hv": complex,
        "power_lv": complex,
        "voltage_hv": complex,
        "voltage_lv": complex,
        "violated": pd.BooleanDtype(),
        "loading": float,
        "max_loading": float,
        "sn": float,
    }

    def assert_res_transformers():
        expected_results = [
            {
                "transformer_id": transformer.id,
                "current_hv": strip_q(transformer.side_hv.res_current),
                "current_lv": strip_q(transformer.side_lv.res_current),
                "power_hv": strip_q(transformer.side_hv.res_power),
                "power_lv": strip_q(transformer.side_lv.res_power),
                "voltage_hv": strip_q(transformer.side_hv.res_voltage),
                "voltage_lv": strip_q(transformer.side_lv.res_voltage),
                "loading": strip_q(transformer.res_loading),
                "violated": transformer.res_violated,
                "max_loading": strip_q(transformer.max_loading),
                "sn": strip_q(transformer.sn),
            }
            for transformer in en.transformers.values()
        ]
        expected_frame = (
            pd.DataFrame.from_records(expected_results, columns=list(expected_dtypes))
            .astype(expected_dtypes)
            .set_index("transformer_id")
        )
        assert_frame_equal(en.res_transformers, expected_frame)

    assert_res_transformers()


def test_network_res_lines(small_network_with_results: ElectricalNetwork):
    en = small_network_with_results
    expected_dtypes = {  # in the expected order
        "line_id": object,
        "current1": complex,
        "current2": complex,
        "power1": complex,
        "power2": complex,
        "voltage1": complex,
        "voltage2": complex,
        "series_losses": complex,
        "series_current": complex,
        "violated": pd.BooleanDtype(),
        "loading": float,
        "max_loading": float,
        "ampacity": float,
    }

    def assert_res_lines():
        expected_results = [
            {
                "line_id": line.id,
                "current1": strip_q(line.side1.res_current),
                "current2": strip_q(line.side2.res_current),
                "power1": strip_q(line.side1.res_power),
                "power2": strip_q(line.side2.res_power),
                "voltage1": strip_q(line.side1.res_voltage),
                "voltage2": strip_q(line.side2.res_voltage),
                "series_losses": strip_q(line.res_series_power_losses),
                "series_current": strip_q(line.res_series_current),
                "violated": line.res_violated,
                "loading": strip_q(line.res_loading),
                "max_loading": strip_q(line.max_loading),
                "ampacity": strip_q(line.ampacity),
            }
            for line in en.lines.values()
        ]
        expected_frame = (
            pd.DataFrame.from_records(expected_results, columns=list(expected_dtypes))
            .astype(expected_dtypes)
            .set_index("line_id")
        )
        assert_frame_equal(en.res_lines, expected_frame)

    line = next(iter(en.lines.values()))

    # Violations not defined
    assert all(line.res_violated is None for line in en.lines.values())
    assert_res_lines()

    # Not violated
    line.parameters.ampacity = 500
    assert line.res_violated is False
    assert_res_lines()

    # Violated because of ampacity
    line.parameters.ampacity = 1e-3
    assert line.res_violated is True
    assert_res_lines()

    # Violated because of max loading
    line.parameters.ampacity = 500
    line._max_loading = 1e-3 / 500
    assert line.res_violated is True
    assert_res_lines()


def test_network_res_switches(small_network_with_results: ElectricalNetwork):
    en = small_network_with_results
    expected_dtypes = {  # in the expected order
        "switch_id": object,
        "current1": complex,
        "current2": complex,
        "power1": complex,
        "power2": complex,
        "voltage1": complex,
        "voltage2": complex,
    }

    def assert_res_switches():
        expected_results = [
            {
                "switch_id": switch.id,
                "current1": strip_q(switch.side1.res_current),
                "current2": strip_q(switch.side2.res_current),
                "power1": strip_q(switch.side1.res_power),
                "power2": strip_q(switch.side2.res_power),
                "voltage1": strip_q(switch.side1.res_voltage),
                "voltage2": strip_q(switch.side2.res_voltage),
            }
            for switch in en.switches.values()
        ]
        expected_frame = (
            pd.DataFrame.from_records(expected_results, columns=list(expected_dtypes))
            .astype(expected_dtypes)
            .set_index("switch_id")
        )
        assert_frame_equal(en.res_switches, expected_frame)

    assert_res_switches()


def test_network_res_loads(small_network_with_results: ElectricalNetwork):
    en = small_network_with_results
    expected_dtypes = {  # in the expected order
        "load_id": object,
        "type": LoadTypeDtype,
        "current": complex,
        "power": complex,
        "voltage": complex,
    }

    def assert_res_loads():
        expected_results = [
            {
                "load_id": load.id,
                "type": load.type,
                "current": strip_q(load.res_current),
                "power": strip_q(load.res_power),
                "voltage": strip_q(load.res_voltage),
            }
            for load in en.loads.values()
        ]
        expected_frame = (
            pd.DataFrame.from_records(expected_results, columns=list(expected_dtypes))
            .astype(expected_dtypes)
            .set_index("load_id")
        )
        assert_frame_equal(en.res_loads, expected_frame)

    assert_res_loads()


def test_network_res_sources(small_network_with_results: ElectricalNetwork):
    en = small_network_with_results
    expected_dtypes = {  # in the expected order
        "source_id": object,
        "current": complex,
        "power": complex,
        "voltage": complex,
    }

    def assert_res_sources():
        expected_results = [
            {
                "source_id": source.id,
                "current": strip_q(source.res_current),
                "power": strip_q(source.res_power),
                "voltage": strip_q(source.res_voltage),
            }
            for source in en.sources.values()
        ]
        expected_frame = (
            pd.DataFrame.from_records(expected_results, columns=list(expected_dtypes))
            .astype(expected_dtypes)
            .set_index("source_id")
        )
        assert_frame_equal(en.res_sources, expected_frame)

    assert_res_sources()


def test_solver_warm_start(small_network: ElectricalNetwork, monkeypatch):
    load = next(load for load in small_network.loads.values() if isinstance(load, PowerLoad))
    load_bus = load.bus

    original_propagate_voltages = small_network._propagate_voltages
    original_reset_inputs = small_network._reset_inputs

    def _propagate_voltages():
        nonlocal propagate_voltages_called
        propagate_voltages_called = True
        return original_propagate_voltages()

    def _reset_inputs():
        nonlocal reset_inputs_called
        reset_inputs_called = True
        return original_reset_inputs()

    monkeypatch.setattr(small_network, "_propagate_voltages", _propagate_voltages)
    monkeypatch.setattr(small_network, "_reset_inputs", _reset_inputs)
    monkeypatch.setattr(small_network._solver, "solve_load_flow", lambda *_, **__: (1, 1e-20))

    # First case: network is valid, no results yet -> no warm start
    propagate_voltages_called = False
    reset_inputs_called = False
    assert small_network._valid
    assert not small_network._results_valid  # Results are not valid by default
    with warnings.catch_warnings(action="error"):  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=True)
    assert not propagate_voltages_called  # Is not called because it was already called in the constructor
    assert not reset_inputs_called

    # Second case: the user requested no warm start (even though the network and results are valid)
    propagate_voltages_called = False
    reset_inputs_called = False
    assert small_network._valid
    assert small_network._results_valid
    with warnings.catch_warnings(action="error"):  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=False)
    assert not propagate_voltages_called
    assert reset_inputs_called

    # Third case: network is valid, results are valid -> warm start
    propagate_voltages_called = False
    reset_inputs_called = False
    assert small_network._valid
    assert small_network._results_valid
    with warnings.catch_warnings(action="error"):  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=True)
    assert not propagate_voltages_called
    assert not reset_inputs_called

    # Fourth case (load powers changes): network is valid, results are not valid -> warm start
    propagate_voltages_called = False
    reset_inputs_called = False
    load.power = load.power + Q_(1 + 1j, "VA")
    assert small_network._valid
    assert not small_network._results_valid
    with warnings.catch_warnings(action="error"):  # Make sure there is no warning
        small_network.solve_load_flow(warm_start=True)
    assert not propagate_voltages_called
    assert not reset_inputs_called

    # Fifth case: network is not valid -> no warm start
    propagate_voltages_called = False
    reset_inputs_called = False
    new_load = PowerLoad("new_load", load_bus, power=100)
    assert new_load.network is small_network
    assert not small_network._valid
    assert not small_network._results_valid
    with warnings.catch_warnings(action="error"):  # Make sure there is no warning
        # We could warn here that the user requested warm start but the network is not valid
        # but this will be disruptive for the user especially that warm start is the default
        small_network.solve_load_flow(warm_start=True)
    assert propagate_voltages_called
    assert not reset_inputs_called


def test_propagate_voltages():
    # Delta source
    source_bus = Bus(id="source_bus")
    _ = VoltageSource(id="source", bus=source_bus, voltage=20e3)
    load_bus = Bus(id="load_bus")
    _ = Switch(id="switch", bus1=source_bus, bus2=load_bus)

    assert not load_bus._initialized
    assert not source_bus._initialized
    _ = ElectricalNetwork.from_element(source_bus)
    assert load_bus._initialized
    assert source_bus._initialized
    expected_voltages = 20e3
    assert np.allclose(load_bus.initial_voltage.m, expected_voltages)
    assert np.allclose(source_bus.initial_voltage.m, expected_voltages)


def test_to_graph(small_network: ElectricalNetwork):
    g = small_network.to_graph()
    assert isinstance(g, nx.Graph)
    assert sorted(g.nodes) == sorted(small_network.buses)
    assert sorted(g.edges) == sorted(
        (b.bus1.id, b.bus2.id)
        for b in it.chain(
            small_network.lines.values(), small_network.transformers.values(), small_network.switches.values()
        )
    )

    for bus in small_network.buses.values():
        node_data = g.nodes[bus.id]
        assert node_data["geom"] == bus.geometry

    for line in small_network.lines.values():
        edge_data = g.edges[line.bus1.id, line.bus2.id]
        ampacity = ampacity.m if (ampacity := line.parameters.ampacity) is not None else None
        assert edge_data == {
            "id": line.id,
            "type": "line",
            "parameters_id": line.parameters.id,
            "max_loading": line.max_loading.m,
            "ampacity": ampacity,
            "geom": line.geometry,
        }

    for transformer in small_network.transformers.values():
        edge_data = g.edges[transformer.bus1.id, transformer.bus2.id]
        assert edge_data == {
            "id": transformer.id,
            "type": "transformer",
            "parameters_id": transformer.parameters.id,
            "max_loading": transformer.max_loading.m,
            "geom": transformer.geometry,
            "sn": transformer.sn.m,
        }

    for switch in small_network.switches.values():
        edge_data = g.edges[switch.bus1.id, switch.bus2.id]
        assert edge_data == {"id": switch.id, "type": "switch", "geom": switch.geometry}


def test_serialization(all_elements_network, all_elements_network_with_results):
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

    # No results: include_results is ignored
    en = all_elements_network
    en_dict_with_results = en.to_dict(include_results=True)
    en_dict_without_results = en.to_dict(include_results=False)
    assert_results(en_dict_with_results, included=False)
    assert_results(en_dict_without_results, included=False)
    assert_json_close(en_dict_with_results, en_dict_without_results)
    new_en = ElectricalNetwork.from_dict(en_dict_without_results)
    assert_json_close(new_en.to_dict(), en_dict_without_results)

    # Has results: include_results is respected
    en = all_elements_network_with_results
    en_dict_with_results = en.to_dict(include_results=True)
    en_dict_without_results = en.to_dict(include_results=False)
    assert_results(en_dict_with_results, included=True)
    assert_results(en_dict_without_results, included=False)
    assert en_dict_with_results != en_dict_without_results
    # round tripping
    assert_json_close(ElectricalNetwork.from_dict(en_dict_with_results).to_dict(), en_dict_with_results)
    assert_json_close(ElectricalNetwork.from_dict(en_dict_without_results).to_dict(), en_dict_without_results)
    # default is to include the results
    assert_json_close(en.to_dict(), en_dict_with_results)

    # Has invalid results: cannot include them
    en.loads["load0"].power += Q_(1, "VA")  # <- invalidate the results
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


def test_results_to_dict(all_elements_network_with_results):
    en = all_elements_network_with_results

    # By default full=False
    res_network = en.results_to_dict()
    assert set(res_network) == {
        "buses",
        "lines",
        "transformers",
        "switches",
        "loads",
        "sources",
    }
    for v in res_network.values():
        assert isinstance(v, list)
    for res_bus in res_network["buses"]:
        bus = en.buses[res_bus.pop("id")]
        voltage = complex(*res_bus.pop("voltage"))
        np.testing.assert_allclose(voltage, bus._res_voltage)
        assert not res_bus, res_bus
    for res_line in res_network["lines"]:
        line = en.lines[res_line.pop("id")]
        current1 = complex(*res_line.pop("current1"))
        np.testing.assert_allclose(current1, line.side1.res_current.m)
        current2 = complex(*res_line.pop("current2"))
        np.testing.assert_allclose(current2, line.side2.res_current.m)
        voltage1 = complex(*res_line.pop("voltage1"))
        np.testing.assert_allclose(voltage1, line.side1.res_voltage.m)
        voltage2 = complex(*res_line.pop("voltage2"))
        np.testing.assert_allclose(voltage2, line.side2.res_voltage.m)
        assert not res_line, res_line
    for res_transformer in res_network["transformers"]:
        transformer = en.transformers[res_transformer.pop("id")]
        current_hv = complex(*res_transformer.pop("current_hv"))
        np.testing.assert_allclose(current_hv, transformer.side_hv.res_current.m)
        current_lv = complex(*res_transformer.pop("current_lv"))
        np.testing.assert_allclose(current_lv, transformer.side_lv.res_current.m)
        voltage_hv = complex(*res_transformer.pop("voltage_hv"))
        np.testing.assert_allclose(voltage_hv, transformer.side_hv.res_voltage.m)
        voltage_lv = complex(*res_transformer.pop("voltage_lv"))
        np.testing.assert_allclose(voltage_lv, transformer.side_lv.res_voltage.m)
        assert not res_transformer, res_transformer
    for res_switch in res_network["switches"]:
        switch = en.switches[res_switch.pop("id")]
        current1 = complex(*res_switch.pop("current1"))
        np.testing.assert_allclose(current1, switch.side1.res_current.m)
        current2 = complex(*res_switch.pop("current2"))
        np.testing.assert_allclose(current2, switch.side2.res_current.m)
        voltage1 = complex(*res_switch.pop("voltage1"))
        np.testing.assert_allclose(voltage1, switch.side1.res_voltage.m)
        voltage2 = complex(*res_switch.pop("voltage2"))
        np.testing.assert_allclose(voltage2, switch.side2.res_voltage.m)
        assert not res_switch, res_switch
    for res_load in res_network["loads"]:
        load = en.loads[res_load.pop("id")]
        assert res_load.pop("type") == load.type
        current = complex(*res_load.pop("current"))
        np.testing.assert_allclose(current, load.res_current.m)
        voltage = complex(*res_load.pop("voltage"))
        np.testing.assert_allclose(voltage, load.res_voltage.m)
        assert not res_load, res_load
    for res_source in res_network["sources"]:
        source = en.sources[res_source.pop("id")]
        assert res_source.pop("type") == source.type
        current = complex(*res_source.pop("current"))
        np.testing.assert_allclose(current, source.res_current.m)
        voltage = complex(*res_source.pop("voltage"))
        np.testing.assert_allclose(voltage, source.res_voltage.m)
        assert not res_source, res_source


def test_results_to_dict_full(all_elements_network_with_results):
    en = all_elements_network_with_results

    # Here, `full` is True
    res_network = en.results_to_dict(full=True)
    assert set(res_network) == {"buses", "lines", "transformers", "switches", "loads", "sources"}
    for v in res_network.values():
        assert isinstance(v, list)
    for res_bus in res_network["buses"]:
        bus = en.buses[res_bus.pop("id")]
        # Voltage
        voltage = complex(*res_bus.pop("voltage"))
        np.testing.assert_allclose(voltage, bus.res_voltage.m)
        # Voltage level
        if (voltage_level := res_bus.pop("voltage_level")) is None:
            assert bus.res_voltage_level is None
        else:
            np.testing.assert_allclose(voltage_level, bus.res_voltage_level.m)
        assert not res_bus, res_bus
    for res_line in res_network["lines"]:
        line = en.lines[res_line.pop("id")]
        # Currents
        current1 = complex(*res_line.pop("current1"))
        np.testing.assert_allclose(current1, line.side1.res_current.m)
        current2 = complex(*res_line.pop("current2"))
        np.testing.assert_allclose(current2, line.side2.res_current.m)
        # Powers
        power1 = complex(*res_line.pop("power1"))
        np.testing.assert_allclose(power1, line.side1.res_power.m)
        power2 = complex(*res_line.pop("power2"))
        np.testing.assert_allclose(power2, line.side2.res_power.m)
        # Voltages
        voltage1 = complex(*res_line.pop("voltage1"))
        np.testing.assert_allclose(voltage1, line.side1.res_voltage.m)
        voltage2 = complex(*res_line.pop("voltage2"))
        np.testing.assert_allclose(voltage2, line.side2.res_voltage.m)
        # Power losses
        power_losses = complex(*res_line.pop("power_losses"))
        np.testing.assert_allclose(power_losses, line.res_power_losses.m)
        # Series currents
        series_current = complex(*res_line.pop("series_current"))
        np.testing.assert_allclose(series_current, line.res_series_current.m)
        # Shunt currents
        shunt_currents1 = complex(*res_line.pop("shunt_current1"))
        np.testing.assert_allclose(shunt_currents1, line.side1.res_shunt_current.m)
        shunt_currents2 = complex(*res_line.pop("shunt_current2"))
        np.testing.assert_allclose(shunt_currents2, line.side2.res_shunt_current.m)
        # Series power losses
        series_power_losses = complex(*res_line.pop("series_power_losses"))
        np.testing.assert_allclose(series_power_losses, line.res_series_power_losses.m)
        # Shunt power losses
        shunt_power_losses = complex(*res_line.pop("shunt_power_losses"))
        np.testing.assert_allclose(shunt_power_losses, line.res_shunt_power_losses.m)
        # Loading
        if (loading := res_line.pop("loading")) is None:
            assert line.res_loading is None
        else:
            np.testing.assert_allclose(loading, line.res_loading.m)
        assert not res_line, res_line
    for res_transformer in res_network["transformers"]:
        transformer = en.transformers[res_transformer.pop("id")]
        # Currents
        current_hv = complex(*res_transformer.pop("current_hv"))
        np.testing.assert_allclose(current_hv, transformer.side_hv.res_current.m)
        current_lv = complex(*res_transformer.pop("current_lv"))
        np.testing.assert_allclose(current_lv, transformer.side_lv.res_current.m)
        # Powers
        power_hv = complex(*res_transformer.pop("power_hv"))
        np.testing.assert_allclose(power_hv, transformer.side_hv.res_power.m)
        power_lv = complex(*res_transformer.pop("power_lv"))
        np.testing.assert_allclose(power_lv, transformer.side_lv.res_power.m)
        # Voltages
        voltage_hv = complex(*res_transformer.pop("voltage_hv"))
        np.testing.assert_allclose(voltage_hv, transformer.side_hv.res_voltage.m)
        voltage_lv = complex(*res_transformer.pop("voltage_lv"))
        np.testing.assert_allclose(voltage_lv, transformer.side_lv.res_voltage.m)
        # Power losses
        power_losses = complex(*res_transformer.pop("power_losses"))
        np.testing.assert_allclose(power_losses, transformer.res_power_losses.m)
        # Loading
        loading = res_transformer.pop("loading")
        np.testing.assert_allclose(loading, transformer.res_loading.m)
        assert not res_transformer, res_transformer
    for res_switch in res_network["switches"]:
        switch = en.switches[res_switch.pop("id")]
        # Currents
        current1 = complex(*res_switch.pop("current1"))
        np.testing.assert_allclose(current1, switch.side1.res_current.m)
        current2 = complex(*res_switch.pop("current2"))
        np.testing.assert_allclose(current2, switch.side2.res_current.m)
        # Powers
        power1 = complex(*res_switch.pop("power1"))
        np.testing.assert_allclose(power1, switch.side1.res_power.m)
        power2 = complex(*res_switch.pop("power2"))
        np.testing.assert_allclose(power2, switch.side2.res_power.m)
        # Voltages
        voltage1 = complex(*res_switch.pop("voltage1"))
        np.testing.assert_allclose(voltage1, switch.side1.res_voltage.m)
        voltage2 = complex(*res_switch.pop("voltage2"))
        np.testing.assert_allclose(voltage2, switch.side2.res_voltage.m)
        assert not res_switch, res_switch
    for res_load in res_network["loads"]:
        load = en.loads[res_load.pop("id")]
        assert res_load.pop("type") == load.type
        # Current
        current = complex(*res_load.pop("current"))
        np.testing.assert_allclose(current, load.res_current.m)
        # Power
        power = complex(*res_load.pop("power"))
        np.testing.assert_allclose(power, load.res_power.m)
        # Voltage
        voltage = complex(*res_load.pop("voltage"))
        np.testing.assert_allclose(voltage, load.res_voltage.m)
        assert not res_load, res_load
    for res_source in res_network["sources"]:
        source = en.sources[res_source.pop("id")]
        assert res_source.pop("type") == source.type
        # Current
        current = complex(*res_source.pop("current"))
        np.testing.assert_allclose(current, source.res_current.m)
        # Power
        power = complex(*res_source.pop("power"))
        np.testing.assert_allclose(power, source.res_power.m)
        # Voltage
        voltage = complex(*res_source.pop("voltage"))
        np.testing.assert_allclose(voltage, source.res_voltage.m)
        assert not res_source, res_source


def test_results_to_json(small_network_with_results, tmp_path):
    en = small_network_with_results
    res_network_expected = en.results_to_dict()
    tmp_file = tmp_path / "results.json"
    en.results_to_json(tmp_file)

    with tmp_file.open() as fp:
        res_network = json.load(fp)

    assert_json_close(res_network, res_network_expected)


def test_add_shunt_line_to_existing_network_no_segfault():
    # https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/346
    bus = Bus("Bus")
    VoltageSource("Source", bus=bus, voltage=20e3)
    ElectricalNetwork.from_element(bus)
    bus_new = Bus("New Bus")
    lp = LineParameters("LP with shunt", z_line=0.1 + 0.1j, y_shunt=0.01j)
    Line("New Line", bus1=bus, bus2=bus_new, parameters=lp, length=0.1)  # <- used to segfault here


def test_duplicate_line_parameters_id():
    # Creating a network with duplicate line parameters ID raises an exception
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    lp1 = LineParameters("LP", z_line=0.1 + 0.1j)
    lp2 = LineParameters("LP", z_line=0.1 + 0.1j)
    ln1 = Line("Line 1", bus1=bus1, bus2=bus2, parameters=lp1, length=0.1)
    ln2 = Line("Line 2", bus1=bus1, bus2=bus2, parameters=lp2, length=0.1)
    assert lp1._elements == {ln1}
    assert lp2._elements == {ln2}
    with pytest.raises(RoseauLoadFlowException) as e:
        en = ElectricalNetwork.from_element(bus1)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_ID
    assert e.value.msg == (
        "Line parameters IDs must be unique in the network. ID 'LP' is used by several line parameters objects."
    )

    # Adding the duplicate element to an existing network also raises an exception
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    lp1 = LineParameters("LP", z_line=0.1 + 0.1j)
    ln1 = Line("Line 1", bus1=bus1, bus2=bus2, parameters=lp1, length=0.1)
    en = ElectricalNetwork.from_element(bus1)
    lp2 = LineParameters("LP", z_line=0.1 + 0.1j)
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("Line 2", bus1=bus1, bus2=bus2, parameters=lp2, length=0.1)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_ID
    assert "ID 'LP' is used by several line parameters objects." in e.value.msg
    assert en._parameters["line"] == {lp1.id: lp1}

    # Setting the parameters later also raises an exception
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    lp1 = LineParameters("LP", z_line=0.1 + 0.1j)
    ln1 = Line("Line 1", bus1=bus1, bus2=bus2, parameters=lp1, length=0.1)
    ln2 = Line("Line 2", bus1=bus1, bus2=bus2, parameters=lp1, length=0.1)
    assert lp1._elements == {ln1, ln2}
    en = ElectricalNetwork.from_element(bus1)
    assert en._parameters["line"] == {lp1.id: lp1}
    lp2 = LineParameters("LP", z_line=0.1 + 0.1j)
    with pytest.raises(RoseauLoadFlowException) as e:
        ln2.parameters = lp2
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_ID
    assert "ID 'LP' is used by several line parameters objects." in e.value.msg
    assert en._parameters["line"] == {lp1.id: lp1}
    assert ln2.parameters == lp1

    # But if only one line is using the parameters, it is replaced
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    lp1 = LineParameters("LP", z_line=0.1 + 0.1j)
    ln1 = Line("Line 1", bus1=bus1, bus2=bus2, parameters=lp1, length=0.1)
    assert lp1._elements == {ln1}
    en = ElectricalNetwork.from_element(bus1)
    assert en._parameters["line"] == {lp1.id: lp1}
    lp2 = LineParameters("LP", z_line=0.1 + 0.1j)
    ln1.parameters = lp2
    assert lp1._elements == set()
    assert lp2._elements == {ln1}
    assert en._parameters["line"] == {lp2.id: lp2}


def test_duplicate_transformer_parameters_id():
    # Creating a network with duplicate transformer parameters ID raises an exception
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    tp1 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.1, ym=0.1j)
    tp2 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    tr1 = Transformer("Tr 1", bus_hv=bus1, bus_lv=bus2, parameters=tp1)
    tr2 = Transformer("Tr 2", bus_hv=bus1, bus_lv=bus2, parameters=tp2)
    assert tp1._elements == {tr1}
    assert tp2._elements == {tr2}
    with pytest.raises(RoseauLoadFlowException) as e:
        en = ElectricalNetwork.from_element(bus1)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_ID
    assert e.value.msg == (
        "Transformer parameters IDs must be unique in the network. ID 'TP' is used by several "
        "transformer parameters objects."
    )

    # Adding the duplicate element to an existing network also raises an exception
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    tp1 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.1, ym=0.1j)
    tr1 = Transformer("Tr 1", bus_hv=bus1, bus_lv=bus2, parameters=tp1)
    en = ElectricalNetwork.from_element(bus1)
    tp2 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    with pytest.raises(RoseauLoadFlowException) as e:
        tr2 = Transformer("Tr 2", bus_hv=bus1, bus_lv=bus2, parameters=tp2)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_ID
    assert "ID 'TP' is used by several transformer parameters objects." in e.value.msg
    assert en._parameters["transformer"] == {tp1.id: tp1}

    # Setting the parameters later also raises an exception
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    tp1 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.1, ym=0.1j)
    tr1 = Transformer("Tr 1", bus_hv=bus1, bus_lv=bus2, parameters=tp1)
    tr2 = Transformer("Tr 2", bus_hv=bus1, bus_lv=bus2, parameters=tp1)
    assert tp1._elements == {tr1, tr2}
    en = ElectricalNetwork.from_element(bus1)
    assert en._parameters["transformer"] == {tp1.id: tp1}
    tp2 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    with pytest.raises(RoseauLoadFlowException) as e:
        tr2.parameters = tp2
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_ID
    assert "ID 'TP' is used by several transformer parameters objects." in e.value.msg
    assert en._parameters["transformer"] == {tp1.id: tp1}
    assert tr2.parameters == tp1

    # But if only one transformer is using the parameters, it is replaced
    bus1 = Bus("Bus 1")
    bus2 = Bus("Bus 2")
    VoltageSource("Source", bus=bus1, voltage=20e3)
    tp1 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.1, ym=0.1j)
    tr1 = Transformer("Tr 1", bus_hv=bus1, bus_lv=bus2, parameters=tp1)
    assert tp1._elements == {tr1}
    en = ElectricalNetwork.from_element(bus1)
    assert en._parameters["transformer"] == {tp1.id: tp1}
    tp2 = TransformerParameters("TP", vg="Dyn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    tr1.parameters = tp2
    assert tp1._elements == set()
    assert tp2._elements == {tr1}
    assert en._parameters["transformer"] == {tp2.id: tp2}


def test_propagate_voltages_step_up_transformers():
    # Source is located at the LV side of the transformer
    bus1 = Bus(id="Bus1")
    bus2 = Bus(id="Bus2")
    VoltageSource(id="Source", bus=bus1, voltage=400)  # LV source
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="TP", vg="Dyn11", sn=160000, uhv=20000.0, ulv=400.0, i0=0.023, p0=460.0, psc=2350.0, vsc=0.04
    )
    Transformer(id="Tr", bus_lv=bus1, bus_hv=bus2, parameters=tp)
    ElectricalNetwork.from_element(bus1)  # propagate the voltages
    expected_lv_ini = 400
    expected_hv_ini = cmath.rect(20e3, -np.pi / 6)  # Dyn11 shifts by -30°
    npt.assert_allclose(bus1.initial_voltage.m, expected_lv_ini)
    npt.assert_allclose(bus2.initial_voltage.m, expected_hv_ini)
