import contextlib

import numpy as np
import pytest

from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    Ground,
    GroundConnection,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    RoseauLoadFlowException,
    RoseauLoadFlowExceptionCode,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow._solvers import AbstractSolver, Newton, NewtonGoldstein


def test_solver():
    bus = Bus(id="bus", phases="abcn")
    VoltageSource(id="vs", bus=bus, voltages=[20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j])
    PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(bus)

    # Bad solvers
    with pytest.raises(RoseauLoadFlowException) as e:
        AbstractSolver.from_dict(data={"name": "toto", "params": {}}, network=en)
    assert "'toto' is not implemented" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_NAME

    # Bad Goldstein and Price parameters
    with pytest.raises(RoseauLoadFlowException) as e:
        # m1 and m2 provided
        AbstractSolver.from_dict(data={"name": "newton_goldstein", "params": {"m1": 0.9, "m2": 0.1}}, network=en)
    assert "the inequality m1 < m2 should be respected" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS
    with pytest.raises(RoseauLoadFlowException) as e:
        # only m1 provided (m2 defaults to 0.9)
        AbstractSolver.from_dict(data={"name": "newton_goldstein", "params": {"m1": 0.9}}, network=en)
    assert "the inequality m1 < m2 should be respected" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS

    # Good ones
    data = {"name": "newton_goldstein", "params": {"m1": 0.1, "m2": 0.9, "weighted_merit": True}}
    solver = AbstractSolver.from_dict(data=data, network=en)
    data2 = solver.to_dict()
    assert data == data2

    # A non-default weighted_merit survives the round trip
    data = {"name": "newton_goldstein", "params": {"m1": 0.1, "m2": 0.9, "weighted_merit": False}}
    solver = AbstractSolver.from_dict(data=data, network=en)
    assert isinstance(solver, NewtonGoldstein)
    assert solver.weighted_merit is False
    assert solver.to_dict() == data

    data = {"name": "newton", "params": {}}
    solver = AbstractSolver.from_dict(data=data, network=en)
    data2 = solver.to_dict()
    assert data == data2


def test_network_solver():
    bus = Bus(id="bus", phases="abcn")
    VoltageSource(id="vs", bus=bus, voltages=[20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j])
    PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(bus)

    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow()
    solver = en._solver
    assert isinstance(solver, NewtonGoldstein)

    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="newton_goldstein", solver_params={"m1": 0.2})
    assert solver == en._solver  # Solver did not change
    assert solver.m1 == 0.2
    assert solver.m2 == NewtonGoldstein.DEFAULT_M2

    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="newton")
    assert solver != en._solver
    assert isinstance(en._solver, Newton)

    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow()  # Reset to default
    assert isinstance(en._solver, NewtonGoldstein)


def test_bfs_limitations():
    bus1 = Bus(id="bus1", phases="abc")
    PotentialRef(id="pref", element=bus1)
    VoltageSource(id="vs", bus=bus1, voltages=20000)
    bus2 = Bus(id="bus2", phases="abc")
    lp = LineParameters(id="test", z_line=np.eye(3, dtype=complex))
    Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=1.0)
    bus3 = Bus(id="bus3", phases="abc")
    Line(id="line2", bus1=bus2, bus2=bus3, parameters=lp, length=1.0)
    en = ElectricalNetwork.from_element(bus1)
    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="backward_forward")  # Ok, no loop or floating neutral

    # Add floating neutral
    load = PowerLoad(id="load", bus=bus3, powers=[10, 10, 10], phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert (
        "The backward-forward solver does not support loads or voltage sources with floating neutral" in e.value.args[0]
    )
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    load.disconnect()

    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="backward_forward")  # Ok, no loop or floating neutral

    # Add floating neutral
    load = PowerLoad(id="Load", bus=bus3, powers=20e3, phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert (
        "The backward-forward solver does not support loads or voltage sources with floating neutral" in e.value.args[0]
    )
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    load.disconnect()

    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="backward_forward")  # Ok, no loop or floating neutral

    # Add second source
    src2 = VoltageSource(id="Src2", bus=bus3, voltages=20e3)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    assert e.value.msg == (
        "The backward-forward solver supports only one voltage source, but the network contains 2. "
        "Use a Newton solver instead."
    )
    src2.disconnect()

    # Add loop
    Line(id="line3", bus1=bus1, bus2=bus3, parameters=lp, length=1.0)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert "The backward-forward solver does not support loops, but the network contains one." in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD


