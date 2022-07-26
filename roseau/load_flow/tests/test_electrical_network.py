import numpy as np
import pytest
from pandas.testing import assert_frame_equal

from roseau.load_flow import (
    AdmittanceLoad,
    Bus,
    DeltaWyeTransformer,
    ElectricalNetwork,
    Ground,
    ImpedanceLoad,
    PotentialReference,
    PowerLoad,
    ShuntLine,
    SimplifiedLine,
    Switch,
    TransformerCharacteristics,
    VoltageSource,
)
from roseau.load_flow.conftest import assert_frame_not_equal
from roseau.load_flow.models.lines.line_characteristics import LineCharacteristics
from roseau.load_flow.utils import ThundersValueError


def test_from_element():
    ground = Ground()
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        voltages=voltages,
    )
    load_bus = Bus(id="load bus", n=4)
    load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
    line = SimplifiedLine(
        id="line", n=4, bus1=vs, bus2=load_bus, line_characteristics=line_characteristics, length=10  # km
    )
    p_ref = PotentialReference(element=ground)

    en = ElectricalNetwork(buses=[vs, load_bus], branches=[line], loads=[load], special_elements=[p_ref, ground])
    en.solve_load_flow()
    buses_results_1, branches_results_1 = en.results()

    en = ElectricalNetwork.from_element(vs)
    en.solve_load_flow()
    buses_results_2, branches_results_2 = en.results()

    # Check
    assert_frame_equal(buses_results_1, buses_results_2, check_like=True)
    assert_frame_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)


def test_add_and_remove():
    ground = Ground()
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        voltages=voltages,
    )
    load_bus = Bus(id="load bus", n=4)
    load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
    line = SimplifiedLine(
        id="line", n=4, bus1=vs, bus2=load_bus, line_characteristics=line_characteristics, length=10  # km
    )
    _ = PotentialReference(element=ground)
    en = ElectricalNetwork.from_element(vs)
    en.solve_load_flow()
    buses_results_1, branches_results_1 = en.results()

    en.remove_element(load.id)
    new_load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
    en.add_element(new_load)
    en.solve_load_flow()
    buses_results_2, branches_results_2 = en.results()

    # Check
    assert_frame_equal(buses_results_1, buses_results_2, check_like=True)
    assert_frame_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)

    # Bad key
    with pytest.raises(ThundersValueError) as e:
        en.remove_element("unknown element")
    assert "is not a valid bus, branch or load key" in e.value.args[0]

    # Old element
    with pytest.raises(ThundersValueError) as e:
        en.add_element(load)
    assert "A disconnected element can not be reconnected" in e.value.args[0]

    # Adding ground
    ground2 = Ground()
    with pytest.raises(ThundersValueError) as e:
        en.add_element(ground2)
    assert e.value.args[0] == "Only lines, loads and buses can be added to the network."

    # Remove line => 2 separated connected components
    with pytest.raises(ThundersValueError) as e:
        en.remove_element(line.id)
        en.solve_load_flow()
    assert "does not have a potential reference" in e.value.args[0]


def test_bad_networks():
    # No voltage source
    ground = Ground()
    bus1 = Bus("bus1", 3)
    bus2 = Bus("bus2", 3)
    ground.connect(bus2)
    line_characteristics = LineCharacteristics("test", z_line=np.eye(3, dtype=complex))
    line = SimplifiedLine(id="line", n=3, bus1=bus1, bus2=bus2, line_characteristics=line_characteristics, length=10)
    p_ref = PotentialReference(ground)
    with pytest.raises(ThundersValueError) as e:
        ElectricalNetwork.from_element(bus1)
    assert e.value.args[0] == "There is no voltage source provided in the network, you must provide at least one."

    # Bad constructor
    vs = VoltageSource("vs", 4, ground, [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j])
    switch = Switch("switch", 4, vs, bus1)
    with pytest.raises(ThundersValueError) as e:
        ElectricalNetwork([vs, bus1], [line, switch], [], [ground, p_ref])  # no bus2
    assert "but is not in the ElectricalNetwork constructor." in e.value.args[0]
    assert bus2.id in e.value.args[0]

    # No potential reference
    bus3 = Bus("bus3", 4)
    transformer_characteristics = TransformerCharacteristics(
        type_name="160 kVA", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3, psc=2350, vsc=4
    )
    _ = DeltaWyeTransformer("transfo", bus2, bus3, transformer_characteristics)
    with pytest.raises(ThundersValueError) as e:
        ElectricalNetwork.from_element(vs)
    assert "does not have a potential reference" in e.value.args[0]

    # Good network
    ground.connect(bus3)
    en = ElectricalNetwork.from_element(vs)
    en.solve_load_flow()

    # 2 potential reference
    _ = PotentialReference(bus3)
    with pytest.raises(ThundersValueError) as e:
        ElectricalNetwork.from_element(vs)
    assert "has 2 potential references, it should have only one." in e.value.args[0]


