import pytest

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.solvers import check_solver_params


def test_solver():
    # Additional key
    solver_params = check_solver_params(
        algorithm="newton", solver_params={"linear_solver": "SparseLU", "m1": 0.1, "toto": ""}
    )
    assert "m1" not in solver_params
    assert "toto" not in solver_params
    assert "linear_solver" in solver_params

    # Bad algorithm
    with pytest.raises(RoseauLoadFlowException) as e:
        check_solver_params(algorithm="toto", solver_params={"linear_solver": "SparseLU"})
    assert "Algorithm 'toto' is not implemented" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_ALGORITHM

    # Bad linear solver
    with pytest.raises(RoseauLoadFlowException) as e:
        check_solver_params(algorithm="newton", solver_params={"linear_solver": "toto"})
    assert "Linear solver 'toto' is not implemented" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS

    # Bad Goldstein and Price parameters
    with pytest.raises(RoseauLoadFlowException) as e:
        # m1 and m2 provided
        check_solver_params(algorithm="goldstein_newton", solver_params={"m1": 0.9, "m2": 0.1})
    assert "the inequality m1 < m2 should be respected" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS
    with pytest.raises(RoseauLoadFlowException) as e:
        # only m1 provided (m2 defaults to 0.9)
        check_solver_params(algorithm="goldstein_newton", solver_params={"m1": 0.9})
    assert "the inequality m1 < m2 should be respected" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS
