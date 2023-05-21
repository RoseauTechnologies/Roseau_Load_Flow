import logging
from typing import Optional

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Algorithm, JsonDict

logger = logging.getLogger(__name__)

LINEAR_SOLVERS = ["SparseLU"]

_SOLVER_PARAMS: dict[Algorithm, list[str]] = {
    "newton": ["linear_solver"],
    "goldstein_newton": ["linear_solver", "m1", "m2"],
}
ALGORITHMS = list(_SOLVER_PARAMS)


def check_solver_params(algorithm: Algorithm, solver_params: Optional[JsonDict]) -> JsonDict:
    """Strip and check the solver parameters.

    Args:
        algorithm:
            The name of the algorithm used by the solver.

        solver_params:
            The solver parameters dictionary.

    Returns:
        The updated solver parameters.
    """
    if solver_params is None:
        solver_params = {}
    else:
        solver_params = solver_params.copy()

    # Check the algorithm
    if algorithm not in _SOLVER_PARAMS:
        msg = f"Algorithm {algorithm!r} is not implemented. Available algorithms are: {ALGORITHMS}"
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_ALGORITHM)

    # Warn about and remove unexpected parameters
    param_list = _SOLVER_PARAMS[algorithm]
    to_delete: list[str] = []
    for key in solver_params:
        if key not in param_list:
            msg = "Unexpected solver parameter %r for the %r algorithm. Available params are: %s"
            logger.warning(msg, key, algorithm, param_list)
            to_delete.append(key)
    for key in to_delete:
        del solver_params[key]

    # Check the linear solver
    if "linear_solver" in solver_params and solver_params["linear_solver"] not in LINEAR_SOLVERS:
        msg = (
            f"Linear solver {solver_params['linear_solver']!r} is not implemented. "
            f"The implemented solvers are: {LINEAR_SOLVERS}"
        )
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS)

    # Extra checks per algorithm
    if algorithm == "newton":
        pass  # Nothing more to check
    elif algorithm == "goldstein_newton":
        if solver_params.get("m1", 0.1) >= solver_params.get("m2", 0.9):
            msg = "For the 'goldstein_newton' algorithm, the inequality m1 < m2 should be respected."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS)

    return solver_params
