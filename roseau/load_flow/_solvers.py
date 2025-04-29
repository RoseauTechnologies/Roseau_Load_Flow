import logging
import time
import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic

import numpy as np
from typing_extensions import TypeVar

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.license import activate_license, get_license
from roseau.load_flow.typing import FloatArray, FloatArrayLike1D, FloatMatrix, JsonDict, Solver
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_engine.cy_engine import (
    CyAbstractNewton,
    CyAbstractSolver,
    CyBackwardForward,
    CyNewton,
    CyNewtonGoldstein,
)

logger = logging.getLogger(__name__)

_SOLVERS_PARAMS: dict[Solver, list[str]] = {
    "newton": [],
    "newton_goldstein": ["m1", "m2"],
    "backward_forward": [],
}
SOLVERS = list(_SOLVERS_PARAMS)

if TYPE_CHECKING:
    from roseau.load_flow.network import ElectricalNetwork


_CyS_co = TypeVar("_CyS_co", bound=CyAbstractSolver, default=CyAbstractSolver, covariant=True)


class AbstractSolver(ABC, Generic[_CyS_co]):
    """This is an abstract class for all the solvers."""

    name: str | None = None

    def __init__(self, network: "ElectricalNetwork") -> None:
        """AbstractSolver constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.
        """
        self.network = network
        self._cy_solver: _CyS_co | None = None

    @classmethod
    def from_dict(cls, data: JsonDict, network: "ElectricalNetwork") -> "AbstractSolver":
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
        elif data["name"] == "backward_forward":
            return BackwardForward(network=network)
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
                The maximum number of allowed iterations.

        Returns:
            The number of iterations and the final residual.
        """
        lic = get_license()
        if lic is None:
            activate_license(key=None)

        start = time.perf_counter()
        try:
            iterations, residual = self._cy_solver.solve_load_flow(max_iterations=max_iterations, tolerance=tolerance)
        except RuntimeError as e:
            code, msg = e.args[0].split(" ", 1)
            code = int(code)
            if code == 0:
                msg = f"The license cannot be validated. The detailed error message is {msg!r}"
                exception_code = RoseauLoadFlowExceptionCode.LICENSE_ERROR
            else:
                msg, exception_code = self._parse_solver_error(code, msg)
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=exception_code) from e
        end = time.perf_counter()

        if iterations == max_iterations:
            msg = (
                f"The load flow did not converge after {iterations} iterations. The norm of the "
                f"residuals is {residual:5n}"
            )
            logger.error(msg=msg)
            raise RoseauLoadFlowException(
                msg, RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE, iterations, residual
            )
        logger.debug(f"The load flow converged after {iterations} iterations and {end - start:.3n} s.")
        return iterations, residual

    @abstractmethod
    def _parse_solver_error(self, code: int, msg: str) -> tuple[str, RoseauLoadFlowExceptionCode]:
        """Parse the solver's error code and message into a user-friendly message and an exception code."""
        raise NotImplementedError

    def reset_inputs(self) -> None:
        """Reset the input vector (which is used for the first step of the newton algorithm) to its initial value"""
        self._cy_solver.reset_inputs()

    @abstractmethod
    def update_network(self, network: "ElectricalNetwork") -> None:
        """If the network has changed, we need to re-create a solver for this new network."""
        raise NotImplementedError

    def update_params(self, params: JsonDict) -> None:
        """If the network has changed, we need to re-create a solver for this new network."""
        msg = "The update_params() method is called for a solver that doesn't have any parameters."
        warnings.warn(msg, stacklevel=find_stack_level())

    def to_dict(self) -> JsonDict:
        """Return the solver information as a dictionary format."""
        return {"name": self.name, "params": self.params()}

    def params(self) -> JsonDict:
        """Return the parameters of the solver."""
        return {}

    # Debugging methods
    # -----------------
    def save_matrix(self, prefix: str) -> None:
        """Output files of the jacobian and vector matrix of the first newton step.

        Those files can be used to launch an eigen solver benchmark
        (see https://eigen.tuxfamily.org/dox/group__TopicSparseSystems.html)

        Args:
            prefix:
                The prefix of the name of the files. They will be output as `prefix.mtx` and
                `prefix_m.mtx` to follow Eigen solver benchmark convention.
        """
        raise NotImplementedError(f"save_matrix() is not implemented for solver {self.name!r}.")

    def jacobian(self) -> FloatMatrix:
        """Get the jacobian of the current iteration (useful for debugging)."""
        raise NotImplementedError(f"jacobian() is not implemented for solver {self.name!r}.")

    def variables(self) -> FloatArray:
        """Get the variables of the current iteration (useful for debugging)."""
        return self._cy_solver.get_variables()

    def set_variables(self, variables: FloatArrayLike1D) -> None:
        """Set the independent variables (useful for debugging)."""
        self._cy_solver.set_variables(np.array(variables, dtype=np.float64))

    def residuals(self) -> FloatArray:
        """Get the residuals of the current iteration (useful for debugging)."""
        raise NotImplementedError(f"residuals() is not implemented for solver {self.name!r}.")

    def analyse_jacobian(self) -> tuple[list[int], list[int]]:
        """Analyse the jacobian to try to understand why it is singular.

        Returns:
            The vector of elements associated with a column of zeros and the vector of elements
            associated with a line which contains a NaN.
        """
        raise NotImplementedError(f"analyse_jacobian() is not implemented for solver {self.name!r}.")


_CyN_co = TypeVar("_CyN_co", bound=CyAbstractNewton, default=CyAbstractNewton, covariant=True)


