"""Performance benchmarks for Roseau Load Flow, measured with CodSpeed."""

import json
from pathlib import Path

import pytest

import roseau.load_flow as rlf
import roseau.load_flow_single as rlfs

ROSEAU_PATH = Path(__file__).parent.parent.joinpath("roseau")


@pytest.fixture(scope="session")
def rlf_network_path() -> Path:
    return ROSEAU_PATH.joinpath("load_flow", "tests", "data", "networks", "all_elements_network.json")


@pytest.fixture(scope="session")
def rlfs_network_path() -> Path:
    return ROSEAU_PATH.joinpath("load_flow_single", "tests", "data", "networks", "all_elements_network.json")


@pytest.fixture(scope="session")
def dgs_network_path() -> Path:
    return ROSEAU_PATH.joinpath("load_flow", "tests", "data", "dgs", "Full_Example.json")


# JSON serialization benchmarks
# -----------------------------
def test_rlf_from_json(benchmark, rlf_network_path):
    """Benchmark the creation of rlf.ElectricalNetwork from a JSON file."""
    benchmark(rlf.ElectricalNetwork.from_json, rlf_network_path, include_results=True)


def test_rlfs_from_json(benchmark, rlfs_network_path):
    """Benchmark the creation of rlfs.ElectricalNetwork from a JSON file."""
    benchmark(rlfs.ElectricalNetwork.from_json, rlfs_network_path, include_results=True)


def test_rlf_to_json(benchmark, rlf_network_path, tmp_path):
    """Benchmark the serialization of rlf.ElectricalNetwork to JSON."""
    en = rlf.ElectricalNetwork.from_json(rlf_network_path)
    output_path = tmp_path / "network.json"
    benchmark(en.to_json, output_path, include_results=True)


def test_rlfs_to_json(benchmark, rlfs_network_path, tmp_path):
    """Benchmark the serialization of rlfs.ElectricalNetwork to JSON."""
    en = rlfs.ElectricalNetwork.from_json(rlfs_network_path)
    output_path = tmp_path / "network.json"
    benchmark(en.to_json, output_path, include_results=True)


# Dict serialization benchmarks
# -----------------------------
def test_rlf_from_dict(benchmark, rlf_network_path):
    """Benchmark the creation of rlf.ElectricalNetwork from a dictionary."""
    with open(rlf_network_path, encoding="utf-8") as f:
        network_dict = json.load(f)
    benchmark(rlf.ElectricalNetwork.from_dict, network_dict, include_results=True)


def test_rlfs_from_dict(benchmark, rlfs_network_path):
    """Benchmark the creation of rlfs.ElectricalNetwork from a dictionary."""
    with open(rlfs_network_path, encoding="utf-8") as f:
        network_dict = json.load(f)
    benchmark(rlfs.ElectricalNetwork.from_dict, network_dict, include_results=True)


def test_rlf_to_dict(benchmark, rlf_network_path):
    """Benchmark the serialization of rlf.ElectricalNetwork to a dictionary."""
    en = rlf.ElectricalNetwork.from_json(rlf_network_path)
    benchmark(en.to_dict, include_results=True)


def test_rlfs_to_dict(benchmark, rlfs_network_path):
    """Benchmark the serialization of rlfs.ElectricalNetwork to a dictionary."""
    en = rlfs.ElectricalNetwork.from_json(rlfs_network_path)
    benchmark(en.to_dict, include_results=True)


# DGS serialization benchmarks
# ----------------------------
def test_rlf_from_dgs(benchmark, dgs_network_path):
    """Benchmark the creation of rlf.ElectricalNetwork from a DGS JSON file."""
    benchmark(rlf.ElectricalNetwork.from_dgs_file, dgs_network_path, use_name_as_id=True)


def test_rlfs_from_dgs(benchmark, dgs_network_path):
    """Benchmark the creation of rlfs.ElectricalNetwork from a DGS JSON file."""
    benchmark(rlfs.ElectricalNetwork.from_dgs_file, dgs_network_path, use_name_as_id=True)


