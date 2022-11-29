import logging
from collections.abc import Sequence
from typing import Any

from pint import Quantity

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.core import Element
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

    def __init__(self, id: Any, n: int, bus: Bus, voltages: Sequence[complex], **kwargs) -> None:
        """Voltage source constructor.

        Args:
            id:
                The unique ID of the voltage source.

            n:
                Number of ports ie number of phases.

            bus:
                The bus of the voltage source.

            voltages:
                The voltages of the source. They will be fixed on the connected bus.
        """
        super().__init__(**kwargs)
        self.connected_elements = [bus]
        bus.connected_elements.append(self)
        if len(voltages) != n - 1:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {n - 1}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)

        if isinstance(voltages, Quantity):
            voltages = voltages.m_as("V")

        self.id = id
        self.n = n
        self.bus = bus
        self.voltages = voltages

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, n={self.n}, bus={self.bus.id!r}, voltages={self.voltages!r})"

    @ureg.wraps(None, (None, "V"), strict=False)
    def update_voltages(self, voltages: Sequence[complex]) -> None:
        """Change the voltages of the source.

        Args:
            voltages:
                The new voltages to set on the source.
        """
        if len(voltages) != self.n - 1:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {self.n - 1}"
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
        return cls(id=data["id"], n=4, bus=bus, voltages=voltages)

    def to_dict(self) -> dict[str, Any]:
        va = self.voltages[0]
        vb = self.voltages[1]
        vc = self.voltages[2]
        return {
            "id": self.id,
            "n": self.n,
            "voltages": {"va": [va.real, va.imag], "vb": [vb.real, vb.imag], "vc": [vc.real, vc.imag]},
        }
