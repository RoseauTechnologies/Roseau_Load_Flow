import pytest

from roseau.load_flow import (
    AbstractSolver,
    Bus,
    ElectricalNetwork,
    PotentialRef,
    RoseauLoadFlowException,
    RoseauLoadFlowExceptionCode,
    VoltageSource,
)


def test_solver():
    bus = Bus(id="bus", phases="abcn")
    VoltageSource(id="vs", bus=bus, voltages=[20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j])
    PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(bus)

    # Bad solvers
    with pytest.raises(RoseauLoadFlowException) as e:
        AbstractSolver.from_dict(data={"solver": "toto", "linear_solver": "SparseLU"}, network=en)
    assert "'toto' is not implemented" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_TYPE

    with pytest.raises(RoseauLoadFlowException) as e:
        AbstractSolver.from_dict(data={"solver": "newton", "linear_solver": "toto"}, network=en)
    assert "'toto' is not implemented" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINEAR_SOLVER_TYPE
