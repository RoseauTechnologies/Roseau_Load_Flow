import logging
import warnings
from typing import TYPE_CHECKING, NoReturn

import numpy as np
from numpy.typing import NDArray
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import (
    ComplexArray,
    ComplexArrayLike1D,
    ControlType,
    FloatArrayLike1D,
    JsonDict,
    ProjectionType,
)
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import JsonMixin, _optional_deps
from roseau.load_flow_engine.cy_engine import CyControl, CyFlexibleParameter, CyProjection

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from matplotlib.axes import Axes


class Control(JsonMixin):
    """Control class for flexible loads.

    This class contains the information needed to formulate the control equations. This includes the control type,
    control limits, and other factors.

    The control for a :class:`PowerLoad` instance can be of four possible types:
        * ``"constant"``: no control is applied. In this case, a simple :class:`PowerLoad` without `flexible_params`
          could have been used instead.
        * ``"p_max_u_production"``: control the maximum production active power of the load (inverter) based on the
          voltage :math:`P^{\\max}_{\\mathrm{prod}}(U)`.

        * ``"p_max_u_consumption"``: control the maximum consumption active power of the load based on the voltage
          :math:`P^{\\max}_{\\mathrm{cons}}(U)`.

        * ``"q_u"``: control the reactive power based on the voltage :math:`Q(U)`.
    """

    _DEFAULT_ALPHA: float = 1000.0
    _DEFAULT_EPSILON: float = 1e-8

    @ureg_wraps(None, (None, None, "V", "V", "V", "V", None, None))
    def __init__(
        self,
        type: ControlType,
        u_min: float | Q_[float],
        u_down: float | Q_[float],
        u_up: float | Q_[float],
        u_max: float | Q_[float],
        alpha: float = _DEFAULT_ALPHA,
        epsilon: float = _DEFAULT_EPSILON,
    ) -> None:
        """Control constructor.

        Args:
            type:
                The type of the control:
                  * ``"constant"``: no control is applied;
                  * ``"p_max_u_production"``: control the maximum production active power of the
                    load (inverter) based on the voltage :math:`P^{\\max}_{\\mathrm{prod}}(U)`;
                  * ``"p_max_u_consumption"``: control the maximum consumption active power of the
                    load based on the voltage :math:`P^{\\max}_{\\mathrm{cons}}(U)`;
                  * ``"q_u"``: control the reactive power based on the voltage :math:`Q(U)`.

            u_min:
                The minimum voltage i.e. the one the control reached the maximum action.

            u_down:
                The voltage which starts to trigger the control (lower value).

            u_up:
                The voltage  which starts to trigger the control (upper value).

            u_max:
                The maximum voltage i.e. the one the control reached its maximum action.

            alpha:
                An approximation factor used by the family function (soft clip). The bigger the
                factor is the closer the function is to the non-differentiable function.

            epsilon:
                This value is used to make a smooth inverse function. It is only useful for P control.
        """
        self._type = type
        self._u_min = u_min
        self._u_down = u_down
        self._u_up = u_up
        self._u_max = u_max
        self._alpha = alpha
        self._epsilon = epsilon
        self._check_values()
        self._cy_control = CyControl(
            t=self._type,
            u_min=self._u_min,
            u_down=self._u_down,
            u_up=self._u_up,
            u_max=self._u_max,
            alpha=self._alpha,
            epsilon=self._epsilon,
        )

    def _check_values(self) -> None:
        """Check the provided values."""
        if self.type == "constant":
            useless_values = {"u_min": self._u_min, "u_down": self._u_down, "u_up": self._u_up, "u_max": self._u_max}
        elif self.type == "p_max_u_production":
            useless_values = {"u_min": self._u_min, "u_down": self._u_down}
        elif self.type == "p_max_u_consumption":
            useless_values = {"u_max": self._u_max, "u_up": self._u_up}
        elif self.type == "q_u":
            useless_values = {}
        else:
            msg = f"Unsupported control type {self.type!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE)

        # Warn the user if a value different from 0 was given to the control for a useless value
        msg_list = []
        for name, value in useless_values.items():
            if not np.isclose(value, 0):
                msg_list.append(f"{name!r} ({value:.1f} V)")

        if msg_list:
            msg = ", ".join(msg_list)
            warnings.warn(
                message=(
                    f"Some voltage norm value(s) will not be used by the {self.type!r} control. Nevertheless, values "
                    f"different from 0 were given: {msg}"
                ),
                category=UserWarning,
                stacklevel=2,
            )

        # Raise an error if the useful values are not well-ordered and positive
        natural_order = ("u_min", "u_down", "u_up", "u_max")
        previous_name = None
        previous_value = Q_(0, "V")
        for name in natural_order:
            if name in useless_values:
                continue

            value = getattr(self, name)
            if value <= previous_value:
                if previous_name is None:
                    msg = f"{name!r} must be greater than zero as it is a voltage norm: {value:P#~} was provided."
                else:
                    msg = (
                        f"{name!r} must be greater than the value {previous_name!r}, but {value:P#~} <= "
                        f"{previous_value:P#~}."
                    )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE)

            previous_value = value
            previous_name = name

        # Values greater than 0
        if self._epsilon <= 0.0:
            msg = f"'epsilon' must be greater than 0 but {self._epsilon:.1f} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE)

        # alpha must be "large"
        if self._alpha < 1.0:
            msg = f"'alpha' must be greater than 1 but {self._alpha:.1f} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE)

        # epsilon must be "small"
        if self._epsilon > 1.0:
            msg = f"'epsilon' must be lower than 1 but {self._epsilon:.3f} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Control):
            return NotImplemented
        return (
            (self.type == other.type)
            and (self._u_min == other._u_min)
            and (self._u_down == other._u_down)
            and (self._u_up == other._u_up)
            and (self._u_max == other._u_max)
            and (self._alpha == other._alpha)
            and (self._epsilon == other._epsilon)
        )

    @property
    def type(self) -> ControlType:
        """The type of the control."""
        return self._type

    @property
    @ureg_wraps("V", (None,))
    def u_min(self) -> Q_[float]:
        """The minimum voltage i.e. the one the control reached the maximum action."""
        return self._u_min

    @property
    @ureg_wraps("V", (None,))
    def u_down(self) -> Q_[float]:
        """The voltage which starts to trigger the control (lower value)."""
        return self._u_down

    @property
    @ureg_wraps("V", (None,))
    def u_up(self) -> Q_[float]:
        """TThe voltage  which starts to trigger the control (upper value)."""
        return self._u_up

    @property
    @ureg_wraps("V", (None,))
    def u_max(self) -> Q_[float]:
        """The maximum voltage i.e. the one the control reached its maximum action."""
        return self._u_max

    @property
    def alpha(self) -> float:
        """An approximation factor used by the family function (soft clip). The bigger the factor is the closer the
        function is to the non-differentiable function."""
        return self._alpha

    @property
    def epsilon(self) -> float:
        """This value is used to make a smooth inverse function."""
        return self._epsilon

    @classmethod
    def constant(cls) -> Self:
        """Create a constant control i.e no control."""
        return cls(type="constant", u_min=0.0, u_down=0.0, u_up=0.0, u_max=0.0)

    @classmethod
    @ureg_wraps(None, (None, "V", "V", None, None))
    def p_max_u_production(
        cls,
        u_up: float | Q_[float],
        u_max: float | Q_[float],
        alpha: float = _DEFAULT_ALPHA,
        epsilon: float = _DEFAULT_EPSILON,
    ) -> Self:
        """Create a control of the type ``"p_max_u_production"``.

        See Also:
            :ref:`$P(U)$ control documentation <models-flexible_load-p_u_control>`

        Args:
            u_up:
                The voltage norm that triggers the control. A voltage higher than this value signals to
                the controller to start to reduce the production active power. On the figure, a normalised version
                :math:`U^{\\mathrm{up}\\,\\mathrm{norm.}}` is used.

            u_max:
                The maximum norm voltage i.e. the one the control reached its maximum action. A voltage
                higher than this value signals to the controller to set the production active power
                to its minimal value. On the figure, a normalised version :math:`U^{\\max\\,\\mathrm{norm.}}` is used.

            alpha:
                A factor used to soften the control function (soft clip) to make it more
                differentiable. The bigger alpha is, the closer the function is to the
                non-differentiable function. This parameter is noted :math:`\\alpha` on the figure.

            epsilon:
                This value is used to make a smooth inverse function.

        Returns:
            The ``"p_max_u_production"`` control using the provided parameters.
        """
        return cls(
            type="p_max_u_production", u_min=0.0, u_down=0.0, u_up=u_up, u_max=u_max, alpha=alpha, epsilon=epsilon
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", None, None))
    def p_max_u_consumption(
        cls,
        u_min: float | Q_[float],
        u_down: float | Q_[float],
        alpha: float = _DEFAULT_ALPHA,
        epsilon: float = _DEFAULT_EPSILON,
    ) -> Self:
        """Create a control of the type ``"p_max_u_consumption"``.

        See Also:
            :ref:`$P(U)$ control documentation <models-flexible_load-p_u_control>`

        Args:
            u_min:
                The minimum voltage norm i.e. the one the control reached its maximum action. A voltage
                lower than this value signals to the controller to set the consumption active power
                to its minimal value. On the figure, a normalised version :math:`U^{\\min\\,\\mathrm{norm.}}` is used.

            u_down:
                The voltage norm that triggers the control. A voltage lower than this value signals to
                the controller to start to reduce the consumption active power. On the figure, a normalised version
                :math:`U^{\\mathrm{down}\\,\\mathrm{norm.}}` is used.

            alpha:
                A factor used to soften the control function (soft clip) to make it more
                differentiable. The bigger alpha is, the closer the function is to the
                non-differentiable function. This parameter is noted :math:`\\alpha` on the figure.

            epsilon:
                This value is used to make a smooth inverse function.

        Returns:
            The ``"p_max_u_consumption"`` control using the provided parameters.
        """
        return cls(
            type="p_max_u_consumption", u_min=u_min, u_down=u_down, u_up=0.0, u_max=0.0, alpha=alpha, epsilon=epsilon
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "V", "V", None))
    def q_u(
        cls,
        u_min: float | Q_[float],
        u_down: float | Q_[float],
        u_up: float | Q_[float],
        u_max: float | Q_[float],
        alpha: float = _DEFAULT_ALPHA,
    ) -> Self:
        """Create a control of the type ``"q_u"``.

        See Also:
            :ref:`$Q(U)$ control documentation <models-flexible_load-q_u_control>`

        Args:
            u_min:
                The minimum voltage norm i.e. the one the control reached its maximum action. A voltage
                lower than this value signals to the controller to set the reactive power to its
                maximal capacitive value. On the figure, a normalised version :math:`U^{\\min\\,\\mathrm{norm.}}` is used.

            u_down:
                The voltage that triggers the capacitive reactive power control. A voltage lower
                than this value signals to the controller to start to increase the capacitive
                reactive power.  On the figure, a normalised version :math:`U^{\\mathrm{down}\\,\\mathrm{norm.}}` is used.

            u_up:
                The voltage that triggers the inductive reactive power control. A voltage higher
                than this value signals to the controller to start to increase the inductive
                reactive power. On the figure, a normalised version :math:`U^{\\mathrm{up}\\,\\mathrm{norm.}}` is used.

            u_max:
                The minimum voltage i.e. the one the control reached its maximum action. A voltage
                lower than this value signals to the controller to set the reactive power to its
                maximal inductive value. On the figure, a normalised version :math:`U^{\\max\\,\\mathrm{norm.}}` is used.

            alpha:
                A factor used to soften the control function (soft clip) to make it more
                differentiable. The bigger alpha is, the closer the function is to the
                non-differentiable function. This parameter is noted :math:`\\alpha` on the figure.

        Returns:
            The ``"q_u"`` control using the provided parameters.
        """
        return cls(type="q_u", u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        alpha = data.get("alpha", cls._DEFAULT_ALPHA)
        epsilon = data.get("epsilon", cls._DEFAULT_EPSILON)
        if data["type"] == "constant":
            return cls.constant()
        elif data["type"] == "p_max_u_production":
            return cls.p_max_u_production(u_up=data["u_up"], u_max=data["u_max"], alpha=alpha, epsilon=epsilon)
        elif data["type"] == "p_max_u_consumption":
            return cls.p_max_u_consumption(u_min=data["u_min"], u_down=data["u_down"], alpha=alpha, epsilon=epsilon)
        elif data["type"] == "q_u":
            return cls.q_u(
                u_min=data["u_min"], u_down=data["u_down"], u_up=data["u_up"], u_max=data["u_max"], alpha=alpha
            )
        else:
            msg = f"Unsupported control type {data['type']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE)

    def _to_dict(self, include_results: bool) -> JsonDict:
        if self.type == "constant":
            return {"type": "constant"}
        elif self.type == "p_max_u_production":
            return {
                "type": "p_max_u_production",
                "u_up": self._u_up,
                "u_max": self._u_max,
                "alpha": self._alpha,
                "epsilon": self._epsilon,
            }
        elif self.type == "p_max_u_consumption":
            return {
                "type": "p_max_u_consumption",
                "u_min": self._u_min,
                "u_down": self._u_down,
                "alpha": self._alpha,
                "epsilon": self._epsilon,
            }
        elif self.type == "q_u":
            return {
                "type": "q_u",
                "u_min": self._u_min,
                "u_down": self._u_down,
                "u_up": self._u_up,
                "u_max": self._u_max,
                "alpha": self._alpha,
            }
        else:
            msg = f"Unsupported control type {self.type!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE)

    def _results_to_dict(self, warning: bool, full: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)


class Projection(JsonMixin):
    """This class defines the projection on the feasible circle for a flexible load.

    The three possible projection types are:
        * ``"euclidean"``: for a Euclidean projection on the feasible space;
        * ``"keep_p"``: for maintaining a constant P;
        * ``"keep_q"``: for maintaining a constant Q.
    """

    _DEFAULT_ALPHA: float = 1000.0
    _DEFAULT_EPSILON: float = 1e-8
    _DEFAULT_TYPE: ProjectionType = "euclidean"

    def __init__(self, type: ProjectionType, alpha: float = _DEFAULT_ALPHA, epsilon: float = _DEFAULT_EPSILON) -> None:
        """Projection constructor.

        Args:
            type:
                The type of the projection. It can be:
                  * ``"euclidean"``: for an Euclidean projection on the feasible space;
                  * ``"keep_p"``: for maintaining a constant P;
                  * ``"keep_q"``: for maintaining a constant Q.

            alpha:
                This value is used to make soft sign function and to build a soft projection function.

            epsilon:
                This value is used to make a smooth sqrt function.
        """
        self.type = type
        self._alpha = alpha
        self._epsilon = epsilon
        self._check_values()
        self._cy_projection = CyProjection(t=type, alpha=self._alpha, epsilon=self._epsilon)

    def _check_values(self) -> None:
        """Check the provided values."""
        # Good type
        if self.type not in ("euclidean", "keep_p", "keep_q"):
            msg = f"Unsupported projection type {self.type!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PROJECTION_TYPE)

        # Values greater than 0
        for name, value in (("alpha", self._alpha), ("epsilon", self._epsilon)):
            if value <= 0:
                msg = f"'{name}' must be greater than 0 but {value:.1f} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE)

        # alpha must be "large"
        if self._alpha < 1.0:
            msg = f"'alpha' must be greater than 1 but {self._alpha:.1f} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE)

        # epsilon must be "small"
        if self._epsilon > 1.0:
            msg = f"'epsilon' must be lower than 1 but {self._epsilon:.3f} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Projection):
            return NotImplemented
        return (self.type == other.type) and (self._alpha == other._alpha) and (self._epsilon == other._epsilon)

    @property
    def alpha(self) -> float:
        """This value is used to make soft sign function and to build a soft projection function."""
        return self._alpha

    @property
    def epsilon(self) -> float:
        """This value is used to make a smooth sqrt function. It is only used in the Euclidean projection."""
        return self._epsilon

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        alpha = data.get("alpha", cls._DEFAULT_ALPHA)
        epsilon = data.get("epsilon", cls._DEFAULT_EPSILON)
        return cls(type=data["type"], alpha=alpha, epsilon=epsilon)

    def _to_dict(self, include_results: bool) -> JsonDict:
        return {"type": self.type, "alpha": self._alpha, "epsilon": self._epsilon}

    def _results_to_dict(self, warning: bool, full: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)


class FlexibleParameter(JsonMixin):
    """Flexible parameters of a flexible load.

    This class encapsulate single-phase flexibility information of a flexible load:

    * The active power :class:`roseau.load_flow.models.Control` to apply;
    * The reactive power :class:`roseau.load_flow.models.Control` to apply;
    * The :class:`Projection` to use when dealing with voltage violations;
    * The apparent power of the flexible load (VA). This is the maximum power the load can
      consume/produce. It is the radius of the feasible circle used by the projection

    For multi-phase loads, you need to use a `FlexibleParameter` instance per phase.
    """

    @ureg_wraps(None, (None, None, None, None, "VA", "VAr", "VAr"))
    def __init__(
        self,
        control_p: Control,
        control_q: Control,
        projection: Projection,
        s_max: float | Q_[float],
        q_min: float | Q_[float] | None = None,
        q_max: float | Q_[float] | None = None,
    ) -> None:
        """FlexibleParameter constructor.

        Args:
            control_p:
                The control to apply on the active power.

            control_q:
                The control to apply on the reactive power.

            projection:
                The projection to use to have a feasible result.

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible circle.

            q_min:
                The minimum reactive power of the flexible load (VAr). By default it is equal to -s_max, but it can
                be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default it is equal to s_max, but it can
                be further constrained.
        """
        self.control_p = control_p
        self.control_q = control_q
        self.projection = projection
        self._cy_fp = None
        self._q_min_value: float | None = None
        self._q_max_value: float | None = None
        self.s_max = s_max
        self.q_min = q_min
        self.q_max = q_max
        self._cy_fp = CyFlexibleParameter(
            control_p=control_p._cy_control,
            control_q=control_q._cy_control,
            projection=projection._cy_projection,
            s_max=self._s_max,
            q_min=self._q_min,
            q_max=self._q_max,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FlexibleParameter):
            return NotImplemented
        return (
            (self.control_p == other.control_p)
            and (self.control_q == other.control_q)
            and (self.projection == other.projection)
            and (self._q_min_value == other._q_min_value)
            and (self._q_max_value == other._q_max_value)
            and (self._s_max == other._s_max)
        )

    @property
    @ureg_wraps("VA", (None,))
    def s_max(self) -> Q_[float]:
        """The apparent power of the flexible load (VA). It is the radius of the feasible circle."""
        return self._s_max

    @s_max.setter
    @ureg_wraps(None, (None, "VA"))
    def s_max(self, value: float | Q_[float]) -> None:
        if value <= 0:
            s_max = Q_(value, "VA")
            msg = f"'s_max' must be greater than 0 but {s_max:P#~} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
        self._s_max = value
        if self._q_max_value is not None and self._q_max_value > self._s_max:
            logger.warning("'s_max' has been updated but now 'q_max' is greater than s_max. 'q_max' is set to s_max")
            self._q_max_value = self._s_max
        if self._q_min_value is not None and self._q_min_value < -self._s_max:
            logger.warning("'s_max' has been updated but now 'q_min' is lower than -s_max. 'q_min' is set to -s_max")
            self._q_min_value = -self._s_max
        if self._cy_fp is not None:
            self._cy_fp.update_parameters(self._s_max, self._q_min, self._q_max)

    @property
    def _q_min(self) -> float:
        return self._q_min_value if self._q_min_value is not None else -self._s_max

    @property
    @ureg_wraps("VAr", (None,))
    def q_min(self) -> Q_[float]:
        """The minimum reactive power of the flexible load (VAr)."""
        return self._q_min

    @q_min.setter
    @ureg_wraps(None, (None, "VAr"))
    def q_min(self, value: float | Q_[float] | None) -> None:
        if value is not None:
            if value < -self._s_max:
                q_min = Q_(value, "VAr")
                msg = f"q_min must be greater than -s_max ({-self.s_max:P#~}) but {q_min:P#~} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
            if value > self._s_max:
                q_min = Q_(value, "VAr")
                msg = f"q_min must be lower than s_max ({self.s_max:P#~}) but {q_min:P#~} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
            if self._q_max_value is not None and value > self._q_max_value:
                q_min = Q_(value, "VAr")
                msg = f"q_min must be lower than q_max ({self.q_max:P#~}) but {q_min:P#~} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
        self._q_min_value = value
        if self._cy_fp is not None:
            self._cy_fp.update_parameters(self._s_max, self._q_min, self._q_max)

    @property
    def _q_max(self) -> float:
        return self._q_max_value if self._q_max_value is not None else self._s_max

    @property
    @ureg_wraps("VAr", (None,))
    def q_max(self) -> Q_[float]:
        """The maximum reactive power of the flexible load (VAr)."""
        return self._q_max

    @q_max.setter
    @ureg_wraps(None, (None, "VAr"))
    def q_max(self, value: float | Q_[float] | None) -> None:
        if value is not None:
            if value > self._s_max:
                q_max = Q_(value, "VAr")
                msg = f"q_max must be lower than s_max ({self.s_max:P#~}) but {q_max:P#~} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
            if value < -self._s_max:
                q_max = Q_(value, "VAr")
                msg = f"q_max must be greater than -s_max ({-self.s_max:P#~}) but {q_max:P#~} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
            if self._q_min_value is not None and value < self._q_min_value:
                q_max = Q_(value, "VAr")
                msg = f"q_max must be greater than q_min ({self.q_min:P#~}) but {q_max:P#~} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
        self._q_max_value = value
        if self._cy_fp is not None:
            self._cy_fp.update_parameters(self._s_max, self._q_min, self._q_max)

    @classmethod
    def constant(cls) -> Self:
        """Build flexible parameters for a constant control with a Euclidean projection.

        Returns:
            A constant control i.e. no control at all. It is an equivalent of the constant power load.
        """
        return cls(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type=Projection._DEFAULT_TYPE),
            s_max=1.0,
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "VA", None, None, None, None, None))
    def p_max_u_production(
        cls,
        u_up: float | Q_[float],
        u_max: float | Q_[float],
        s_max: float | Q_[float],
        alpha_control: float = Control._DEFAULT_ALPHA,
        epsilon_control: float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: float = Projection._DEFAULT_ALPHA,
        epsilon_proj: float = Projection._DEFAULT_EPSILON,
    ) -> Self:
        """Build flexible parameters for production ``P(U)`` control with a Euclidean projection.

        See Also:
            :ref:`$P(U)$ control documentation <models-flexible_load-p_u_control>`

        Args:
            u_up:
                The voltage upper limit value that triggers the control. If the voltage is greater
                than this value, the production active power is reduced.

            u_max:
                The maximum voltage i.e. the one the control reached its maximum action. If the
                voltage is greater than this value, the production active power is reduced to zero.

            s_max:
                The apparent power of the flexible inverter (VA). It is the radius of the feasible
                circle.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            epsilon_control:
                This value is used to make a smooth inverse function for the control.

            type_proj:
                The type of the projection to use.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function (see the diagram above).

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_production" control.
        """
        control_p = Control.p_max_u_production(u_up=u_up, u_max=u_max, alpha=alpha_control, epsilon=epsilon_control)
        return cls(
            control_p=control_p,
            control_q=Control.constant(),
            projection=Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "VA", None, None, None, None, None))
    def p_max_u_consumption(
        cls,
        u_min: float | Q_[float],
        u_down: float | Q_[float],
        s_max: float | Q_[float],
        alpha_control: float = Control._DEFAULT_ALPHA,
        epsilon_control: float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: float = Projection._DEFAULT_ALPHA,
        epsilon_proj: float = Projection._DEFAULT_EPSILON,
    ) -> Self:
        """Build flexible parameters for consumption ``P(U)`` control with a Euclidean projection.

        See Also:
            :ref:`$P(U)$ control documentation <models-flexible_load-p_u_control>`

        Args:
            u_min:
                The minimum voltage i.e. the one the control reached the maximum action.

            u_down:
                The voltage which starts to trigger the control (lower value).

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible circle.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            epsilon_control:
                This value is used to make a smooth inverse function for the control.

            type_proj:
                The type of the projection to use.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_consumption" control.
        """
        control_p = Control.p_max_u_consumption(
            u_min=u_min, u_down=u_down, alpha=alpha_control, epsilon=epsilon_control
        )
        return cls(
            control_p=control_p,
            control_q=Control.constant(),
            projection=Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "V", "V", "VA", "VAr", "VAr", None, None, None, None))
    def q_u(
        cls,
        u_min: float | Q_[float],
        u_down: float | Q_[float],
        u_up: float | Q_[float],
        u_max: float | Q_[float],
        s_max: float | Q_[float],
        q_min: float | Q_[float] | None = None,
        q_max: float | Q_[float] | None = None,
        alpha_control: float = Control._DEFAULT_ALPHA,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: float = Projection._DEFAULT_ALPHA,
        epsilon_proj: float = Projection._DEFAULT_EPSILON,
    ) -> Self:
        """Build flexible parameters for ``Q(U)`` control with a Euclidean projection.

        See Also:
            :ref:`$Q(U)$ control documentation <models-flexible_load-q_u_control>`

        Args:
            u_min:
                The minimum voltage i.e. the one the control reached the maximum action.

            u_down:
                The voltage which starts to trigger the control (lower value).

            u_up:
                The voltage  which starts to trigger the control (upper value).

            u_max:
                The maximum voltage i.e. the one the control reached its maximum action.

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible
                circle.

            q_min:
                The minimum reactive power of the flexible load (VAr). By default, it is equal to -s_max, but it can
                be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default, it is equal to s_max, but it can
                be further constrained.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            type_proj:
                The type of the projection to use.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "q_u" control.
        """
        control_q = Control.q_u(u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha_control)
        return cls(
            control_p=Control.constant(),
            control_q=control_q,
            projection=Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
            q_min=q_min,
            q_max=q_max,
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "V", "V", "V", "V", "VA", "VAr", "VAr", None, None, None, None, None))
    def pq_u_production(
        cls,
        up_up: float | Q_[float],
        up_max: float | Q_[float],
        uq_min: float | Q_[float],
        uq_down: float | Q_[float],
        uq_up: float | Q_[float],
        uq_max: float | Q_[float],
        s_max: float | Q_[float],
        q_min: float | Q_[float] | None = None,
        q_max: float | Q_[float] | None = None,
        alpha_control: float = Control._DEFAULT_ALPHA,
        epsilon_control: float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: float = Projection._DEFAULT_ALPHA,
        epsilon_proj: float = Projection._DEFAULT_EPSILON,
    ) -> Self:
        """Build flexible parameters for production ``P(U)`` control and ``Q(U)`` control with a
        Euclidean projection.

        Args:
            up_up:
                The voltage  which starts to trigger the control on the production (upper value).

            up_max:
                The maximum voltage i.e. the one the control (of production) reached its maximum
                action.

            uq_min:
                The minimum voltage i.e. the one the control reached the maximum action (reactive
                power control)

            uq_down:
                The voltage which starts to trigger the reactive power control (lower value).

            uq_up:
                The voltage  which starts to trigger the reactive power control (upper value).

            uq_max:
                The maximum voltage i.e. the one the reactive power control reached its maximum
                action.

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible
                circle.

            q_min:
                The minimum reactive power of the flexible load (VAr). By default, it is equal to -s_max, but it can
                be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default, it is equal to s_max, but it can
                be further constrained.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            epsilon_control:
                This value is used to make a smooth inverse function for the control.

            type_proj:
                The type of the projection to use.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_production" control and a "q_u" control.

        See Also:
            :meth:`p_max_u_production` and :meth:`q_u` for more details.
        """
        control_p = Control.p_max_u_production(u_up=up_up, u_max=up_max, alpha=alpha_control, epsilon=epsilon_control)
        control_q = Control.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
            q_min=q_min,
            q_max=q_max,
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "V", "V", "V", "V", "VA", "VAr", "VAr", None, None, None, None, None))
    def pq_u_consumption(
        cls,
        up_min: float | Q_[float],
        up_down: float | Q_[float],
        uq_min: float | Q_[float],
        uq_down: float | Q_[float],
        uq_up: float | Q_[float],
        uq_max: float | Q_[float],
        s_max: float | Q_[float],
        q_min: float | Q_[float] | None = None,
        q_max: float | Q_[float] | None = None,
        alpha_control: float = Control._DEFAULT_ALPHA,
        epsilon_control: float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: float = Projection._DEFAULT_ALPHA,
        epsilon_proj: float = Projection._DEFAULT_EPSILON,
    ) -> Self:
        """Build flexible parameters for consumption ``P(U)`` control and ``Q(U)`` control with a
        Euclidean projection.

        Args:
            up_min:
                The minimum voltage i.e. the one the active power control reached the maximum
                action.

            up_down:
                The voltage which starts to trigger the active power control (lower value).

            uq_min:
                The minimum voltage i.e. the one the control reached the maximum action (reactive
                power control)

            uq_down:
                The voltage which starts to trigger the reactive power control (lower value).

            uq_up:
                The voltage  which starts to trigger the reactive power control (upper value).

            uq_max:
                The maximum voltage i.e. the one the reactive power control reached its maximum
                action.

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible
                circle.

            q_min:
                The minimum reactive power of the flexible load (VAr). By default, it is equal to -s_max, but it can
                be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default, it is equal to s_max, but it can
                be further constrained.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            epsilon_control:
                This value is used to make a smooth inverse function for the control.

            type_proj:
                The type of the projection to use.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_consumption" control and "q_u" control.

        See Also:
            :meth:`p_max_u_consumption` and :meth:`q_u` for more details.
        """
        control_p = Control.p_max_u_consumption(
            u_min=up_min, u_down=up_down, alpha=alpha_control, epsilon=epsilon_control
        )
        control_q = Control.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
            q_min=q_min,
            q_max=q_max,
        )

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        control_p = Control.from_dict(data=data["control_p"], include_results=include_results)
        control_q = Control.from_dict(data=data["control_q"], include_results=include_results)
        projection = Projection.from_dict(data=data["projection"], include_results=include_results)
        q_min = data.get("q_min", None)
        q_max = data.get("q_max", None)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=projection,
            s_max=data["s_max"],
            q_min=q_min,
            q_max=q_max,
        )

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {
            "control_p": self.control_p.to_dict(include_results=include_results),
            "control_q": self.control_q.to_dict(include_results=include_results),
            "projection": self.projection.to_dict(include_results=include_results),
            "s_max": self._s_max,
        }
        if self._q_min_value is not None:
            res["q_min"] = self._q_min_value
        if self._q_max_value is not None:
            res["q_max"] = self._q_max_value
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    #
    # Equivalent Python method
    #
    @ureg_wraps("VA", (None, "V", "VA"))
    def compute_powers(self, voltages: ComplexArrayLike1D, power: complex | Q_[complex]) -> Q_[ComplexArray]:
        """Compute the flexible powers for different voltages (norms)

        Args:
            voltages:
                The array of voltage norms to test with this flexible parameter.

            power:
                The input theoretical power of the load.

        Returns:
            The flexible powers really consumed taking into account the control. One value per provided voltage norm.
        """
        return self._compute_powers(voltages=np.abs(np.array(voltages, dtype=complex)), power=power)

    def _compute_powers(self, voltages: FloatArrayLike1D, power: complex) -> ComplexArray:
        # Iterate over the provided voltages to get the associated flexible powers
        res_flexible_powers = [self._cy_fp.compute_power(v, power) for v in voltages]
        return np.array(res_flexible_powers, dtype=complex)

    @ureg_wraps((None, "VA"), (None, "V", "VA", None, None))
    def plot_pq(
        self,
        voltages: FloatArrayLike1D,
        power: complex | Q_[complex],
        ax: "Axes | None" = None,
        voltages_labels_mask: NDArray[np.bool_] | None = None,
    ) -> tuple["Axes", ComplexArray]:
        """Plot the "trajectory" of the flexible powers (in the (P, Q) plane) for the provided voltages and theoretical
        power.

        Args:
            voltages:
                Array-like of voltage norms to test with this flexible parameter.

            power:
                The input theoretical power of the load.

            ax:
                The optional axis to use for the plot. The current axis is used by default.

            voltages_labels_mask:
                A mask to activate the plot of voltages labels. By default, no voltages annotations.

        Returns:
            The axis on which the plot has been drawn and the resulting flexible powers (the input if not `None` else
            the computed values).
        """
        plt = _optional_deps.pyplot  # this line first for better error handling
        from matplotlib import colormaps, patheffects

        # Get the axes
        if ax is None:
            ax = plt.gca()

        voltages = np.array(voltages, dtype=np.float64)

        # Initialise some variables
        if voltages_labels_mask is None:
            voltages_labels_mask = np.zeros_like(voltages, dtype=np.bool_)
        else:
            voltages_labels_mask = np.array(voltages_labels_mask, dtype=np.bool_)
        s_max = self._s_max
        v_min = voltages.min()
        v_max = voltages.max()

        # Compute the powers for the voltages norms
        res_flexible_powers = self._compute_powers(voltages=voltages, power=power)

        # Draw a circle
        circle = plt.Circle((0, 0), radius=s_max, color="black", fill=False)
        ax.add_artist(circle)

        # Draw the powers
        cm = colormaps.get_cmap("Spectral_r")
        sc = ax.scatter(
            x=res_flexible_powers.real,
            y=res_flexible_powers.imag,
            c=voltages,
            cmap=cm,
            vmin=v_min,
            vmax=v_max,
            marker=".",
            s=50,
            zorder=4,
        )
        for m, v, x, y in zip(
            voltages_labels_mask, voltages, res_flexible_powers.real, res_flexible_powers.imag, strict=True
        ):
            if not m:
                continue
            ax.annotate(
                text=f"{v:.1f} V",
                xy=(x, y),
                xycoords="data",
                path_effects=[patheffects.withStroke(linewidth=2, foreground="w")],
                xytext=(4, 4),
                textcoords="offset points",
            )

        # Draw the theoretical power
        ax.axhline(y=power.imag, c="red", zorder=1.9)
        ax.axvline(x=power.real, c="red", zorder=1.9)
        ax.scatter(x=power.real, y=power.imag, marker=".", c="red", zorder=3)
        ax.annotate(
            xy=(power.real, power.imag),
            text=r"$S^{\mathrm{th.}}$",
            path_effects=[patheffects.withStroke(linewidth=2, foreground="w")],
            ha="right",
        )

        # Refine the axes
        ax.grid(visible=True)
        plt.colorbar(sc, ax=ax)
        ax.set_xlim(-s_max * 1.05, s_max * 1.05)
        ax.set_ylim(-s_max * 1.05, s_max * 1.05)
        ax.set_aspect("equal")
        ax.set_xlabel("Active power (W)")
        ax.set_ylabel("Reactive power (VAr)")

        return ax, res_flexible_powers

    @ureg_wraps((None, "VA"), (None, "V", "VA", None))
    def plot_control_p(
        self, voltages: FloatArrayLike1D, power: complex | Q_[complex], ax: "Axes | None" = None
    ) -> tuple["Axes", ComplexArray]:
        """Plot the flexible active power consumed (or produced) for the provided voltages and theoretical power.

        Args:
            voltages:
                Array-like of voltage norms to test with this flexible parameter.

            power:
                The input theoretical power of the load.

            ax:
                The optional axis to use for the plot. The current axis is used by default.

        Returns:
            The axis on which the plot has been drawn and the resulting flexible powers (the input if not `None` else
            the computed values).
        """
        plt = _optional_deps.pyplot

        # Get the axes
        if ax is None:
            ax = plt.gca()

        voltages = np.array(voltages, dtype=np.float64)

        # Depending on the type of the control, several options
        x, y, x_ticks = self._theoretical_control_data(
            control=self.control_p, v_min=voltages.min(), v_max=voltages.max(), power=power.real, s_max=self._s_max
        )

        # Compute the powers for the voltages norms
        res_flexible_powers = self._compute_powers(voltages=voltages, power=power)
        ax.scatter(voltages, res_flexible_powers.real, marker=".", c="blue", zorder=2, label="Actual power")

        # Add the theoretical non-smooth curve
        ax.plot(x, y, marker="s", c="red", zorder=1.9, label="Non-smooth theoretical control")

        # Refine the axis
        ax.grid(visible=True)
        ax.set_xticks(x, x_ticks)
        ax.set_xlabel("Voltage (V)")
        ax.set_ylabel("Active power (W)")
        ax.legend()
        ax.figure.tight_layout()

        return ax, res_flexible_powers

    @ureg_wraps((None, "VA"), (None, "V", "VA", None))
    def plot_control_q(
        self, voltages: FloatArrayLike1D, power: complex | Q_[complex], ax: "Axes | None" = None
    ) -> tuple["Axes", ComplexArray]:
        """Plot the flexible reactive power consumed (or produced) for the provided voltages and theoretical power.

        Args:
            voltages:
                Array-like of voltage norms to test with this flexible parameter.

            power:
                The input theoretical power of the load.

            ax:
                The optional axis to use for the plot. The current axis is used by default.

        Returns:
            The axis on which the plot has been drawn and the resulting flexible powers (the input if not `None` else
            the computed values).
        """
        plt = _optional_deps.pyplot

        # Get the axes
        if ax is None:
            ax = plt.gca()

        voltages = np.array(voltages, dtype=np.float64)

        # Depending on the type of the control, several options
        x, y, x_ticks = self._theoretical_control_data(
            control=self.control_q, v_min=voltages.min(), v_max=voltages.max(), power=power.imag, s_max=self._s_max
        )

        # Compute the powers for the voltages norms
        res_flexible_powers = self._compute_powers(voltages=voltages, power=power)
        ax.scatter(voltages, res_flexible_powers.imag, marker=".", c="blue", zorder=2, label="Actual power")

        # Add the theoretical non-smooth curve
        ax.plot(x, y, marker="s", c="red", zorder=1.9, label="Non-smooth theoretical control")

        # Refine the axis
        ax.grid(visible=True)
        ax.set_xticks(x, x_ticks)
        ax.set_xlabel("Voltage (V)")
        ax.set_ylabel("Reactive power (VAr)")
        ax.legend()
        ax.figure.tight_layout()

        return ax, res_flexible_powers

    #
    # Helpers
    #
    @staticmethod
    def _theoretical_control_data(
        control: Control, v_min: float, v_max: float, power: float, s_max: float
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.object_]]:
        """Helper to get data for the different plots of the class. It provides the theoretical control curve
        abscissas and ordinates values. It also provides ticks for the abscissa axis.

        Args:
            control:
                The control to extract the theoretical value.

            v_min:
                The minimum voltage norm provided by the user in the `voltages` array.

            v_max:
                The maximum voltage norm provided by the user in the `voltages` array.

            power:
                The active (or reactive, depending on the provided control) to use in the constant  control.

            s_max:
                The `s_max` parameter to scale the control functions.

        Returns:
            The x- and y-values of the theoretical control function with x-ticks to use for the plot.
        """
        # Depending on the type of the control, several options
        if control.type == "constant":
            x = np.array([v_min, v_max], dtype=np.float64)
            y = np.array([power, power], dtype=np.float64)
            x_ticks = np.array([f"{v_min:.1f}", f"{v_max:.1f}"], dtype=np.object_)
        elif control.type == "p_max_u_production":
            u_up = control._u_up
            u_max = control._u_max
            x = np.array([u_up, u_max, v_min, v_max], dtype=np.float64)
            y = np.zeros_like(x, dtype=np.float64)
            y[x < u_up] = -s_max
            mask = np.logical_and(u_up <= x, x < u_max)
            y[mask] = -s_max * (x[mask] - u_max) / (u_up - u_max)
            y[x >= u_max] = 0
            x_ticks = np.array(
                [f"{u_up:.1f}\n$U^{{\\mathrm{{up}}}}$", f"{u_max:.1f}\n$U^{{\\max}}$", f"{v_min:.1f}", f"{v_max:.1f}"],
                dtype=np.object_,
            )
        elif control.type == "p_max_u_consumption":
            u_min = control._u_min
            u_down = control._u_down
            x = np.array([u_min, u_down, v_min, v_max], dtype=np.float64)
            y = np.zeros_like(x, dtype=np.float64)
            y[x < u_min] = 0
            y[x >= u_down] = s_max
            mask = np.logical_and(u_min <= x, x < u_down)
            y[mask] = s_max * (x[mask] - u_min) / (u_down - u_min)
            x_ticks = np.array(
                [
                    f"{u_min:.1f}\n$U^{{\\min}}$",
                    f"{u_down:.1f}\n$U^{{\\mathrm{{down}}}}$",
                    f"{v_min:.1f}",
                    f"{v_max:.1f}",
                ],
                dtype=np.object_,
            )
        elif control.type == "q_u":
            u_min = control._u_min
            u_down = control._u_down
            u_up = control._u_up
            u_max = control._u_max
            x = np.array([u_min, u_down, u_up, u_max, v_min, v_max], dtype=np.float64)
            y = np.zeros_like(x, dtype=np.float64)
            y[x < u_min] = -s_max
            mask = np.logical_and(u_min <= x, x < u_down)
            y[mask] = -s_max * (x[mask] - u_down) / (u_min - u_down)
            y[np.logical_and(u_down <= x, x < u_up)] = 0
            mask = np.logical_and(u_up <= x, x < u_max)
            y[mask] = s_max * (x[mask] - u_up) / (u_max - u_up)
            y[x >= u_max] = s_max
            x_ticks = np.array(
                [
                    f"{u_min:.1f}\n$U^{{\\min}}$",
                    f"{u_down:.1f}\n$U^{{\\mathrm{{down}}}}$",
                    f"{u_up:.1f}\n$U^{{\\mathrm{{up}}}}$",
                    f"{u_max:.1f}\n$U^{{\\max}}$",
                    f"{v_min:.1f}",
                    f"{v_max:.1f}",
                ],
                dtype=np.object_,
            )
        else:  # pragma: no-cover
            msg = f"Unsupported control type {control.type!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE)

        # Sort everything according to the voltages
        sort_index = np.argsort(x)
        x = x[sort_index]
        y = y[sort_index]
        x_ticks = x_ticks[sort_index]

        return x, y, x_ticks
