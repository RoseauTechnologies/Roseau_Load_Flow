import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import JsonDict, Self

if TYPE_CHECKING:
    from network import ElectricalNetwork


logger = logging.getLogger(__name__)


class AbstractSolver(ABC):
    """This is an abstract class for all the solvers."""

    _newton_class: type["Newton"]
    _goldstein_newton_class: type["GoldsteinNewton"]

    def __init__(self, network: "ElectricalNetwork", **kwargs):
        """AbstractSolver constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.
        """
        self.network = network

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
        if data["solver"] == "newton":
            return cls._newton_class(network=network, linear_solver=data["linear_solver"])
        elif data["solver"] == "goldstein_newton":
            return cls._goldstein_newton_class(
                network=network, m1=data["m1"], m2=data["m2"], linear_solver=data["linear_solver"]
            )
        else:
            msg = f"Solver {data['solver']!r} is not implemented."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_TYPE)

    @abstractmethod
    def to_dict(self) -> JsonDict:
        """Return the solver information as a dictionary format."""
        raise NotImplementedError


class AbstractNewton(AbstractSolver, ABC):
    """This is an abstract class for all the Newton-Raphson solvers."""

    DEFAULT_LINEAR_SOLVER = "SparseLU"

    def __init__(self, network: "ElectricalNetwork", linear_solver: str = DEFAULT_LINEAR_SOLVER, **kwargs: Any):
        """AbstractNewton constructor

        Args:
            network:
                The electrical network for which the load flow needs to be solved.

            linear_solver:
                The name of the linear solver to use. Currently, only 'SparseLU' is supported.
        """
        super().__init__(network=network, **kwargs)
        if linear_solver != "SparseLU":
            msg = f"Linear solver {linear_solver!r} is not implemented."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINEAR_SOLVER_TYPE)

        self.linear_solver = linear_solver


class Newton(AbstractNewton):
    """The classical Newton-Raphson algorithm."""

    def to_dict(self) -> JsonDict:
        return {"solver": "newton", "linear_solver": self.linear_solver}


class GoldsteinNewton(AbstractNewton):
    """The Newton-Raphson algorithm with the Goldstein and Price linear search. It has better stability than the
    classical Newton-Raphson, without losing performance.
    """

    DEFAULT_M1 = 0.1
    DEFAULT_M2 = 0.9

    def __init__(
        self,
        network: "ElectricalNetwork",
        m1: float = DEFAULT_M1,
        m2: float = DEFAULT_M2,
        linear_solver: str = AbstractNewton.DEFAULT_LINEAR_SOLVER,
        **kwargs: Any,
    ):
        """GoldsteinNewton constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.

            m1:
                The first constant of the Goldstein and Price linear search.

            m2:
                The second constant of the Goldstein and Price linear search.

            linear_solver:
                The name of the linear solver to use. Currently, only 'SparseLU' is supported.
        """
        super().__init__(network=network, linear_solver=linear_solver, **kwargs)
        self.m1 = m1
        self.m2 = m2

    def to_dict(self) -> JsonDict:
        return {"solver": "goldstein_newton", "linear_solver": self.linear_solver, "m1": self.m1, "m2": self.m2}


AbstractSolver._newton_class = Newton
AbstractSolver._goldstein_newton_class = GoldsteinNewton
