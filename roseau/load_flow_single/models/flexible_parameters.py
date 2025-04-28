import logging
from collections.abc import Iterable
from typing import Self

import numpy as np

from roseau.load_flow import SQRT3, Projection, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow import Control as MultiControl
from roseau.load_flow import FlexibleParameter as MultiFlexibleParameter
from roseau.load_flow.typing import ComplexArray, ControlType, Float, ProjectionType
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyControl, CyFlexibleParameter

logger = logging.getLogger(__name__)


class Control(MultiControl):
    """Control class for flexible loads.

    This class contains the information needed to formulate the control equations. This includes the
    control type, control limits, and other factors.

    The control for a :class:`PowerLoad` instance can be of four possible types:
        * ``"constant"``: no control is applied. In this case, a simple :class:`PowerLoad` without
          `flexible_params` could have been used instead.
        * ``"p_max_u_production"``: control the maximum production active power of the load
          (inverter) based on the voltage :math:`P^{\\max}_{\\mathrm{prod}}(U)`.

        * ``"p_max_u_consumption"``: control the maximum consumption active power of the load based
          on the voltage :math:`P^{\\max}_{\\mathrm{cons}}(U)`.

        * ``"q_u"``: control the reactive power based on the voltage :math:`Q(U)`.
    """

    @ureg_wraps(None, (None, None, "V", "V", "V", "V", None, None))
    def __init__(
        self,
        type: ControlType,
        u_min: Float | Q_[Float],
        u_down: Float | Q_[Float],
        u_up: Float | Q_[Float],
        u_max: Float | Q_[Float],
        alpha: Float = MultiControl._DEFAULT_ALPHA,
        epsilon: Float = MultiControl._DEFAULT_EPSILON,
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
        super().__init__(type=type, u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha, epsilon=epsilon)
        self._cy_control = CyControl(
            t=self._type,
            u_min=self._u_min / SQRT3,
            u_down=self._u_down / SQRT3,
            u_up=self._u_up / SQRT3,
            u_max=self._u_max / SQRT3,
            alpha=self._alpha,
            epsilon=self._epsilon,
        )


class FlexibleParameter(MultiFlexibleParameter):
    """Flexible parameters of a flexible load.

    This class encapsulate single-phase flexibility information of a flexible load:

    * The active power :class:`roseau.load_flow_single.models.Control` to apply;
    * The reactive power :class:`roseau.load_flow_single.models.Control` to apply;
    * The :class:`Projection` to use when dealing with voltage violations;
    * The apparent power of the flexible load (VA). This is the maximum power the load can
      consume/produce. It is the radius of the feasible circle used by the projection
    """

    @ureg_wraps(None, (None, None, None, None, "VA", "VAr", "VAr"))
    def __init__(
        self,
        control_p: Control,
        control_q: Control,
        projection: Projection,
        s_max: Float | Q_[Float],
        q_min: Float | Q_[Float] | None = None,
        q_max: Float | Q_[Float] | None = None,
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
                The minimum reactive power of the flexible load (VAr). By default it is equal to
                `-s_max`, but it can be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default it is equal to
                `s_max`, but it can be further constrained.
        """
        super().__init__(
            control_p=control_p, control_q=control_q, projection=projection, s_max=s_max, q_min=q_min, q_max=q_max
        )
        self._cy_fp = CyFlexibleParameter(
            control_p=control_p._cy_control,
            control_q=control_q._cy_control,
            projection=projection._cy_projection,
            s_max=self._s_max / 3.0,
            q_min=self._q_min / 3.0,
            q_max=self._q_max / 3.0,
        )

    @property
    @ureg_wraps("VA", (None,))
    def s_max(self) -> Q_[float]:
        """The apparent power of the flexible load (VA). It is the radius of the feasible circle."""
        return self._s_max  # type: ignore

    @s_max.setter
    @ureg_wraps(None, (None, "VA"))
    def s_max(self, value: Float | Q_[Float]) -> None:
        if value <= 0:
            s_max = Q_(value, "VA")
            msg = f"'s_max' must be greater than 0 but {s_max:P#~} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE)
        self._s_max = float(value)
        if self._q_max_value is not None and self._q_max_value > self._s_max:
            logger.warning("'s_max' has been updated but now 'q_max' is greater than s_max. 'q_max' is set to s_max")
            self._q_max_value = self._s_max
        if self._q_min_value is not None and self._q_min_value < -self._s_max:
            logger.warning("'s_max' has been updated but now 'q_min' is lower than -s_max. 'q_min' is set to -s_max")
            self._q_min_value = -self._s_max
        if self._cy_fp is not None:
            self._cy_fp.update_parameters(self._s_max / 3.0, self._q_min / 3.0, self._q_max / 3.0)

    @property
    def _q_min(self) -> float:
        return self._q_min_value if self._q_min_value is not None else -self._s_max

    @property
    @ureg_wraps("VAr", (None,))
    def q_min(self) -> Q_[float]:
        """The minimum reactive power of the flexible load (VAr)."""
        return self._q_min  # type: ignore

    @q_min.setter
    @ureg_wraps(None, (None, "VAr"))
    def q_min(self, value: Float | Q_[Float] | None) -> None:
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
            value = float(value)
        self._q_min_value = value
        if self._cy_fp is not None:
            self._cy_fp.update_parameters(self._s_max / 3.0, self._q_min / 3.0, self._q_max / 3.0)

    @property
    def _q_max(self) -> float:
        return self._q_max_value if self._q_max_value is not None else self._s_max

    @property
    @ureg_wraps("VAr", (None,))
    def q_max(self) -> Q_[float]:
        """The maximum reactive power of the flexible load (VAr)."""
        return self._q_max  # type: ignore

    @q_max.setter
    @ureg_wraps(None, (None, "VAr"))
    def q_max(self, value: Float | Q_[Float] | None) -> None:
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
            value = float(value)
        self._q_max_value = value
        if self._cy_fp is not None:
            self._cy_fp.update_parameters(self._s_max / 3.0, self._q_min / 3.0, self._q_max / 3.0)

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
        u_up: Float | Q_[Float],
        u_max: Float | Q_[Float],
        s_max: Float | Q_[Float],
        alpha_control: Float = Control._DEFAULT_ALPHA,
        epsilon_control: Float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: Float = Projection._DEFAULT_ALPHA,
        epsilon_proj: Float = Projection._DEFAULT_EPSILON,
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
        control_q = Control.constant()
        projection = Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj)
        return cls(control_p=control_p, control_q=control_q, projection=projection, s_max=s_max)

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "VA", None, None, None, None, None))
    def p_max_u_consumption(
        cls,
        u_min: Float | Q_[Float],
        u_down: Float | Q_[Float],
        s_max: Float | Q_[Float],
        alpha_control: Float = Control._DEFAULT_ALPHA,
        epsilon_control: Float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: Float = Projection._DEFAULT_ALPHA,
        epsilon_proj: Float = Projection._DEFAULT_EPSILON,
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
        control_q = Control.constant()
        projection = Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj)
        return cls(control_p=control_p, control_q=control_q, projection=projection, s_max=s_max)

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "V", "V", "VA", "VAr", "VAr", None, None, None, None))
    def q_u(
        cls,
        u_min: Float | Q_[Float],
        u_down: Float | Q_[Float],
        u_up: Float | Q_[Float],
        u_max: Float | Q_[Float],
        s_max: Float | Q_[Float],
        q_min: Float | Q_[Float] | None = None,
        q_max: Float | Q_[Float] | None = None,
        alpha_control: Float = Control._DEFAULT_ALPHA,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: Float = Projection._DEFAULT_ALPHA,
        epsilon_proj: Float = Projection._DEFAULT_EPSILON,
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
                The minimum reactive power of the flexible load (VAr). By default it is equal to
                `-s_max`, but it can be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default it is equal to
                `s_max`, but it can be further constrained.

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
        control_p = Control.constant()
        control_q = Control.q_u(u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha_control)
        projection = Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=projection,
            s_max=s_max,
            q_min=q_min,
            q_max=q_max,
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "V", "V", "V", "V", "VA", "VAr", "VAr", None, None, None, None, None))
    def pq_u_production(
        cls,
        up_up: Float | Q_[Float],
        up_max: Float | Q_[Float],
        uq_min: Float | Q_[Float],
        uq_down: Float | Q_[Float],
        uq_up: Float | Q_[Float],
        uq_max: Float | Q_[Float],
        s_max: Float | Q_[Float],
        q_min: Float | Q_[Float] | None = None,
        q_max: Float | Q_[Float] | None = None,
        alpha_control: Float = Control._DEFAULT_ALPHA,
        epsilon_control: Float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: Float = Projection._DEFAULT_ALPHA,
        epsilon_proj: Float = Projection._DEFAULT_EPSILON,
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
                The minimum reactive power of the flexible load (VAr). By default it is equal to
                `-s_max`, but it can be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default it is equal to
                `s_max`, but it can be further constrained.

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
        projection = Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=projection,
            s_max=s_max,
            q_min=q_min,
            q_max=q_max,
        )

    @classmethod
    @ureg_wraps(None, (None, "V", "V", "V", "V", "V", "V", "VA", "VAr", "VAr", None, None, None, None, None))
    def pq_u_consumption(
        cls,
        up_min: Float | Q_[Float],
        up_down: Float | Q_[Float],
        uq_min: Float | Q_[Float],
        uq_down: Float | Q_[Float],
        uq_up: Float | Q_[Float],
        uq_max: Float | Q_[Float],
        s_max: Float | Q_[Float],
        q_min: Float | Q_[Float] | None = None,
        q_max: Float | Q_[Float] | None = None,
        alpha_control: Float = Control._DEFAULT_ALPHA,
        epsilon_control: Float = Control._DEFAULT_EPSILON,
        type_proj: ProjectionType = Projection._DEFAULT_TYPE,
        alpha_proj: Float = Projection._DEFAULT_ALPHA,
        epsilon_proj: Float = Projection._DEFAULT_EPSILON,
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
                The minimum reactive power of the flexible load (VAr). By default it is equal to
                `-s_max`, but it can be further constrained.

            q_max:
                The maximum reactive power of the flexible load (VAr). By default it is equal to
                `s_max`, but it can be further constrained.

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
        projection = Projection(type=type_proj, alpha=alpha_proj, epsilon=epsilon_proj)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=projection,
            s_max=s_max,
            q_min=q_min,
            q_max=q_max,
        )

    def _compute_powers(self, voltages: Iterable[float], power: complex) -> ComplexArray:
        # Iterate over the provided voltages to get the associated flexible powers
        flexible_powers = [self._cy_fp.compute_power(v / SQRT3, power / 3.0) for v in voltages]
        return np.array(flexible_powers, dtype=np.complex128)
