import logging
from typing import Optional

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import JsonDict, Solver

logger = logging.getLogger(__name__)

_SOLVERS_PARAMS: dict[Solver, list[str]] = {
    "newton": [],
    "newton_goldstein": ["m1", "m2"],
}
SOLVERS = list(_SOLVERS_PARAMS)


def check_solver_params(solver: Solver, params: Optional[JsonDict]) -> JsonDict:
    """Strip and check the solver parameters.

    Args:
        solver:
            The name of the solver used by the solver.

        params:
            The solver parameters dictionary.

    Returns:
        The updated solver parameters.
    """
    params = {} if params is None else params.copy()

    # Check the solver
    if solver not in _SOLVERS_PARAMS:
        msg = f"Solver {solver!r} is not implemented. Available solvers are: {SOLVERS}"
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_NAME)

    # Warn about and remove unexpected parameters
    param_list = _SOLVERS_PARAMS[solver]
    to_delete: list[str] = []
    for key in params:
        if key not in param_list:
            msg = "Unexpected solver parameter %r for the %r solver. Available params are: %s"
            logger.warning(msg, key, solver, param_list)
            to_delete.append(key)
    for key in to_delete:
        del params[key]

    # Extra checks per solver
    if solver == "newton":
        pass  # Nothing more to check
    elif solver == "newton_goldstein" and params.get("m1", 0.1) >= params.get("m2", 0.9):
        msg = "For the 'newton_goldstein' solver, the inequality m1 < m2 should be respected."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS)

    return params
