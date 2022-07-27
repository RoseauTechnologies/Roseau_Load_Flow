import logging
from typing import Any

from roseau.load_flow.utils.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class Control:
    """A class to store the important values of a control."""

    DEFAULT_ALPHA: float = 200.0

    @ureg.wraps(None, (None, None, "V", "V", "V", "V", None), strict=False)
    def __init__(self, type: str, u_min: float, u_down: float, u_up: float, u_max: float, alpha: float = DEFAULT_ALPHA):
        """Control constructor

        Args:
            type:
                The type of the control:
                  * "constant" if no control;
                  * "p_max_u_production" to control the pmax of the load based on the voltage (production);
                  * "p_max_u_consumption" to control the pmax of the load based on the voltage (consumption);
                  * "q_u" to control the reactive power using the voltage.

            u_min:
                The minimum voltage i.e. the one the control reached the maximum action.

            u_down:
                The voltage which starts to trigger the control (lower value).

            u_up:
                The voltage  which starts to trigger the control (upper value).

            u_max:
                The maximum voltage i.e. the one the control reached its maximum action.

            alpha:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.
        """
        self.type = type
        self.u_min = u_min
        self.u_down = u_down
        self.u_up = u_up
        self.u_max = u_max
        self.alpha = alpha

    @classmethod
    def constant(cls) -> "Control":
        """Retrieve a constant control."""
        return cls(type="constant", u_min=0.0, u_down=0.0, u_up=0.0, u_max=0.0)

    @classmethod
    @ureg.wraps(None, (None, "V", "V", None), strict=False)
    def p_max_u_production(cls, u_up: float, u_max: float, alpha: float = DEFAULT_ALPHA) -> "Control":
        """Retrieve a control of the type "p_max_u_production" using the provided parameters.

        Args:
            u_up:
                The voltage  which starts to trigger the control (upper value).

            u_max:
                The maximum voltage i.e. the one the control reached its maximum action.

            alpha:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

        Returns:
            The control using the provided parameters.

        TODO Add in the docstring a link to an image of the LaTeX documentation.
        """
        assert u_up < u_max
        return cls(type="p_max_u_production", u_min=0.0, u_down=0.0, u_up=u_up, u_max=u_max, alpha=alpha)

    @classmethod
    @ureg.wraps(None, (None, "V", "V", None), strict=False)
    def p_max_u_consumption(cls, u_min: float, u_down: float, alpha: float = DEFAULT_ALPHA) -> "Control":
        """Retrieve a control of the type "p_max_u_consumption" using the provided parameters.

        Args:
            u_min:
                The minimum voltage i.e. the one the control reached the maximum action.

            u_down:
                The voltage which starts to trigger the control (lower value).

            alpha:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

        Returns:
            The control using the provided parameters.

        TODO Add in the docstring a link to an image of the LaTeX documentation.
        """
        assert u_min < u_down
        return cls(type="p_max_u_consumption", u_min=u_min, u_down=u_down, u_up=0.0, u_max=0.0, alpha=alpha)

    @classmethod
    @ureg.wraps(None, (None, "V", "V", "V", "V", None), strict=False)
    def q_u(cls, u_min: float, u_down: float, u_up: float, u_max: float, alpha: float = DEFAULT_ALPHA) -> "Control":
        """Retrieve a control of the type "q_u" using the provided parameters.

        Args:
            u_min:
                The minimum voltage i.e. the one the control reached the maximum action.

            u_down:
                The voltage which starts to trigger the control (lower value).

            u_up:
                The voltage  which starts to trigger the control (upper value).

            u_max:
                The maximum voltage i.e. the one the control reached its maximum action.

            alpha:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

        Returns:
            The control using the provided parameters.

        TODO Add in the docstring a link to an image of the LaTeX documentation.
        """
        assert u_min < u_down < u_up < u_max
        return cls(type="q_u", u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Control":
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
            msg = f"Unsupported control type {data['type']}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE)

    def to_dict(self) -> dict[str, Any]:
        if self.type == "constant":
            return {"type": "constant"}
        elif self.type == "p_max_u_production":
            return {"type": "p_max_u_production", "u_up": self.u_up, "u_max": self.u_max, "alpha": self.alpha}
        elif self.type == "p_max_u_consumption":
            return {"type": "p_max_u_consumption", "u_min": self.u_min, "u_down": self.u_down, "alpha": self.alpha}
        elif self.type == "q_u":
            return {
                "type": "q_u",
                "u_min": self.u_min,
                "u_down": self.u_down,
                "u_up": self.u_up,
                "u_max": self.u_max,
                "alpha": self.alpha,
            }
        else:
            msg = f"Unsupported control type {self.type!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE)


class Projection:
    """This class defines the projection on the feasible circle for a flexible load."""

    DEFAULT_ALPHA: float = 100.0
    DEFAULT_EPSILON: float = 0.01

    def __init__(self, type: str, alpha: float = DEFAULT_ALPHA, epsilon: float = DEFAULT_EPSILON):
        """Projection constructor.

        Args:
            type:
                The type of the projection. It can be:
                  * "euclidean" for an Euclidean projection on the feasible space;
                  * "keep_p" for maintaining a constant P;
                  * "keep_q" for maintaining a constant Q.

            alpha:
                This value is used to make soft sign function and to build a soft projection function.

            epsilon:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean projection.

                .. math::
                    \\sqrt{S}=\\sqrt{\varepsilon \times \\exp\\left(\frac{-{|S|}^2}{\varepsilon}\right) + {|S|}^2}
        """
        self.type = type
        self.alpha = alpha
        self.epsilon = epsilon

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Projection":
        alpha = data["alpha"] if "alpha" in data else cls.DEFAULT_ALPHA
        epsilon = data["epsilon"] if "epsilon" in data else cls.DEFAULT_EPSILON
        return cls(type=data["type"], alpha=alpha, epsilon=epsilon)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "alpha": self.alpha,
            "epsilon": self.epsilon,
        }