# TODO: Add a test_rlf_to_dgs() benchmark once implemented in rlf
def test_rlfs_to_dgs(benchmark, dgs_network_path, tmp_path):
    """Benchmark the serialization of rlfs.ElectricalNetwork to a DGS JSON file."""
    en = rlfs.ElectricalNetwork.from_dgs_file(dgs_network_path, use_name_as_id=True)
    output_path = tmp_path / "network.json"
    benchmark(en.to_dgs_file, output_path)


# RLF conversion benchmarks
# -------------------------
# TODO: Add other conversion benchmarks once implemented in rlf and rlfs
def test_rlfs_from_rlf(benchmark, dgs_network_path):
    """Benchmark the creation of rlfs.ElectricalNetwork from rlf.ElectricalNetwork."""
    rlf_network = rlf.ElectricalNetwork.from_dgs_file(dgs_network_path, use_name_as_id=True)
    benchmark(rlfs.ElectricalNetwork.from_rlf, rlf_network, on_incompatible="ignore")


# Graph conversion benchmarks
# ---------------------------
def test_rlf_to_graph(benchmark, rlf_network_path):
    """Benchmark the conversion of rlf.ElectricalNetwork to a NetworkX graph."""
    en = rlf.ElectricalNetwork.from_json(rlf_network_path)
    benchmark(en.to_graph)


def test_rlfs_to_graph(benchmark, rlfs_network_path):
    """Benchmark the conversion of rlfs.ElectricalNetwork to a NetworkX graph."""
    en = rlfs.ElectricalNetwork.from_json(rlfs_network_path)
    benchmark(en.to_graph)


# Results extraction benchmarks
# -----------------------------
def test_rlf_network_results_extraction(benchmark, rlf_network_path):
    """Benchmark the time taken to extract all dataframe results from rlf.ElectricalNetwork."""
    en = rlf.ElectricalNetwork.from_json(rlf_network_path)

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


def test_rlfs_network_results_extraction(benchmark, rlfs_network_path):
    """Benchmark the time taken to extract all dataframe results from rlfs.ElectricalNetwork."""
    en = rlfs.ElectricalNetwork.from_json(rlfs_network_path)

    @benchmark
    def _extract():
        _ = en.res_buses
        _ = en.res_lines
        _ = en.res_transformers
        _ = en.res_switches
        _ = en.res_loads
        _ = en.res_sources


def test_rlf_elements_results_extraction(benchmark, rlf_network_path):  # noqa: C901
    """Benchmark the time taken to extract all results from all elements of rlf.ElectricalNetwork."""
    en = rlf.ElectricalNetwork.from_json(rlf_network_path)

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


def test_rlfs_elements_results_extraction(benchmark, rlfs_network_path):
    """Benchmark the time taken to extract all results from all elements of rlfs.ElectricalNetwork."""
    en = rlfs.ElectricalNetwork.from_json(rlfs_network_path)

    @benchmark
    def _extract():
        for bus in en.buses.values():
            _ = bus.res_voltage.m
            vl = bus.res_voltage_level
            if vl is not None:
                _ = vl.m
            _ = bus.res_violated
        for line in en.lines.values():
            for side in (line.side1, line.side2):
                _ = side.res_current.m
                _ = side.res_voltage.m
                _ = side.res_power.m
                _ = side.res_shunt_current.m
                _ = side.res_shunt_losses.m
            _ = line.res_series_current.m
            _ = line.res_series_power_losses.m
            _ = line.res_power_losses.m
            ll = line.res_loading
            if ll is not None:
                _ = ll.m
            _ = line.res_violated
        for tr in en.transformers.values():
            for side in (tr.side_hv, tr.side_lv):
                _ = side.res_current.m
                _ = side.res_voltage.m
                _ = side.res_power.m
            _ = tr.res_power_losses.m
            _ = tr.res_loading.m
            _ = tr.res_violated
        for sw in en.switches.values():
            for side in (sw.side1, sw.side2):
                _ = side.res_current.m
                _ = side.res_voltage.m
                _ = side.res_power.m
        for load in en.loads.values():
            _ = load.res_current.m
            _ = load.res_voltage.m
            _ = load.res_power.m
        for src in en.sources.values():
            _ = src.res_current.m
            _ = src.res_voltage.m
            _ = src.res_power.m
