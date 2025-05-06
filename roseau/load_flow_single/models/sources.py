import logging
from typing import Final, Self

import numpy as np

from roseau.load_flow import SQRT3
from roseau.load_flow.typing import Complex, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyVoltageSource
from roseau.load_flow_single.models.buses import Bus
from roseau.load_flow_single.models.connectables import AbstractConnectable

logger = logging.getLogger(__name__)


class VoltageSource(AbstractConnectable[CyVoltageSource]):
    """A voltage source fixes the voltages of the bus it is connected to.

    See Also:
        The :ref:`Voltage source documentation page <models-voltage-source-usage>` for example usage.
    """

    element_type: Final = "source"
    type: Final = "voltage"

    def __init__(self, id: Id, bus: Bus, *, voltage: Complex | Q_[Complex]) -> None:
        """Voltage source constructor.

        Args:
            id:
                A unique ID of the voltage source in the network sources.

            bus:
                The bus of the voltage source.

            voltage:
                The complex voltage of the source (V).
        """
        super().__init__(id, bus)
        self.voltage = voltage
        self._cy_element = CyVoltageSource(n=self._n, voltages=np.array([self._voltage / SQRT3], dtype=np.complex128))
        self._cy_connect()

    @property
    @ureg_wraps("V", (None,))
    def voltage(self) -> Q_[complex]:
        """The complex voltage of the source (V).

        Setting the voltage will update the source voltage and invalidate the network results.
        """
        return self._voltage

    @voltage.setter
    @ureg_wraps(None, (None, "V"))
    def voltage(self, value: Complex | Q_[Complex]) -> None:
        """Set the voltages of the source."""
        self._voltage = complex(value)
        self._invalidate_network_results()
        if self._cy_initialized:
            self._cy_element.update_voltages(np.array([self._voltage / SQRT3], dtype=np.complex128))

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        self = cls(id=data["id"], bus=data["bus"], voltage=complex(*data["voltage"]))
        self._parse_results_from_dict(data, include_results=include_results)
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = super()._to_dict(include_results=include_results)
        data["voltage"] = [self._voltage.real, self._voltage.imag]
        if include_results:
            data["results"] = data.pop("results")  # move results to the end
        return data