class FlexibleParameter:
    """This class stores the required data to make a flexible parameter."""

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
        self.s_max = s_max

    @classmethod
    def constant(cls) -> "FlexibleParameter":
        """Retrieve a constant control i.e. no control at all. It is an equivalent of the constant power load."""
        return cls(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
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
    ) -> "FlexibleParameter":
        """Class method to build a "p_max_u_production" flexible parameter.

        Args:
            u_up:
                The voltage  which starts to trigger the control (upper value).

            u_max:
                The maximum voltage i.e. the one the control reached its maximum action.

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible circle.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean projection.

        Returns:
            The flexible parameter which depicts "p_max_p_u_production" control on the production active power with
            a Euclidean projection.
        """
        control_p = Control.p_max_u_production(u_up=u_up, u_max=u_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=Control.constant(),
            projection=Projection(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
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
    ) -> "FlexibleParameter":
        """Class method to build a "p_max_u_consumption" flexible parameter.

        Args:
            u_min:
                The minimum voltage i.e. the one the control reached the maximum action.

            u_down:
                The voltage which starts to trigger the control (lower value).

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible circle.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean projection.

        Returns:
            The flexible parameter which depicts "p_max_p_u_consumption" control on the consumption active power with
            a Euclidean projection.
        """
        control_p = Control.p_max_u_consumption(u_min=u_min, u_down=u_down, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=Control.constant(),
            projection=Projection("euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
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
    ) -> "FlexibleParameter":
        """Class method to build a "q_u" flexible parameter.

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
                The apparent power of the flexible load (VA). It is the radius of the feasible circle.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean projection.

        Returns:
            The flexible parameter which depicts "q_u" control on the reactive power with a Euclidean projection.
        """
        control_q = Control.q_u(u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha_control)
        return cls(
            control_p=Control.constant(),
            control_q=control_q,
            projection=Projection(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
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
    ) -> "FlexibleParameter":
        """Class method to build a "pq_u_production" flexible parameter.

        Args:
            up_up:
                The voltage  which starts to trigger the control on the production (upper value).

            up_max:
                The maximum voltage i.e. the one the control (of production) reached its maximum action.

            uq_min:
                The minimum voltage i.e. the one the control reached the maximum action (reactive power control)

            uq_down:
                The voltage which starts to trigger the reactive power control (lower value).

            uq_up:
                The voltage  which starts to trigger the reactive power control (upper value).

            uq_max:
                The maximum voltage i.e. the one the reactive power control reached its maximum action.

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible circle.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean projection.

        Returns:
            The flexible parameter which depicts a control on the active power in production and a reactive
            power control with a Euclidean projection.
        """
        control_p = Control.p_max_u_production(u_up=up_up, u_max=up_max, alpha=alpha_control)
        control_q = Control.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=Projection(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
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
    ) -> "FlexibleParameter":
        """Class method to build a "pq_u_consumption" flexible parameter.

        Args:
            up_min:
                The minimum voltage i.e. the one the active power control reached the maximum action.

            up_down:
                The voltage which starts to trigger the active power control (lower value).

            uq_min:
                The minimum voltage i.e. the one the control reached the maximum action (reactive power control)

            uq_down:
                The voltage which starts to trigger the reactive power control (lower value).

            uq_up:
                The voltage  which starts to trigger the reactive power control (upper value).

            uq_max:
                The maximum voltage i.e. the one the reactive power control reached its maximum action.

            s_max:
                The apparent power of the flexible load (VA). It is the radius of the feasible circle.

            alpha_control:
                An approximation factor used by the family function (soft clip). The greater, the closer the function
                are from the non-differentiable function.

            alpha_proj:
                This value is used to make soft sign function and to build a soft projection function.

            epsilon_proj:
                This value is used to make a smooth sqrt function. It is only used in the Euclidean projection.

        Returns:
            The flexible parameter which depicts a control on the active power in consumption and a reactive
            power control with a Euclidean projection.
        """
        control_p = Control.p_max_u_consumption(u_min=up_min, u_down=up_down, alpha=alpha_control)
        control_q = Control.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=Projection(type="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlexibleParameter":
        control_p = Control.from_dict(data["control_p"])
        control_q = Control.from_dict(data["control_q"])
        projection = Projection.from_dict(data["projection"])
        return cls(control_p=control_p, control_q=control_q, projection=projection, s_max=data["s_max"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_p": self.control_p.to_dict(),
            "control_q": self.control_q.to_dict(),
            "projection": self.projection.to_dict(),
            "s_max": self.s_max,
        }
