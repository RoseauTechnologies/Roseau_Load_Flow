import logging
from collections.abc import Sequence
from typing import Any

from pint import Quantity

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element, Phases
from roseau.load_flow.utils.json_mixin import JsonMixin
from roseau.load_flow.utils.units import ureg

logger = logging.getLogger(__name__)


class VoltageSource(Element, JsonMixin):
    """A voltage source.

    The voltage equations are the following:

    .. math::
        \\left(V_{\\mathrm{a}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{a}} \\\\
        \\left(V_{\\mathrm{b}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{b}} \\\\
        \\left(V_{\\mathrm{c}}-V_{\\mathrm{n}}\\right) &= U_{\\mathrm{c}}

    Where $U$ is the voltage and $V$ is the node potential.
    """

    def __init__(self, id: Any, phases: Phases, bus: Bus, voltages: Sequence[complex], **kwargs) -> None:
        """Voltage source constructor.

        Args:
            id:
                The unique ID of the voltage source.

            phases:
                The phases of the source. Only 3-phase elements are currently supported.
                Allowed values are: ``"abc"`` or ``"abcn"``.

            bus:
                The bus of the voltage source.

            voltages:
                The voltages of the source. They will be fixed on the connected bus.
        """
        self._check_phases(id, phases=phases)
        super().__init__(**kwargs)
        self.connected_elements = [bus]
        bus.connected_elements.append(self)
        if len(voltages) != 3:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)

        if isinstance(voltages, Quantity):
            voltages = voltages.m_as("V")

        self.id = id
        self.phases = phases
        self.bus = bus
        self.voltages = voltages

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id!r}, phases={self.phases!r}, bus={self.bus.id!r}, "
            f"voltages={self.voltages!r})"
        )

    @ureg.wraps(None, (None, "V"), strict=False)
    def update_voltages(self, voltages: Sequence[complex]) -> None:
        """Change the voltages of the source.

        Args:
            voltages:
                The new voltages to set on the source.
        """
        if len(voltages) != 3:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of 3"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)
        self.voltages = voltages

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: dict[str, Any], bus: Bus) -> "VoltageSource":
        v = data["voltages"]
        voltages = [complex(*v["va"]), complex(*v["vb"]), complex(*v["vc"])]
        return cls(id=data["id"], phases=data["phases"], bus=bus, voltages=voltages)

    def to_dict(self) -> dict[str, Any]:
        va = self.voltages[0]
        vb = self.voltages[1]
        vc = self.voltages[2]
        return {
            "id": self.id,
            "phases": self.phases,
            "voltages": {"va": [va.real, va.imag], "vb": [vb.real, vb.imag], "vc": [vc.real, vc.imag]},
        }
