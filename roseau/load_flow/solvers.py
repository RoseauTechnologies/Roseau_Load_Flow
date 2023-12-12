import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

import numpy as np

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import JsonDict, Solver
from roseau.load_flow_engine.network.cy_network import CyAbstractSolver, CyNewton, CyNewtonGoldstein

logger = logging.getLogger(__name__)

_SOLVERS_PARAMS: dict[Solver, list[str]] = {
    "newton": [],
    "newton_goldstein": ["m1", "m2"],
}
SOLVERS = list(_SOLVERS_PARAMS)

if TYPE_CHECKING:
    from roseau.load_flow_engine.network import ElectricalNetwork


class AbstractSolver(ABC):
    """This is an abstract class for all the solvers."""

    name: str | None = None

    def __init__(self, network: "ElectricalNetwork", **kwargs):
        """AbstractSolver constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.
        """
        self.network = network
        self.cy_solver: CyAbstractSolver | None = None

    @classmethod
    def from_dict(cls, data: JsonDict, network: "ElectricalNetwork") -> Self:
        """AbstractSolver constructor from dict.

        Args:
            data:
                The solver data.

            network:
                The electrical network for which the load flow needs to be solved.

        Returns:
            The constructed solver.
        """
        if data["name"] == "newton":
            return Newton(network=network)
        elif data["name"] == "newton_goldstein":
            m1 = data["params"].get("m1", NewtonGoldstein.DEFAULT_M1)
            m2 = data["params"].get("m2", NewtonGoldstein.DEFAULT_M2)
            return NewtonGoldstein(network=network, m1=m1, m2=m2)
        else:
            msg = f"Solver {data['name']!r} is not implemented."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_NAME)

    def solve_load_flow(self, max_iterations: int, tolerance: float) -> tuple[int, float]:
        """Solve the load flow for the network the solver was constructed with.

        Args:
            tolerance:
                Required tolerance value on the residuals for the convergence.

            max_iterations:
                The maximum number of allowed iterations

        Returns:
            The number of iterations and the final residual
        """
        return self.cy_solver.solve_load_flow(max_iterations=max_iterations, tolerance=tolerance)

    def reset_inputs(self):
        """Reset the input vector (which is used for the first step of the newton algorithm) to its initial value"""
        self.cy_solver.reset_inputs()

    @abstractmethod
    def update_network(self, network: "ElectricalNetwork") -> None:
        """If the network has changed, we need to re-create a solver for this new network."""
        raise NotImplementedError

    def to_dict(self) -> JsonDict:
        """Return the solver information as a dictionary format."""
        return {"name": self.name, "params": self.params()}

    def params(self) -> JsonDict:
        """Return the parameters of the solver."""
        return {}


class AbstractNewton(AbstractSolver, ABC):
    """This is an abstract class for all the Newton-Raphson solvers."""

    DEFAULT_TAPE_OPTIMIZATION: bool = True

    def __init__(self, network: "ElectricalNetwork", optimize_tape: bool = DEFAULT_TAPE_OPTIMIZATION, **kwargs: Any):
        """AbstractNewton constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.

            optimize_tape:
                If True, a tape optimization will be performed. This operation might take a bit of time, but will make
                every subsequent load flow to run faster.
        """
        super().__init__(network=network, **kwargs)
        self.optimize_tape = optimize_tape

    def save_matrix(self, prefix: str) -> None:
        """Output files of the jacobian and vector matrix of the first newton step. Those files can be used to launch an
        eigen solver benchmark (see https://eigen.tuxfamily.org/dox/group__TopicSparseSystems.html)

        Args:
            prefix:
                The prefix of the name of the files. They will be output as prefix.mtx and prefix_m.mtx to follow Eigen
                solver benchmark convention.
        """
        self.cy_solver.save_matrix(prefix)

    def current_jacobian(self) -> np.ndarray:
        """Show the jacobian of the current iteration (useful for debugging)"""
        return self.cy_solver.current_jacobian()


class Newton(AbstractNewton):
    """The classical Newton-Raphson algorithm."""

    name = "newton"

    def __init__(
        self,
        network: "ElectricalNetwork",
        optimize_tape: bool = AbstractNewton.DEFAULT_TAPE_OPTIMIZATION,
        **kwargs: Any,
    ):
        """Newton constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.

            optimize_tape:
                If True, a tape optimization will be performed. This operation might take a bit of time, but will make
                every subsequent load flow to run faster.
        """
        super().__init__(network=network, optimize_tape=optimize_tape, **kwargs)
        self.cy_solver = CyNewton(network=network.cy_electrical_network, optimize_tape=optimize_tape)

    def update_network(self, network: "ElectricalNetwork") -> None:
        self.cy_solver = CyNewton(network=network.cy_electrical_network, optimize_tape=self.optimize_tape)


class NewtonGoldstein(AbstractNewton):
    """The Newton-Raphson algorithm with the Goldstein and Price linear search. It has better stability than the
    classical Newton-Raphson, without losing performance.
    """

    name = "newton_goldstein"

    DEFAULT_M1 = 0.1
    DEFAULT_M2 = 0.9

    def __init__(
        self,
        network: "ElectricalNetwork",
        m1: float = DEFAULT_M1,
        m2: float = DEFAULT_M2,
        optimize_tape: bool = AbstractNewton.DEFAULT_TAPE_OPTIMIZATION,
        **kwargs: Any,
    ):
        """NewtonGoldstein constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.

            optimize_tape:
                If True, a tape optimization will be performed. This operation might take a bit of time, but will make
                every subsequent load flow iteration to run faster.

            m1:
                The first constant of the Goldstein and Price linear search.

            m2:
                The second constant of the Goldstein and Price linear search.
        """
        super().__init__(network=network, optimize_tape=optimize_tape, **kwargs)
        if m1 >= m2:
            msg = "For the 'newton_goldstein' solver, the inequality m1 < m2 should be respected."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS)
        self.m1 = m1
        self.m2 = m2
        self.cy_solver = CyNewtonGoldstein(
            network=network.cy_electrical_network, optimize_tape=optimize_tape, m1=m1, m2=m2
        )

    def update_network(self, network: "ElectricalNetwork") -> None:
        self.cy_solver = CyNewtonGoldstein(
            network=network.cy_electrical_network, optimize_tape=self.optimize_tape, m1=self.m1, m2=self.m2
        )

    def params(self) -> JsonDict:
        return {"m1": self.m1, "m2": self.m2}


def check_solver_params(solver: Solver, params: JsonDict | None) -> JsonDict:
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
