import logging
from typing import Any

from roseau.load_flow.utils import ThundersIOError

logger = logging.getLogger(__name__)


class Control:
    DEFAULT_ALPHA: float = 200.0

    def __init__(self, type_: str, u_min: float, u_down: float, u_up: float, u_max: float, alpha: float = 4.0):
        self.type = type_
        self.u_min = u_min
        self.u_down = u_down
        self.u_up = u_up
        self.u_max = u_max
        self.alpha = alpha

    @classmethod
    def constant(cls) -> "Control":
        return cls(type_="constant", u_min=0.0, u_down=0.0, u_up=0.0, u_max=0.0)

    @classmethod
    def p_max_u_production(cls, u_up: float, u_max: float, alpha: float = DEFAULT_ALPHA) -> "Control":
        assert u_up < u_max
        return cls(type_="p_max_u_production", u_min=0.0, u_down=0.0, u_up=u_up, u_max=u_max, alpha=alpha)

    @classmethod
    def p_max_u_consumption(cls, u_min: float, u_down: float, alpha: float = DEFAULT_ALPHA) -> "Control":
        assert u_min < u_down
        return cls(type_="p_max_u_consumption", u_min=u_min, u_down=u_down, u_up=0.0, u_max=0.0, alpha=alpha)

    @classmethod
    def q_u(cls, u_min: float, u_down: float, u_up: float, u_max: float, alpha: float = DEFAULT_ALPHA) -> "Control":
        assert u_min < u_down < u_up < u_max
        return cls(type_="q_u", u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha)

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
            raise ThundersIOError(f"Unsupported control type {data['type']}")

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
            raise ThundersIOError(f"Unsupported control type {self.type}")


class Projection:
    DEFAULT_ALPHA: float = 100.0
    DEFAULT_EPSILON: float = 0.01

    def __init__(self, t: str, alpha: float = DEFAULT_ALPHA, epsilon: float = DEFAULT_EPSILON):
        self.t = t
        self.alpha = alpha
        self.epsilon = epsilon

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Projection":
        alpha = data["alpha"] if "alpha" in data else cls.DEFAULT_ALPHA
        epsilon = data["epsilon"] if "epsilon" in data else cls.DEFAULT_EPSILON
        return cls(t=data["type"], alpha=alpha, epsilon=epsilon)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.t,
            "alpha": self.alpha,
            "epsilon": self.epsilon,
        }


class FlexibleParameter:
    def __init__(self, control_p: Control, control_q: Control, projection: Projection, s_max: float) -> None:
        self.control_p = control_p
        self.control_q = control_q
        self.projection = projection
        self.s_max = s_max

    @classmethod
    def constant(cls) -> "FlexibleParameter":
        return cls(
            control_p=Control.constant(), control_q=Control.constant(), projection=Projection(t="euclidean"), s_max=1.0
        )

    @classmethod
    def p_max_u_production(
        cls,
        u_up: float,
        u_max: float,
        s_max: float,
        alpha_control: float = Control.DEFAULT_ALPHA,
        alpha_proj: float = Projection.DEFAULT_ALPHA,
        epsilon_proj: float = Projection.DEFAULT_EPSILON,
    ) -> "FlexibleParameter":
        control_p = Control.p_max_u_production(u_up=u_up, u_max=u_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=Control.constant(),
            projection=Projection(t="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
    def p_max_u_consumption(
        cls,
        u_min: float,
        u_down: float,
        s_max: float,
        alpha_control: float = Control.DEFAULT_ALPHA,
        alpha_proj: float = Projection.DEFAULT_ALPHA,
        epsilon_proj: float = Projection.DEFAULT_EPSILON,
    ) -> "FlexibleParameter":
        control_p = Control.p_max_u_consumption(u_min=u_min, u_down=u_down, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=Control.constant(),
            projection=Projection("euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
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
        control_q = Control.q_u(u_min=u_min, u_down=u_down, u_up=u_up, u_max=u_max, alpha=alpha_control)
        return cls(
            control_p=Control.constant(),
            control_q=control_q,
            projection=Projection(t="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
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
        control_p = Control.p_max_u_production(u_up=up_up, u_max=up_max, alpha=alpha_control)
        control_q = Control.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=Projection(t="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

    @classmethod
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
        control_p = Control.p_max_u_consumption(u_min=up_min, u_down=up_down, alpha=alpha_control)
        control_q = Control.q_u(u_min=uq_min, u_down=uq_down, u_up=uq_up, u_max=uq_max, alpha=alpha_control)
        return cls(
            control_p=control_p,
            control_q=control_q,
            projection=Projection(t="euclidean", alpha=alpha_proj, epsilon=epsilon_proj),
            s_max=s_max,
        )

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
