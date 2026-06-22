"""Performance benchmarks for Roseau Load Flow, measured with CodSpeed."""

import json
from pathlib import Path

import pytest

import roseau.load_flow as rlf

TEST_NETWORKS_PATHS = list(
    Path(__file__).parent.parent.joinpath("roseau", "load_flow", "tests", "data", "networks").glob("*.json")
)


@pytest.fixture(params=TEST_NETWORKS_PATHS, ids=[path.stem for path in TEST_NETWORKS_PATHS])
def test_network_path(request) -> Path:
    return request.param


def test_from_json(benchmark, test_network_path):
    """Benchmark the time taken to create an ElectricalNetwork object from a JSON file."""
    benchmark(rlf.ElectricalNetwork.from_json, test_network_path, include_results=True)


def test_from_dict(benchmark, test_network_path):
    """Benchmark the time taken to create an ElectricalNetwork object from a dictionary."""
    with open(test_network_path, encoding="utf-8") as f:
        network_dict = json.load(f)
    benchmark(rlf.ElectricalNetwork.from_dict, network_dict, include_results=True)


def test_to_json(benchmark, test_network_path, tmp_path):
    """Benchmark the time taken to serialize an ElectricalNetwork object to a JSON string."""
    en = rlf.ElectricalNetwork.from_json(test_network_path)
    output_path = tmp_path / "network.json"
    benchmark(en.to_json, output_path, include_results=True)


def test_to_dict(benchmark, test_network_path):
    """Benchmark the time taken to serialize an ElectricalNetwork object to a dictionary."""
    en = rlf.ElectricalNetwork.from_json(test_network_path)
    benchmark(en.to_dict, include_results=True)


def test_network_results_extraction(benchmark, test_network_path):
    """Benchmark the time taken to extract all dataframe results from a network."""
    en = rlf.ElectricalNetwork.from_json(test_network_path)

    @benchmark
    def _extract():
        _ = en.res_buses
        _ = en.res_buses_voltages
        _ = en.res_buses_voltages_pp
        _ = en.res_buses_voltages_pn
        _ = en.res_lines
        _ = en.res_transformers
        _ = en.res_switches
        _ = en.res_loads
        _ = en.res_loads_voltages
        _ = en.res_loads_voltages_pp
        _ = en.res_loads_voltages_pn
        _ = en.res_sources
        _ = en.res_sources_voltages
        _ = en.res_sources_voltages_pp
        _ = en.res_sources_voltages_pn


def test_elements_results_extraction(benchmark, test_network_path):  # noqa: C901
    """Benchmark the time taken to extract all results from all elements of a network."""
    en = rlf.ElectricalNetwork.from_json(test_network_path)

    @benchmark
    def _extract():  # noqa: C901
        for bus in en.buses.values():
            _ = bus.res_potentials.m
            _ = bus.res_voltages.m
            vl = bus.res_voltage_levels
            if vl is not None:
                _ = vl.m
            if len(bus.phases.removesuffix("n")) > 1:
                _ = bus.res_voltages_pp.m
                vl_pp = bus.res_voltage_levels_pp
                if vl_pp is not None:
                    _ = vl_pp.m
            if bus.phases.endswith("n"):
                _ = bus.res_voltages_pn.m
                vl_pn = bus.res_voltage_levels_pn
                if vl_pn is not None:
                    _ = vl_pn.m
                _ = bus.res_violated
        for line in en.lines.values():
            for side in (line.side1, line.side2):
                _ = side.res_currents.m
                _ = side.res_potentials.m
                _ = side.res_voltages.m
                _ = side.res_powers.m
                _ = side.res_shunt_currents.m
                _ = side.res_shunt_losses.m
            _ = line.res_series_currents.m
            _ = line.res_series_power_losses.m
            _ = line.res_power_losses.m
            ll = line.res_loading
            if ll is not None:
                _ = ll.m
            _ = line.res_violated
        for tr in en.transformers.values():
            for side in (tr.side_hv, tr.side_lv):
                _ = side.res_currents.m
                _ = side.res_potentials.m
                _ = side.res_voltages.m
                _ = side.res_powers.m
            _ = tr.res_power_losses.m
            _ = tr.res_loading.m
            _ = tr.res_violated
        for sw in en.switches.values():
            for side in (sw.side1, sw.side2):
                _ = side.res_currents.m
                _ = side.res_potentials.m
                _ = side.res_voltages.m
                _ = side.res_powers.m
        for load in en.loads.values():
            _ = load.res_currents.m
            _ = load.res_potentials.m
            _ = load.res_voltages.m
            if len(load.phases.removesuffix("n")) > 1:
                _ = load.res_voltages_pp.m
            if load.phases.endswith("n"):
                _ = load.res_voltages_pn.m
            _ = load.res_powers.m
            _ = load.res_inner_currents.m
            _ = load.res_inner_powers.m
        for src in en.sources.values():
            _ = src.res_currents.m
            _ = src.res_potentials.m
            _ = src.res_voltages.m
            if len(src.phases.removesuffix("n")) > 1:
                _ = src.res_voltages_pp.m
            if src.phases.endswith("n"):
                _ = src.res_voltages_pn.m
            _ = src.res_powers.m
