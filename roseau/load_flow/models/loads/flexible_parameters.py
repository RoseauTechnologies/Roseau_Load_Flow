import logging
import warnings
from typing import NoReturn

import numpy as np
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import ControlType, JsonDict, ProjectionType
from roseau.load_flow.units import Q_, ureg
from roseau.load_flow.utils import JsonMixin

logger = logging.getLogger(__name__)


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

    See Also:
        :ref:`Control documentation <models-flexible_load-controls>`
    """

    DEFAULT_ALPHA: float = 1000.0

    @ureg.wraps(None, (None, None, "V", "V", "V", "V", None), strict=False)
    def __init__(
        self,
        type: ControlType,
        u_min: float,
        u_down: float,
        u_up: float,
        u_max: float,
        alpha: float = DEFAULT_ALPHA,
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
        """
        self.type = type
        self._u_min = u_min
        self._u_down = u_down
        self._u_up = u_up
        self._u_max = u_max
        self._alpha = alpha
        self._check_values()

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

        # Check on alpha
        if self._alpha <= 0:
            msg = f"'alpha' must be greater than 0 but {self._alpha:.1f} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE)

    @property
    @ureg.wraps("V", (None,), strict=False)
    def u_min(self) -> Q_[float]:
        """The minimum voltage i.e. the one the control reached the maximum action."""
        return self._u_min

    @property
    @ureg.wraps("V", (None,), strict=False)
    def u_down(self) -> Q_[float]:
        """The voltage which starts to trigger the control (lower value)."""
        return self._u_down

    @property
    @ureg.wraps("V", (None,), strict=False)
    def u_up(self) -> Q_[float]:
        """TThe voltage  which starts to trigger the control (upper value)."""
        return self._u_up

    @property
    @ureg.wraps("V", (None,), strict=False)
    def u_max(self) -> Q_[float]:
        """The maximum voltage i.e. the one the control reached its maximum action."""
        return self._u_max

    @property
    def alpha(self) -> float:
        """An approximation factor used by the family function (soft clip). The bigger the factor is the closer the
        function is to the non-differentiable function."""
        return self._alpha

    @classmethod
    def constant(cls) -> Self:
        """Create a constant control i.e no control."""
        return cls(type="constant", u_min=0.0, u_down=0.0, u_up=0.0, u_max=0.0)

    @classmethod
    @ureg.wraps(None, (None, "V", "V", None), strict=False)
    def p_max_u_production(cls, u_up: float, u_max: float, alpha: float = DEFAULT_ALPHA) -> Self:
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

        Returns:
            The ``"p_max_u_production"`` control using the provided parameters.
        """
        return cls(type="p_max_u_production", u_min=0.0, u_down=0.0, u_up=u_up, u_max=u_max, alpha=alpha)

    @classmethod
    @ureg.wraps(None, (None, "V", "V", None), strict=False)
    def p_max_u_consumption(cls, u_min: float, u_down: float, alpha: float = DEFAULT_ALPHA) -> Self:
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

        Returns:
            The ``"p_max_u_consumption"`` control using the provided parameters.
        """
        return cls(type="p_max_u_consumption", u_min=u_min, u_down=u_down, u_up=0.0, u_max=0.0, alpha=alpha)

    @classmethod
    @ureg.wraps(None, (None, "V", "V", "V", "V", None), strict=False)
    def q_u(cls, u_min: float, u_down: float, u_up: float, u_max: float, alpha: float = DEFAULT_ALPHA) -> Self:
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
    def from_dict(cls, data: JsonDict) -> Self:
        alpha = data["alpha"] if "alpha" in data else cls.DEFAULT_ALPHA
        if data["type"] == "constant":
            return cls.constant()
        elif data["type"] == "p_max_u_production":
            return cls.p_max_u_production(u_up=data["u_up"], u_max=data["u_max"], alpha=alpha)
        elif data["type"] == "p_max_u_consumption":
            return cls.p_max_u_consumption(u_min=data["u_min"], u_down=data["u_down"], alpha=alpha)
        elif data["type"] == "q_u":
            return cls.q_u(
                u_min=data["u_min"], u_down=data["u_down"], u_up=data["u_up"], u_max=data["u_max"], alpha=alpha
            )
        else:
            msg = f"Unsupported control type {data['type']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE)

    def to_dict(self, geometry: bool = True) -> JsonDict:
        if self.type == "constant":
            return {"type": "constant"}
        elif self.type == "p_max_u_production":
            return {"type": "p_max_u_production", "u_up": self._u_up, "u_max": self._u_max, "alpha": self._alpha}
        elif self.type == "p_max_u_consumption":
            return {"type": "p_max_u_consumption", "u_min": self._u_min, "u_down": self._u_down, "alpha": self._alpha}
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

    def _results_to_dict(self, warning: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    def results_from_dict(self, data: JsonDict) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to import."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)


class Projection(JsonMixin):
    """This class defines the projection on the feasible circle for a flexible load.

    The three possible projection types are:
        * ``"euclidean"``: for an Euclidean projection on the feasible space;
        * ``"keep_p"``: for maintaining a constant P;
        * ``"keep_q"``: for maintaining a constant Q.

    See Also:
        :ref:`Projection documentation <models-flexible_load-projection>`
    """

    DEFAULT_ALPHA: float = 1000.0
    DEFAULT_EPSILON: float = 1e-8

    def __init__(self, type: ProjectionType, alpha: float = DEFAULT_ALPHA, epsilon: float = DEFAULT_EPSILON) -> None:
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
    def from_dict(cls, data: JsonDict) -> Self:
        alpha = data["alpha"] if "alpha" in data else cls.DEFAULT_ALPHA
        epsilon = data["epsilon"] if "epsilon" in data else cls.DEFAULT_EPSILON
        return cls(type=data["type"], alpha=alpha, epsilon=epsilon)

    def to_dict(self, geometry: bool = True) -> JsonDict:
        return {"type": self.type, "alpha": self._alpha, "epsilon": self._epsilon}

    def _results_to_dict(self, warning: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    def results_from_dict(self, data: JsonDict) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to import."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)


class FlexibleParameter(JsonMixin):
    """Flexible parameters of a flexible load.

    This class encapsulate single-phase flexibility information of a flexible load:

        * The active power :class:`Control` to apply;
        * The reactive power :class:`Control` to apply;
        * The :class:`Projection` to use when dealing with voltage violations;
        * The apparent power of the flexible load (VA). This is the maximum power the load can consume/produce. It is
            the radius of the feasible circle used by the projection

    For multi-phase loads, you need to use a `FlexibleParameter` instance per phase.

    See Also:
        :ref:`Flexible Parameters documentation <models-flexible_load-flexible_parameters>`
    """

    _control_class: type[Control] = Control
    _projection_class: type[Projection] = Projection

    @ureg.wraps(None, (None, None, None, None, "VA"), strict=False)
    def __init__(self, control_p: Control, control_q: Control, projection: Projection, s_max: float) -> None:
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
        """
        self.control_p = control_p
        self.control_q = control_q
        self.projection = projection
        self._s_max = s_max
        self._check_values()

    def _check_values(self) -> None:
        """Check the provided values."""
        if self._s_max <= 0:
            msg = f"'s_max' must be greater than 0 but {self.s_max:P#~} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SMAX_VALUE)

    @property
    @ureg.wraps("VA", (None,), strict=False)
    def s_max(self) -> Q_[float]:
        """The apparent power of the flexible load (VA). It is the radius of the feasible circle."""
        return self._s_max

    @classmethod
    def constant(cls) -> Self:
        """Build flexible parameters for a constant control with a Euclidean projection.

        Returns:
            A constant control i.e. no control at all. It is an equivalent of the constant power
            load.
        """
        return cls(
            control_p=cls._control_class.constant(),
            control_q=cls._control_class.constant(),
            projection=cls._projection_class(type="euclidean"),
            s_max=1.0,
        )

    @classmethod
    @ureg.wraps(None, (None, "V", "V", "VA", None, None, None), strict=False)
    def p_max_u_production(
        cls,
        u_up: float,
        u_max: float,
        s_max: float,
        alpha_control: float = Control.DEFAULT_ALPHA,
        alpha_proj: float = Projection.DEFAULT_ALPHA,
        epsilon_proj: float = Projection.DEFAULT_EPSILON,
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

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function (see the diagram above).

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_production" control.
        """
        control_p = cls._control_class.p_max_u_production(u_up=u_up, u_max=u_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=cls._control_class.constant(),
            projection=cls._projection_class(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
    @ureg.wraps(None, (None, "V", "V", "VA", None, None, None), strict=False)
    def p_max_u_consumption(
        cls,
        u_min: float,
        u_down: float,
        s_max: float,
        alpha_control: float = Control.DEFAULT_ALPHA,
        alpha_proj: float = Projection.DEFAULT_ALPHA,
        epsilon_proj: float = Projection.DEFAULT_EPSILON,
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

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_consumption" control.
        """
        control_p = cls._control_class.p_max_u_consumption(u_min=u_min, u_down=u_down, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=cls._control_class.constant(),
            projection=cls._projection_class("euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
    @ureg.wraps(None, (None, "V", "V", "V", "V", "VA", None, None, None), strict=False)
    def q_u(
        cls,
        u_min: float,
        u_down: float,
        u_up: float,
        u_max: float,
        s_max: float,
        alpha_control: float = Control.DEFAULT_ALPHA,
        alpha_proj: float = Projection.DEFAULT_ALPHA,
        epsilon_proj: float = Projection.DEFAULT_EPSILON,
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

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "q_u" control.
        """
        control_q = cls._control_class.q_u(u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha_control)
        return cls(
            control_p=cls._control_class.constant(),
            control_q=control_q,
            projection=cls._projection_class(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
    @ureg.wraps(None, (None, "V", "V", "V", "V", "V", "V", "VA", None, None, None), strict=False)
    def pq_u_production(
        cls,
        up_up: float,
        up_max: float,
        uq_min: float,
        uq_down: float,
        uq_up: float,
        uq_max: float,
        s_max: float,
        alpha_control=Control.DEFAULT_ALPHA,
        alpha_proj=Projection.DEFAULT_ALPHA,
        epsilon_proj=Projection.DEFAULT_EPSILON,
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

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_production" control and a "q_u" control.

        .. seealso::
            :meth:`p_max_u_production` and :meth:`q_u` for more details.
        """
        control_p = cls._control_class.p_max_u_production(u_up=up_up, u_max=up_max, alpha=alpha_control)
        control_q = cls._control_class.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=cls._projection_class(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
    @ureg.wraps(None, (None, "V", "V", "V", "V", "V", "V", "VA", None, None, None), strict=False)
    def pq_u_consumption(
        cls,
        up_min: float,
        up_down: float,
        uq_min: float,
        uq_down: float,
        uq_up: float,
        uq_max: float,
        s_max: float,
        alpha_control: float = Control.DEFAULT_ALPHA,
        alpha_proj: float = Projection.DEFAULT_ALPHA,
        epsilon_proj: float = Projection.DEFAULT_EPSILON,
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

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the
                closer the function are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection
                function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean
                projection.

        Returns:
            A flexible parameter which performs "p_max_u_consumption" control and "q_u" control.

        .. seealso::
            :meth:`p_max_u_consumption` and :meth:`q_u` for more details.
        """
        control_p = cls._control_class.p_max_u_consumption(u_min=up_min, u_down=up_down, alpha=alpha_control)
        control_q = cls._control_class.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=cls._projection_class(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        control_p = cls._control_class.from_dict(data["control_p"])
        control_q = cls._control_class.from_dict(data["control_q"])
        projection = cls._projection_class.from_dict(data["projection"])
        return cls(control_p=control_p, control_q=control_q, projection=projection, s_max=data["s_max"])

    def to_dict(self, geometry: bool = True) -> JsonDict:
        return {
            "control_p": self.control_p.to_dict(),
            "control_q": self.control_q.to_dict(),
            "projection": self.projection.to_dict(),
            "s_max": self._s_max,
        }

    def _results_to_dict(self, warning: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    def results_from_dict(self, data: JsonDict) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to import."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)
