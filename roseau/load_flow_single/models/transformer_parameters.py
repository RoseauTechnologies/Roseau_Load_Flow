import logging
from typing import Final, Self

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow import TransformerParameters as MultiTransformerParameters
from roseau.load_flow.constants import CLOCK_PHASE_SHIFT

logger = logging.getLogger(__name__)


class TransformerParameters(MultiTransformerParameters):
    """Parameters that define electrical models of three-phase transformers."""

    is_multi_phase: Final = False  # type: ignore

    # fmt: off
    allowed_vector_groups: Final = { # type: ignore
        # Common connections (clock numbers 0, 1, 5, 6, 11)
        "Dd0", "Yy0", "YNy0", "Yyn0", "YNyn0", "Dz0", "Dzn0",
        "Dy1", "Dyn1", "Yz1", "YNz1", "Yzn1", "YNzn1", "Yd1", "YNd1",
        "Dy5", "Dyn5", "Yz5", "YNz5", "Yzn5", "YNzn5", "Yd5", "YNd5",
        "Dd6", "Yy6", "YNy6", "Yyn6", "YNyn6", "Dz6", "Dzn6",
        "Dy11", "Dyn11", "Yz11", "YNz11", "Yzn11", "YNzn11", "Yd11", "YNd11",
        # Additional connections (clock numbers 2, 4, 7, 8, 10)
        "Dd2", "Dz2", "Dzn2",
        "Dd4", "Dz4", "Dzn4",
        "Dy7", "Dyn7", "Yz7", "YNz7", "Yzn7", "YNzn7", "Yd7", "YNd7",
        "Dd8", "Dz8", "Dzn8",
        "Dd10", "Dz10", "Dzn10",
    }
    # fmt: on

    @property
    def kd(self) -> complex:
        """The positive-sequence (direct-system) transformation ratio of the transformer."""
        return self._ulv / self._uhv * CLOCK_PHASE_SHIFT[self._clock]

    @property
    def z2d(self) -> complex:
        """The positive-sequence (direct-system) series impedance of the transformer."""
        return self._z2 / 3.0 if self.winding2[0] == "d" else self._z2

    @property
    def ymd(self) -> complex:
        """The positive-sequence (direct-system) magnetizing admittance of the transformer."""
        return self._ym * 3.0 if self.winding1[0] == "D" else self._ym

    @classmethod
    def from_roseau_load_flow(cls, tp_m: MultiTransformerParameters, /) -> Self:
        """Create an instance from a multi-phase `rlf.TransformerParameters` object."""
        if not isinstance(tp_m, MultiTransformerParameters):
            raise TypeError(f"Expected an rlf.TransformerParameters object, got {type(tp_m)}.")
        if tp_m.vg not in TransformerParameters.allowed_vector_groups:
            msg = (
                f"Multi-phase transformer parameters with id {tp_m.id!r} and vector group {tp_m.vg!r} "
                f"cannot be converted to `rlfs.TransformerParameters`. It must be three-phase."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE)
        tp_dict = tp_m.to_dict(include_results=False)
        return cls.from_dict(tp_dict, include_results=False)
