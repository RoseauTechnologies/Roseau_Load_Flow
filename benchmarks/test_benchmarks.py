"""Performance benchmarks for Roseau Load Flow, measured with CodSpeed.

These benchmarks exercise the hot paths of the library: building an electrical
network from serialized data, running the load flow solver, and serializing the
network (with and without results) back to a dictionary.

They rely on the small sample networks bundled in the catalogue. All of the
selected networks stay within the 10-bus limit of the free public license key
(documented in the project README), so the benchmarks run without a commercial
license. If a ``ROSEAU_LOAD_FLOW_LICENSE_KEY`` is provided in the environment,
it is used instead.
"""

import os

import pytest

import roseau.load_flow as rlf

# Free public license key, valid for networks with up to 10 buses (see README).
FREE_LICENSE_KEY = "A8C6DA-9405FB-E74FB9-C71C3C-207661-V3"

# Catalogue networks of increasing size, all within the free-license bus limit.
NETWORKS = (
    "LVFeeder06713",  # 3 buses
    "LVFeeder04790",  # 4 buses
    "LVFeeder06975",  # 6 buses
    "LVFeeder02639",  # 7 buses
    "LVFeeder00939",  # 8 buses
)
LOAD_POINT = "Winter"


@pytest.fixture(scope="session", autouse=True)
def _license():
    """Activate the license once for the whole benchmark session.

    A ``ROSEAU_LOAD_FLOW_LICENSE_KEY`` from the environment takes precedence;
    otherwise the free public key is used (valid for networks up to 10 buses).
    """
    if not os.environ.get("ROSEAU_LOAD_FLOW_LICENSE_KEY"):
        os.environ["ROSEAU_LOAD_FLOW_LICENSE_KEY"] = FREE_LICENSE_KEY
    rlf.activate_license()


@pytest.fixture(params=NETWORKS, ids=NETWORKS)
def network_dict(request):
    """Return the serialized form of a catalogue network."""
    return rlf.ElectricalNetwork.from_catalogue(request.param, LOAD_POINT).to_dict()


@pytest.mark.benchmark
def test_from_dict(benchmark, network_dict):
    """Build an :class:`ElectricalNetwork` from its serialized representation."""
    benchmark(rlf.ElectricalNetwork.from_dict, network_dict)


@pytest.mark.benchmark
def test_solve_load_flow(benchmark, network_dict):
    """Run the load flow solver from a cold start (no warm start)."""
    en = rlf.ElectricalNetwork.from_dict(network_dict, include_results=False)
    benchmark(lambda: en.solve_load_flow(warm_start=False))


@pytest.mark.benchmark
def test_to_dict_with_results(benchmark, network_dict):
    """Serialize a solved network, including its load flow results."""
    en = rlf.ElectricalNetwork.from_dict(network_dict, include_results=False)
    en.solve_load_flow(warm_start=False)
    benchmark(en.to_dict)