def test_bfs_pref():
    # Potential reference on a bus which is not the source bus
    bus1 = Bus(id="Bus1", phases="abcn")
    bus2 = Bus(id="Bus2", phases="abcn")
    VoltageSource(id="Src", bus=bus1, voltages=230)
    lp = LineParameters(id="LP", z_line=0.3 * np.eye(4, dtype=np.complex128))
    Line(id="Line", bus1=bus1, bus2=bus2, parameters=lp, length=1)
    PotentialRef(id="PRef", element=bus2, phases="n")
    en = ElectricalNetwork.from_element(bus1)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    assert e.value.msg == (
        "The backward-forward solver does not support this network: potential reference 'PRef' is "
        "on bus 'Bus2' but it must be on bus 'Bus1' where its section is fed. Use a Newton solver "
        "instead."
    )

    # Potential reference on a ground connected to a bus which is not the source bus
    bus1 = Bus(id="Bus1", phases="abcn")
    bus2 = Bus(id="Bus2", phases="abcn")
    VoltageSource(id="Src", bus=bus1, voltages=230)
    lp = LineParameters(id="LP", z_line=0.3 * np.eye(4, dtype=np.complex128))
    Line(id="Line", bus1=bus1, bus2=bus2, parameters=lp, length=1)
    ground = Ground(id="Gnd")
    GroundConnection(ground=ground, element=bus2)
    PotentialRef(id="PRef", element=ground)
    en = ElectricalNetwork.from_element(bus1)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    assert e.value.msg == (
        "The backward-forward solver does not support this network: potential reference 'PRef' is "
        "on ground 'Gnd' which is connected to bus 'Bus2' but it must be connected to bus 'Bus1' "
        "where its section is fed. Use a Newton solver instead."
    )

    # Ground connected to several buses of the same section
    GroundConnection(ground=ground, element=bus1)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    assert e.value.msg == (
        "The backward-forward solver does not support this network: ground 'Gnd' is connected more "
        "than once to the section fed at bus 'Bus1' (buses 'Bus2' and 'Bus1'), which creates a "
        "loop through the ground. Use a Newton solver instead."
    )

    # Potential reference on the secondary side of a transformer, but not on the transformer bus
    tp = TransformerParameters(id="TP", vg="Ii0", uhv=20e3, ulv=230, sn=50e3, z2=0.02 + 0.05j, ym=1e-7 - 2e-6j)
    lp = LineParameters(id="LP", z_line=0.3 * np.eye(2, dtype=np.complex128))
    hv = Bus(id="HV Bus", phases="an")
    lv1 = Bus(id="LV Bus1", phases="an")
    lv2 = Bus(id="LV Bus2", phases="an")
    VoltageSource(id="Src", bus=hv, voltages=20e3)
    PotentialRef(id="PRef HV", element=hv, phases="n")
    Transformer(id="Tr", bus_hv=hv, bus_lv=lv1, parameters=tp)
    Line(id="Line", bus1=lv1, bus2=lv2, parameters=lp, length=0.2)
    PotentialRef(id="PRef LV", element=lv2, phases="n")
    en = ElectricalNetwork.from_element(hv)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    assert e.value.msg == (
        "The backward-forward solver does not support this network: potential reference 'PRef LV' "
        "is on bus 'LV Bus2' but it must be on bus 'LV Bus1' where its section is fed. Use a "
        "Newton solver instead."
    )

    # Ground holding the potential reference only connected through the line shunt admittance
    ground = Ground(id="Gnd")
    PotentialRef(id="PRef", element=ground)
    bus1 = Bus(id="Bus1", phases="abcn")
    bus2 = Bus(id="Bus2", phases="abcn")
    VoltageSource(id="Src", bus=bus1, voltages=230)
    lp = LineParameters(id="LP", z_line=0.3 * np.eye(4, dtype=np.complex128), y_shunt=1e-6j * np.eye(4))
    Line(id="Line", bus1=bus1, bus2=bus2, parameters=lp, length=1, ground=ground)
    en = ElectricalNetwork.from_element(bus1)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert e.value.code == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    assert e.value.msg == (
        "The backward-forward solver does not support this network: the section fed at bus 'Bus1' "
        "must have its potential reference on this bus or on a ground connected to it. Use a "
        "Newton solver instead."
    )


def test_bfs_supported_networks():
    lp = LineParameters(id="LP", z_line=0.3 * np.eye(4, dtype=np.complex128))

    # Potential reference on the source bus
    bus1 = Bus(id="Bus1", phases="abcn")
    bus2 = Bus(id="Bus2", phases="abcn")
    VoltageSource(id="Src", bus=bus1, voltages=230)
    Line(id="Line", bus1=bus1, bus2=bus2, parameters=lp, length=1)
    PotentialRef(id="PRef", element=bus1, phases="n")
    en = ElectricalNetwork.from_element(bus1)
    assert en._backward_forward_error is None
    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="backward_forward")

    # Potential reference on a ground connected to the source bus
    bus1 = Bus(id="Bus1", phases="abcn")
    bus2 = Bus(id="Bus2", phases="abcn")
    VoltageSource(id="Src", bus=bus1, voltages=230)
    Line(id="Line", bus1=bus1, bus2=bus2, parameters=lp, length=1)
    ground = Ground(id="Gnd")
    GroundConnection(ground=ground, element=bus1)
    PotentialRef(id="PRef", element=ground)
    en = ElectricalNetwork.from_element(bus1)
    assert en._backward_forward_error is None
    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="backward_forward")

    # One ground with a single potential reference shared by both sides of a transformer
    tp = TransformerParameters(id="TP", vg="Ii0", uhv=20e3, ulv=230, sn=50e3, z2=0.02 + 0.05j, ym=1e-7 - 2e-6j)
    lp2 = LineParameters(id="LP2", z_line=0.3 * np.eye(2, dtype=np.complex128))
    hv = Bus(id="HV Bus", phases="an")
    lv1 = Bus(id="LV Bus1", phases="an")
    lv2 = Bus(id="LV Bus2", phases="an")
    VoltageSource(id="Src", bus=hv, voltages=20e3)
    Transformer(id="Tr", bus_hv=hv, bus_lv=lv1, parameters=tp)
    Line(id="Line", bus1=lv1, bus2=lv2, parameters=lp2, length=0.2)
    ground = Ground(id="Gnd")
    GroundConnection(ground=ground, element=hv)
    GroundConnection(ground=ground, element=lv1)
    PotentialRef(id="PRef", element=ground)
    en = ElectricalNetwork.from_element(hv)
    assert en._backward_forward_error is None
    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="backward_forward")
