from importlib import resources
from pathlib import Path

import numpy as np
from shapely import LineString, Point

import roseau.load_flow as rlf

TEST_NETWORKS_PATH = Path(resources.files("roseau.load_flow")) / "tests" / "data" / "networks"


def generate_small_network() -> None:
    # Build a small network
    point1 = Point(-1.318375372111463, 48.64794139348595)
    point2 = Point(-1.320149235966572, 48.64971306653889)
    line_string = LineString([point1, point2])

    ground = rlf.Ground("ground")
    source_bus = rlf.Bus(id="bus0", phases="abcn", geometry=point1)
    load_bus = rlf.Bus(id="bus1", phases="abcn", geometry=point2)
    ground.connect(load_bus)

    voltages = [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j]
    vs = rlf.VoltageSource(id="vs", bus=source_bus, voltages=voltages, phases="abcn")
    load = rlf.PowerLoad(id="load", bus=load_bus, powers=[100, 100, 100], phases="abcn")
    pref = rlf.PotentialRef(id="pref", element=ground)

    lp = rlf.LineParameters(id="test", z_line=10 * np.eye(4, dtype=complex))
    line = rlf.Line(
        id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=1.0, geometry=line_string
    )

    en = rlf.ElectricalNetwork(
        buses=[source_bus, load_bus],
        lines=[line],
        transformers=[],
        switches=[],
        loads=[load],
        sources=[vs],
        grounds=[ground],
        potential_refs=[pref],
    )
    en.solve_load_flow()
    en.to_json(TEST_NETWORKS_PATH / "small_network.json")


def generate_single_phase_network() -> None:
    # Build a small single-phase network
    # ----------------------------------

    # Phase "b" is chosen to catch errors where the index of the first phase may be assumed to be 0
    phases = "bn"

    # Network geometry
    point1 = Point(-1.318375372111463, 48.64794139348595)
    point2 = Point(-1.320149235966572, 48.64971306653889)
    line_string = LineString([point1, point2])

    # Network elements
    bus0 = rlf.Bus(id="bus0", phases=phases, geometry=point1)
    bus1 = rlf.Bus(id="bus1", phases=phases, geometry=point2)

    ground = rlf.Ground("ground")
    ground.connect(bus1)
    pref = rlf.PotentialRef(id="pref", element=ground)

    vs = rlf.VoltageSource(id="vs", bus=bus0, voltages=[20000.0 + 0.0j], phases=phases)
    load = rlf.PowerLoad(id="load", bus=bus1, powers=[100], phases=phases)

    lp = rlf.LineParameters(id="test", z_line=10 * np.eye(2, dtype=complex))
    line = rlf.Line(id="line", bus1=bus0, bus2=bus1, phases=phases, parameters=lp, length=1.0, geometry=line_string)

    en = rlf.ElectricalNetwork(
        buses=[bus0, bus1],
        lines=[line],
        transformers=[],
        switches=[],
        loads=[load],
        sources=[vs],
        grounds=[ground],
        potential_refs=[pref],
    )
    en.solve_load_flow()
    en.to_json(TEST_NETWORKS_PATH / "single_phase_network.json")


if __name__ == "__main__":
    generate_small_network()
    generate_single_phase_network()
