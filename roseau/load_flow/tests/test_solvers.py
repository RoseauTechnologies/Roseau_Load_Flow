import contextlib

import numpy as np
import pytest

from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    RoseauLoadFlowException,
    RoseauLoadFlowExceptionCode,
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
    data = {"name": "newton_goldstein", "params": {"m1": 0.1, "m2": 0.9}}
    solver = AbstractSolver.from_dict(data=data, network=en)
    data2 = solver.to_dict()
    assert data == data2

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


def test_backward_forward_limitations():
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
    vs = VoltageSource(id="vs2", bus=bus3, voltages=20e3, phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert (
        "The backward-forward solver does not support loads or voltage sources with floating neutral" in e.value.args[0]
    )
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
    vs.disconnect()

    with contextlib.suppress(TypeError):  # cython solve_load_flow method has been patched
        en.solve_load_flow(solver="backward_forward")  # Ok, no loop or floating neutral

    # Add loop
    Line(id="line3", bus1=bus1, bus2=bus3, parameters=lp, length=1.0)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.solve_load_flow(solver="backward_forward")
    assert "The backward-forward solver does not support loops, but the network contains one." in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
