import logging
from collections.abc import Sequence
from typing import Any, Optional

from pint import Quantity

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class VoltageSource(Element, JsonMixin):
    r"""A voltage source.

    The voltage equations are the following:

    .. math::
        \left(V_{\mathrm{a}}-V_{\mathrm{n}}\right) &= U_{\mathrm{a}} \\
        \left(V_{\mathrm{b}}-V_{\mathrm{n}}\right) &= U_{\mathrm{b}} \\
        \left(V_{\mathrm{c}}-V_{\mathrm{n}}\right) &= U_{\mathrm{c}}

    Where $U$ is the voltage and $V$ is the node potential.
    """

    allowed_phases = Bus.allowed_phases

    def __init__(
        self, id: Any, bus: Bus, *, voltages: Sequence[complex], phases: Optional[str] = None, **kwargs
    ) -> None:
        """Voltage source constructor.

        Args:
            id:
                The unique ID of the voltage source.

            bus:
                The bus of the voltage source.

            voltages:
                The voltages of the source. They will be fixed on the connected bus.

            phases:
                The phases of the source. A string like ``"abc"`` or ``"an"`` etc. The order of the
                phases is important. For a full list of supported phases, see the class attribute
                :attr:`allowed_phases`. All phases of the source, except ``"n"``, must be present in
                the phases of the connected bus. By default, the phases of the bus are used.
        """
        super().__init__(**kwargs)
        self.connected_elements = [bus]
        bus.connected_elements.append(self)
        self.id = id

        if phases is None:
            phases = bus.phases
        else:
            self._check_phases(id, phases=phases)
            # Also check they are in the bus phases
            phases_not_in_bus = set(phases) - set(bus.phases) - {"n"}  # "n" is allowed to be absent
            if phases_not_in_bus:
                msg = (
                    f"Phases {sorted(phases_not_in_bus)} of source {id!r} are not in bus "
                    f"{bus.id!r} phases {bus.phases!r}"
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        self._size = len(set(phases) - {"n"})

        if len(voltages) != self._size:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)

        if isinstance(voltages, Quantity):
            voltages = voltages.m_as("V")

        self.phases = phases
        self.bus = bus
        self.voltages = voltages

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id!r}, bus={self.bus.id!r}, voltages={self.voltages!r}, "
            f"phases={self.phases!r})"
        )

    @ureg.wraps(None, (None, "V"), strict=False)
    def update_voltages(self, voltages: Sequence[complex]) -> None:
        """Change the voltages of the source.

        Args:
            voltages:
                The new voltages to set on the source.
        """
        if len(voltages) != self._size:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)
        self.voltages = voltages

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any], bus: Bus) -> "VoltageSource":
        v: dict[str, list[str]] = data["voltages"]
        phases: str = data["phases"]
        voltages = [complex(*v[f"v{ph}"]) for ph in phases.removesuffix("n")]
        return cls(data["id"], bus, voltages=voltages, phases=phases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "phases": self.phases,
            "voltages": {f"v{ph}": [v.real, v.imag] for v, ph in zip(self.voltages, self.phases)},
        }
