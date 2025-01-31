from pathlib import Path

import numpy as np
from shapely import LineString, Point

import roseau.load_flow as rlf

TEST_NETWORKS_PATH = Path(rlf.__file__).parent / "tests" / "data" / "networks"


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


def generate_all_element_network() -> None:
    # Ground and potential ref
    ground = rlf.Ground("ground")
    pref = rlf.PotentialRef(id="pref", element=ground)

    # Buses
    bus0 = rlf.Bus(id="bus0", phases="abc", initial_potentials=20e3 / rlf.SQRT3 * rlf.PositiveSequence)
    bus1 = rlf.Bus(id="bus1", phases="abc")
    bus2 = rlf.Bus(id="bus2", phases="abcn")
    bus3 = rlf.Bus(id="bus3", phases="abcn")
    bus4 = rlf.Bus(id="bus4", phases="abcn")

    # Voltage source
    voltages = rlf.converters.calculate_voltages(potentials=20e3 / rlf.SQRT3 * rlf.PositiveSequence, phases="abc")
    voltage_source0 = rlf.VoltageSource(id="voltage_source0", bus=bus0, voltages=voltages, phases="abc")

    # Line between bus0 and bus1 (with shunt)
    lp0 = rlf.LineParameters.from_catalogue(name="U_AM_148", id="lp0")
    line0 = rlf.Line(id="line0", bus1=bus0, bus2=bus1, parameters=lp0, length=rlf.Q_(1.5, "km"), ground=ground)

    # Transformer between bus1 and bus2
    tp0 = rlf.TransformerParameters.from_catalogue(name="SE Minera A0Ak 100kVA 15/20kV(20) 410V Dyn11", id="tp0")
    transformer0 = rlf.Transformer(id="transformer0", bus_hv=bus1, bus_lv=bus2, parameters=tp0, tap=1.0)
    ground.connect(bus=bus2, phase="n")

    # Switch between the bus2 and the bus3
    switch0 = rlf.Switch(id="switch0", bus1=bus2, bus2=bus3)

    # Line between bus3 and bus4 (without shunt)
    lp1_tmp = rlf.LineParameters.from_catalogue(name="T_AL_75", id="lp1", nb_phases=4)
    lp1 = rlf.LineParameters(
        id=lp1_tmp.id,
        z_line=lp1_tmp.z_line,
        y_shunt=None,  # <---- No shunt
        ampacities=lp1_tmp.ampacities,
        line_type=lp1_tmp.line_type,
        materials=lp1_tmp.materials,
        insulators=lp1_tmp.insulators,
        sections=lp1_tmp.sections,
    )
    line1 = rlf.Line(id="line1", bus1=bus3, bus2=bus4, parameters=lp1, length=rlf.Q_(100, "m"))

    # Loads
    load0 = rlf.PowerLoad(id="load0", bus=bus4, powers=rlf.Q_([100 + 5j, 100 + 5j, 100 + 5j], "W"), phases="abcn")
    load1 = rlf.CurrentLoad(id="load1", bus=bus4, currents=rlf.Q_([10 + 1j, 10 + 1j, 10 + 1j], "A"), phases="abcn")
    load2 = rlf.ImpedanceLoad(id="load2", bus=bus4, impedances=rlf.Q_([1, 1, 1], "ohm"), phases="abcn")

    fp0 = rlf.FlexibleParameter.constant()
    fp1 = rlf.FlexibleParameter.p_max_u_consumption(
        u_min=rlf.Q_(210, "V"), u_down=rlf.Q_(215, "V"), s_max=rlf.Q_(150, "VA")
    )
    fp2 = rlf.FlexibleParameter.pq_u_consumption(
        up_min=rlf.Q_(210, "V"),
        up_down=rlf.Q_(215, "V"),
        uq_min=rlf.Q_(215, "V"),
        uq_down=rlf.Q_(220, "V"),
        uq_up=rlf.Q_(245, "V"),
        uq_max=rlf.Q_(250, "V"),
        s_max=rlf.Q_(150, "VA"),
    )
    load3 = rlf.PowerLoad(
        id="load3", bus=bus4, powers=rlf.Q_([100, 100, 100], "W"), phases="abcn", flexible_params=[fp0, fp1, fp2]
    )

    fp3 = rlf.FlexibleParameter.constant()
    fp4 = rlf.FlexibleParameter.p_max_u_production(
        u_up=rlf.Q_(245, "V"), u_max=rlf.Q_(250, "V"), s_max=rlf.Q_(150, "VA")
    )
    fp5 = rlf.FlexibleParameter.pq_u_production(
        up_up=rlf.Q_(245, "V"),
        up_max=rlf.Q_(250, "V"),
        uq_min=rlf.Q_(215, "V"),
        uq_down=rlf.Q_(220, "V"),
        uq_up=rlf.Q_(240, "V"),
        uq_max=rlf.Q_(245, "V"),
        s_max=rlf.Q_(150, "VA"),
    )
    load4 = rlf.PowerLoad(
        id="load4", bus=bus4, powers=rlf.Q_([-100, -100, -100], "W"), phases="abcn", flexible_params=[fp3, fp4, fp5]
    )

    fp6 = rlf.FlexibleParameter.q_u(
        u_min=rlf.Q_(215, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(245, "V"),
        s_max=rlf.Q_(150, "VA"),
        q_min=rlf.Q_(-100, "VAr"),
        q_max=rlf.Q_(100, "VAr"),
    )
    load5 = rlf.PowerLoad(
        id="load5", bus=bus4, powers=rlf.Q_([-100, -100, -100], "W"), phases="abcn", flexible_params=[fp6, fp6, fp6]
    )

    en = rlf.ElectricalNetwork(
        buses=[bus0, bus1, bus2, bus3, bus4],
        lines=[line0, line1],
        transformers=[transformer0],
        switches=[switch0],
        loads=[load0, load1, load2, load3, load4, load5],
        sources=[voltage_source0],
        grounds=[ground],
        potential_refs=[pref],
    )
    en.solve_load_flow()
    en.to_json(TEST_NETWORKS_PATH / "all_element_network.json")


if __name__ == "__main__":
    generate_small_network()
    generate_single_phase_network()
    generate_all_element_network()