class AbstractNewton(AbstractSolver[_CyN_co], ABC):
    """This is an abstract class for all the Newton-Raphson solvers."""

    DEFAULT_TAPE_OPTIMIZATION: bool = True

    def __init__(self, network: "ElectricalNetwork", optimize_tape: bool = DEFAULT_TAPE_OPTIMIZATION) -> None:
        """AbstractNewton constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.

            optimize_tape:
                If True, a tape optimization will be performed. This operation might take a bit of time, but will make
                every subsequent load flow to run faster.
        """
        super().__init__(network=network)
        self.optimize_tape = optimize_tape

    def _parse_solver_error(self, code: int, msg: str) -> tuple[str, RoseauLoadFlowExceptionCode]:
        assert code == 1, f"Unexpected error code {code} for a Newton solver."
        zero_elements_index, inf_elements_index = self.analyse_jacobian()
        if inf_elements_index:
            inf_elements = [self.network._elements[i] for i in inf_elements_index]
            printable_elements = ", ".join(f"{type(e).__name__}({e.id!r})" for e in inf_elements)
            msg += f"The problem seems to come from the elements [{printable_elements}] that induce infinite values."
            power_load = False
            flexible_load = False
            for inf_element in inf_elements:
                load = self.network.loads.get(inf_element.id)
                if load is inf_element and load.type == "power":
                    power_load = True
                    if load.is_flexible:
                        flexible_load = True
                        break
            if power_load:
                msg += " This might be caused by a bad potential initialization of a power load"
            if flexible_load:
                msg += ", or by flexible loads with very high alpha or incorrect flexible parameters voltages."
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NAN_VALUE)
        elif zero_elements_index:
            zero_elements = [self.network._elements[i] for i in zero_elements_index]
            printable_elements = ", ".join(f"{type(e).__name__}({e.id!r})" for e in zero_elements)
            msg += (
                f"The problem seems to come from the elements [{printable_elements}] that have at "
                f"least one disconnected phase."
            )
        return msg, RoseauLoadFlowExceptionCode.BAD_JACOBIAN

    # Debugging methods
    # -----------------
    def save_matrix(self, prefix: str) -> None:
        self._cy_solver.save_matrix(prefix)

    def jacobian(self) -> FloatMatrix:
        return self._cy_solver.get_jacobian()

    def residuals(self) -> FloatArray:
        return self._cy_solver.get_residuals()

    def analyse_jacobian(self) -> tuple[list[int], list[int]]:
        return self._cy_solver.analyse_jacobian()


class Newton(AbstractNewton[CyNewton]):
    """The classical Newton-Raphson algorithm."""

    name = "newton"

    def __init__(
        self, network: "ElectricalNetwork", optimize_tape: bool = AbstractNewton.DEFAULT_TAPE_OPTIMIZATION
    ) -> None:
        """Newton constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.

            optimize_tape:
                If True, a tape optimization will be performed. This operation might take a bit of time, but will make
                every subsequent load flow to run faster.
        """
        super().__init__(network=network, optimize_tape=optimize_tape)
        self._cy_solver = CyNewton(network=network._cy_electrical_network, optimize_tape=optimize_tape)

    def update_network(self, network: "ElectricalNetwork") -> None:
        self._cy_solver = CyNewton(network=network._cy_electrical_network, optimize_tape=self.optimize_tape)


class NewtonGoldstein(AbstractNewton[CyNewtonGoldstein]):
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
    ) -> None:
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
        super().__init__(network=network, optimize_tape=optimize_tape)
        if m1 >= m2:
            msg = "For the 'newton_goldstein' solver, the inequality m1 < m2 should be respected."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SOLVER_PARAMS)
        self.m1 = m1
        self.m2 = m2
        self._cy_solver = CyNewtonGoldstein(
            network=network._cy_electrical_network, optimize_tape=optimize_tape, m1=m1, m2=m2
        )

    def update_network(self, network: "ElectricalNetwork") -> None:
        self._cy_solver = CyNewtonGoldstein(
            network=network._cy_electrical_network, optimize_tape=self.optimize_tape, m1=self.m1, m2=self.m2
        )

    def update_params(self, params: JsonDict) -> None:
        m1 = params.get("m1", NewtonGoldstein.DEFAULT_M1)
        m2 = params.get("m2", NewtonGoldstein.DEFAULT_M2)
        if m1 != self.m1 or m2 != self.m2:
            self._cy_solver.update_params(m1=m1, m2=m2)
            self.m1 = m1
            self.m2 = m2

    def params(self) -> JsonDict:
        return {"m1": self.m1, "m2": self.m2}


class BackwardForward(AbstractSolver[CyBackwardForward]):
    """A backward-forward implementation, less stable than Newton-Raphson based algorithms,
    but can be more performant in some cases.
    """

    name = "backward_forward"

    def __init__(self, network: "ElectricalNetwork") -> None:
        """Backward-Forward constructor.

        Args:
            network:
                The electrical network for which the load flow needs to be solved.
        """
        super().__init__(network=network)
        self._cy_solver = CyBackwardForward(network=network._cy_electrical_network)

    def update_network(self, network: "ElectricalNetwork") -> None:
        self._cy_solver = CyBackwardForward(network=network._cy_electrical_network)

    def solve_load_flow(self, max_iterations: int, tolerance: float) -> tuple[int, float]:
        if self.network._has_loop:
            msg = "The backward-forward solver does not support loops, but the network contains one."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD)
        if self.network._has_floating_neutral:
            msg = (
                "The backward-forward solver does not support loads or voltage sources with floating neutral, "
                "but the network contains at least one."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD)
        return super().solve_load_flow(max_iterations, tolerance)

    def _parse_solver_error(self, code: int, msg: str) -> tuple[str, RoseauLoadFlowExceptionCode]:
        assert code == 2, f"Unexpected error code {code} for a Backward-Forward solver."
        return msg, RoseauLoadFlowExceptionCode.NO_BACKWARD_FORWARD
