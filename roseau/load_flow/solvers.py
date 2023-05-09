import logging
from typing import Any, Optional

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode

logger = logging.getLogger(__name__)

LINEAR_SOLVERS = ["SparseLU"]


def check_solver_params(solver_name: str, solver_params: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Strip and check the solver parameters.

    Args:
        solver_name:
            The name of the solver.

        solver_params:
            The solver parameters.

    Returns:
        The updated solver parameters.
    """
    if solver_params is None:
        solver_params = {}

    if solver_name == "newton":
        param_list = ["linear_solver"]
        _strip_params(param_list=param_list, solver_params=solver_params)
        _check_linear_solver(solver_params)
    elif solver_name == "goldstein_newton":
        param_list = ["linear_solver", "m1", "m2"]
        _strip_params(param_list=param_list, solver_params=solver_params)
        _check_linear_solver(solver_params)
        if "m1" in solver_params and "m2" in solver_params and solver_params["m1"] >= solver_params["m2"]:
            msg = "For the solver 'goldstein_newton', the inequality m1 < m2 should be respected."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS)
    else:
        msg = f"Solver {solver_name!r} is not implemented."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_TYPE)

    return solver_params


def _check_linear_solver(solver_params):
    """Check that the provided linear solver is implemented.

    Args:
        solver_params:
            The solver parameters.
    """
    if "linear_solver" in solver_params and solver_params["linear_solver"] not in LINEAR_SOLVERS:
        msg = (
            f"Linear solver {solver_params['linear_solver']!r} is not implemented. "
            f"The implemented solvers are: {LINEAR_SOLVERS}"
        )
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS)


def _strip_params(param_list: list[str], solver_params: dict[str, Any]):
    """Remove the unexpected solver parameters.

    Args:
        param_list:
            The expected parameters.

        solver_params:
            The solver parameters.
    """
    to_delete = []
    for key in solver_params:
        if key not in param_list:
            logger.warning(f"Unexpected argument {key!r} to solver params. The expected solver params are {param_list}")
            to_delete.append(key)
    for key in to_delete:
        del solver_params[key]
