import logging
from typing import Final, Self

import numpy as np

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.connectables import AbstractConnectable
from roseau.load_flow.sym import PositiveSequence
from roseau.load_flow.typing import ComplexArray, ComplexScalarOrArrayLike1D, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import CyDeltaVoltageSource, CyVoltageSource

logger = logging.getLogger(__name__)


class VoltageSource(AbstractConnectable[CyVoltageSource | CyDeltaVoltageSource]):
    """A voltage source fixes the voltages on the phases of the bus it is connected to.

    The source can be connected in a wye or star configuration (i.e with a neutral) or in a delta
    configuration (i.e without a neutral).

    See Also:
        The :ref:`Voltage source documentation page <models-voltage-source-usage>` for example usage.
    """

    element_type: Final = "source"
    type: Final = "voltage"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        voltages: ComplexScalarOrArrayLike1D,
        phases: str | None = None,
        connect_neutral: bool | None = None,
    ) -> None:
        """Voltage source constructor.

        Args:
            id:
                A unique ID of the voltage source in the network sources.

            bus:
                The bus of the voltage source.

            voltages:
                A single voltage value or an array-like of the voltages of the source to be fixed on
                the connected bus phases. If the source has a neutral connection, the voltages are
                considered phase-to-neutral voltages, otherwise they are the phase-to-phase voltages.
                Either pass complex values (V) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

                When a scalar value is passed, it is interpreted as the first value of the source
                voltages vector. The other values are calculated based on the number of phases of
                the source. For a single-phase source, the passed scalar value is used. For a two-
                phase source, the second voltage value is the negative of the first value (180°
                phase shift). For a three-phase source, the second and third values are calculated
                based on the first value and the phase shift of -120° and 120°, respectively (120°
                phase shift clockwise).

            phases:
                The phases of the source. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the source must
                be present in the phases of the connected bus. Multiphase sources are allowed to be
                connected to buses that don't have a neutral if ``connect_neutral`` is not set to
                ``True``.

            connect_neutral:
                Specifies whether the source's neutral should be connected to the bus's neutral or
                left floating. By default, the source's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the source's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        super().__init__(id, bus, phases=phases, connect_neutral=connect_neutral)
        self.voltages = voltages
        if self.phases == "abc":
            self._cy_element = CyDeltaVoltageSource(n=self._n, voltages=self._voltages)
        else:
            self._cy_element = CyVoltageSource(n=self._n, voltages=self._voltages)
        self._cy_connect()

    @property
    @ureg_wraps("V", (None,))
    def voltages(self) -> Q_[ComplexArray]:
        """The complex voltages of the source (V).

        Setting the voltages will update the source voltages and invalidate the network results.

        Note:
            Setting a scalar value updates the complex voltages of all phases of the source, not
            just their magnitudes. The phase angles are calculated based on the number of phases of
            the source. For a single-phase source, the phase angle is 0°. For a two-phase source,
            the phase angle of the second phase is 180°. For a three-phase source, the phase angles
            of the second and third phases are -120° and 120°, respectively (120° phase shift
            clockwise).
        """
        return self._voltages

    @voltages.setter
    @ureg_wraps(None, (None, "V"))
    def voltages(self, value: ComplexScalarOrArrayLike1D) -> None:
        """Set the voltages of the source."""
        if np.isscalar(value):
            if self._size == 1:
                voltages = [value]
            elif self._size == 2:
                voltages = [value, -value]
            else:
                assert self._size == 3
                voltages = value * PositiveSequence
        else:
            voltages = value
        voltages = np.array(voltages, dtype=np.complex128)
        if len(voltages) != self._size:
            msg = f"Incorrect number of voltages: {len(voltages)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE)
        self._voltages = voltages
        self._invalidate_network_results()
        if self._cy_initialized:
            self._cy_element.update_voltages(self._voltages)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        self = cls(
            id=data["id"],
            bus=data["bus"],
            voltages=[complex(*v) for v in data["voltages"]],
            phases=data["phases"],
            connect_neutral=data["connect_neutral"],
        )
        self._parse_results_from_dict(data, include_results=include_results)
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        source_dict = super()._to_dict(include_results=include_results)
        source_dict["voltages"] = [[v.real, v.imag] for v in self._voltages]
        if include_results:
            source_dict["results"] = source_dict.pop("results")  # move results to the end
        return source_dict