def test_update_dynamics():
    ground = Ground()
    _ = PotentialReference(ground)
    vn = 20000 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        voltages=voltages,
    )
    bus1 = Bus(id="bus1", n=4)
    bus2 = Bus(id="bus2", n=4)
    load_bus = Bus(id="load bus", n=4)
    power_load = PowerLoad(id="load1", n=4, bus=load_bus, s=[10 + 0j, 10 + 0j, 10 + 0j])
    admittance_load = AdmittanceLoad(id="load2", n=4, bus=load_bus, y=[1e-5 + 0j, 1e-5 + 0j, 1e-5 + 0j])
    impedance_load = ImpedanceLoad(id="load3", n=4, bus=load_bus, z=[1e5 + 0j, 1e5 + 0j, 1e5 + 0j])
    transformer_characteristics = TransformerCharacteristics(
        type_name="160 kVA", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3, psc=2350, vsc=4
    )
    transformer = DeltaWyeTransformer("transfo", vs, bus1, transformer_characteristics)
    line_characteristics = LineCharacteristics(
        "test", z_line=5 * np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex)
    )
    line_characteristics_2 = LineCharacteristics("test2", z_line=5 * np.eye(4, dtype=complex))
    shunt_line = ShuntLine(
        id="line1", n=4, bus1=bus1, bus2=bus2, ground=ground, line_characteristics=line_characteristics, length=1.0
    )
    simplified_line = SimplifiedLine(
        id="line2", n=4, bus1=bus2, bus2=load_bus, line_characteristics=line_characteristics_2, length=1.0
    )

    # Change dynamic parameters before network creation
    power_load.update_powers([15 + 0j, 15 + 0j, 15 + 0j])

    # Network creation
    en = ElectricalNetwork.from_element(vs)
    en.solve_load_flow()
    buses_results_1, branches_results_1 = en.results()

    # Update voltage source
    vn = 20000 / np.sqrt(3) * 1.01
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs.update_voltages(voltages)
    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
    buses_results_1, branches_results_1 = buses_results_2, branches_results_2

    # Update voltage source 2
    vn = 20000 / np.sqrt(3) * 1.00
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    en.set_source_voltages(voltages)
    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
    buses_results_1, branches_results_1 = buses_results_2, branches_results_2

    # Update transformer
    transformer_characteristics = TransformerCharacteristics(
        type_name="160 kVA", windings="Dz6", uhv=20000, ulv=400, sn=200 * 1e3, p0=460, i0=2.3, psc=2350, vsc=4
    )
    with pytest.raises(ThundersValueError) as e:
        transformer.update_transformer_parameters(transformer_characteristics)  # Bad windings
    assert "The updated windings changed for transformer" in e.value.args[0]

    transformer_characteristics = TransformerCharacteristics(
        type_name="160 kVA", windings="Dyn11", uhv=20000, ulv=400, sn=200 * 1e3, p0=460, i0=2.3, psc=2350, vsc=4
    )
    transformer.update_transformer_parameters(transformer_characteristics)

    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
    buses_results_1, branches_results_1 = buses_results_2, branches_results_2

    # Update shunt line
    line_characteristics = LineCharacteristics(
        "test", z_line=4 * np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex)
    )
    shunt_line.update_line_parameters(line_characteristics)

    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
    buses_results_1, branches_results_1 = buses_results_2, branches_results_2

    # Update simplified line
    line_characteristics_2 = LineCharacteristics("test2", z_line=2 * np.eye(4, dtype=complex))
    simplified_line.update_line_parameters(line_characteristics_2)

    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
    buses_results_1, branches_results_1 = buses_results_2, branches_results_2

    # Update power load
    power_load.update_powers([20 + 0j, 20 + 0j, 20 + 0j])
    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
    buses_results_1, branches_results_1 = buses_results_2, branches_results_2

    # Update admittance load
    admittance_load.update_admittances([1e-3 + 0j, 1e-3 + 0j, 1e-3 + 0j])
    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
    buses_results_1, branches_results_1 = buses_results_2, branches_results_2

    # Update impedance load
    impedance_load.update_impedance([1e3 + 0j, 1e3 + 0j, 1e3 + 0j])
    en.solve_load_flow()  # Rerun results
    buses_results_2, branches_results_2 = en.results()
    assert_frame_not_equal(buses_results_1, buses_results_2, check_like=True)  # Check that the results changed
    assert_frame_not_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
