import logging
from abc import ABC, abstractmethod
from typing import Final

import numpy as np
from typing_extensions import TypeVar

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models.buses import Bus
from roseau.load_flow.models.connectables import AbstractConnectable
from roseau.load_flow.models.loads.flexible_parameters import FlexibleParameter
from roseau.load_flow.typing import ComplexArray, ComplexScalarOrArrayLike1D, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow_engine.cy_engine import (
    CyAdmittanceLoad,
    CyCurrentLoad,
    CyDeltaAdmittanceLoad,
    CyDeltaCurrentLoad,
    CyDeltaFlexibleLoad,
    CyDeltaPowerLoad,
    CyFlexibleLoad,
    CyLoad,
    CyPowerLoad,
)

logger = logging.getLogger(__name__)

_CyL_co = TypeVar("_CyL_co", bound=CyLoad, default=CyLoad, covariant=True)


class AbstractLoad(AbstractConnectable[_CyL_co], ABC):
    """An abstract class of an electric load.

    The subclasses of this class can be used to model:
        * star-connected loads using a `phases` constructor argument containing `"n"`
        * delta-connected loads using a `phases` constructor argument not containing `"n"`
    """

    element_type: Final = "load"

    @abstractmethod
    def __init__(self, id: Id, bus: Bus, *, phases: str | None = None, connect_neutral: bool | None = None) -> None:
        """AbstractLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to be
                connected to buses that don't have a neutral if ``connect_neutral`` is not set to
                ``True``.

            connect_neutral:
                Specifies whether the load's neutral should be connected to the bus's neutral or
                left floating. By default, the load's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the load's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        super().__init__(id, bus, phases=phases, connect_neutral=connect_neutral)
        self._symbol = {"power": "S", "current": "I", "impedance": "Z"}[self.type]
        self._res_inner_currents: ComplexArray | None = None

    @property
    def is_flexible(self) -> bool:
        """Whether the load is flexible or not. Only :class:`PowerLoad` can be flexible."""
        return False

    def _refresh_results(self) -> None:
        if self._fetch_results:
            super()._refresh_results()
            self._res_inner_currents = self._cy_element.get_inner_currents(self._size)

    def _res_inner_currents_getter(self, warning: bool) -> ComplexArray:
        self._refresh_results()
        return self._res_getter(value=self._res_inner_currents, warning=warning)

    def _res_inner_powers_getter(self, warning: bool) -> ComplexArray:
        currents = self._res_inner_currents_getter(warning=warning)
        voltages = self._res_voltages_getter(warning=False)  # warn only once
        return voltages * currents.conjugate()

    @property
    @ureg_wraps("A", (None,))
    def res_inner_currents(self) -> Q_[ComplexArray]:
        """The load flow result of the currents that flow in the inner components of the load (A)."""
        return self._res_inner_currents_getter(warning=True)

    @property
    @ureg_wraps("VA", (None,))
    def res_inner_powers(self) -> Q_[ComplexArray]:
        """The load flow result of the powers that flow in the inner components of the load (VA).

        Unlike `res_powers`, the inner powers do not depend on the reference of potentials. They
        are the physical powers consumed by each of the load dipoles.
        """
        return self._res_inner_powers_getter(warning=True)

    def _validate_value(self, value: ComplexScalarOrArrayLike1D) -> ComplexArray:
        values = [value for _ in range(self._size)] if np.isscalar(value) else value
        values = np.array(values, dtype=np.complex128)
        if len(values) != self._size:
            msg = f"Incorrect number of {self.type}s: {len(values)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{self._symbol}_SIZE"])
        # A load cannot have any zero impedance
        if self.type == "impedance" and np.isclose(values, 0).any():
            msg = f"An impedance of the load {self.id!r} is null"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_VALUE)
        return values

    #
    # Json Mixin interface
    #
    def _parse_results_from_dict(self, data: JsonDict, include_results: bool) -> None:
        if include_results and "results" in data:
            super()._parse_results_from_dict(data, include_results=include_results)
            if "inner_currents" in data["results"]:
                self._res_inner_currents = np.array(
                    [complex(*i) for i in data["results"]["inner_currents"]], dtype=np.complex128
                )
            if "flexible_powers" in data["results"]:
                assert isinstance(self, PowerLoad), "Only PowerLoad can be flexible"
                self._res_flexible_powers = np.array(
                    [complex(*p) for p in data["results"]["flexible_powers"]], dtype=np.complex128
                )

    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> "AbstractLoad":
        load_type = data["type"]
        if load_type == "power":
            if (fp_data_list := data.get("flexible_params")) is not None:
                fp = [
                    FlexibleParameter.from_dict(data=fp_dict, include_results=include_results)
                    for fp_dict in fp_data_list
                ]
            else:
                fp = None
            self = PowerLoad(
                id=data["id"],
                bus=data["bus"],
                powers=[complex(*s) for s in data["powers"]],
                phases=data["phases"],
                flexible_params=fp,
                connect_neutral=data["connect_neutral"],
            )
        elif load_type == "current":
            self = CurrentLoad(
                id=data["id"],
                bus=data["bus"],
                currents=[complex(*i) for i in data["currents"]],
                phases=data["phases"],
            )
        elif load_type == "impedance":
            self = ImpedanceLoad(
                id=data["id"],
                bus=data["bus"],
                impedances=[complex(*z) for z in data["impedances"]],
                phases=data["phases"],
                connect_neutral=data["connect_neutral"],
            )
        else:
            msg = f"Unknown load type {load_type!r} for load {data['id']!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        self._parse_results_from_dict(data, include_results=include_results)
        return self

    def _to_dict(self, include_results: bool) -> JsonDict:
        complex_array = getattr(self, f"_{self.type}s")
        data = super()._to_dict(include_results=include_results)
        data[f"{self.type}s"] = [[value.real, value.imag] for value in complex_array]
        if self.is_flexible:
            assert isinstance(self, PowerLoad), "Only PowerLoad can be flexible"
            assert self.flexible_params is not None, "Flexible load must have flexible parameters"
            data["flexible_params"] = [fp.to_dict(include_results=include_results) for fp in self.flexible_params]
            if include_results:
                flexible_powers = self._res_flexible_powers_getter(warning=False)  # warn only once
                data["results"]["flexible_powers"] = [[s.real, s.imag] for s in flexible_powers]
        if include_results:
            inner_currents = self._res_inner_currents_getter(warning=False)
            data["results"]["inner_currents"] = [[i.real, i.imag] for i in inner_currents]
            data["results"] = data.pop("results")  # move results to the end
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        results = super()._results_to_dict(warning=warning, full=full)
        inner_currents = self._res_inner_currents_getter(warning=False)
        results["inner_currents"] = [[i.real, i.imag] for i in inner_currents]
        if full:
            inner_powers = self._res_inner_powers_getter(warning=False)
            results["inner_powers"] = [[i.real, i.imag] for i in inner_powers]
        if self.is_flexible:
            assert isinstance(self, PowerLoad), "Only PowerLoad can be flexible"
            flexible_powers = self._res_flexible_powers_getter(warning=False)  # warn only once
            results["flexible_powers"] = [[s.real, s.imag] for s in flexible_powers]
        return results


class PowerLoad(AbstractLoad[CyPowerLoad | CyDeltaPowerLoad | CyFlexibleLoad | CyDeltaFlexibleLoad]):
    """A constant power load."""

    type: Final = "power"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        powers: ComplexScalarOrArrayLike1D,
        phases: str | None = None,
        flexible_params: list[FlexibleParameter] | None = None,
        connect_neutral: bool | None = None,
    ) -> None:
        """PowerLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            powers:
                A single power value or an array-like of power values for each phase component.
                Either complex values (VA) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

                When a scalar value is provided, it creates a balanced load with the same power for
                each phase. The scalar value passed is assumed to be the power of each component of
                the load, not the total multi-phase power. To create an unbalanced load, provide a
                vector of power values with the same length as the number of components of the load.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to be
                connected to buses that don't have a neutral if ``connect_neutral`` is not set to
                ``True``.

            flexible_params:
                A list of :class:`FlexibleParameters` object, one for each phase. When provided,
                the load is considered as flexible (or controllable) and the parameters are used
                to compute the flexible power of the load.

            connect_neutral:
                Specifies whether the load's neutral should be connected to the bus's neutral or
                left floating. By default, the load's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the load's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        super().__init__(id=id, bus=bus, phases=phases, connect_neutral=connect_neutral)

        if bus.short_circuits:
            msg = (
                f"The power load {self.id!r} is connected on bus {bus.id!r} that already has a short-circuit. "
                f"It makes the short-circuit calculation impossible."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)
        if flexible_params and len(flexible_params) != self._size:
            msg = f"Incorrect number of parameters: {len(flexible_params)} instead of {self._size}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE)

        self._flexible_params = flexible_params
        self.powers = powers
        self._res_flexible_powers: ComplexArray | None = None

        if self.is_flexible:
            cy_parameters = np.array([p._cy_fp for p in flexible_params])  # type: ignore
            if self.phases == "abc":
                self._cy_element = CyDeltaFlexibleLoad(n=self._n, powers=self._powers, parameters=cy_parameters)
            else:
                self._cy_element = CyFlexibleLoad(n=self._n, powers=self._powers, parameters=cy_parameters)
        else:
            if self.phases == "abc":
                self._cy_element = CyDeltaPowerLoad(n=self._n, powers=self._powers)
            else:
                self._cy_element = CyPowerLoad(n=self._n, powers=self._powers)
        self._cy_connect()

    @property
    def flexible_params(self) -> list[FlexibleParameter] | None:
        return self._flexible_params

    @property
    def is_flexible(self) -> bool:
        return self._flexible_params is not None

    @property
    @ureg_wraps("VA", (None,))
    def powers(self) -> Q_[ComplexArray]:
        """The powers of the load (VA).

        Setting the powers will update the load's power values and invalidate the network results.
        """
        return self._powers

    @powers.setter
    @ureg_wraps(None, (None, "VA"))
    def powers(self, value: ComplexScalarOrArrayLike1D) -> None:
        value = self._validate_value(value)
        if self._flexible_params is not None:
            for power, fp in zip(value, self._flexible_params, strict=True):
                if fp.control_p.type == "constant" and fp.control_q.type == "constant":
                    continue  # No checks for this case
                if abs(power) > fp._s_max:
                    msg = f"The power is greater than the parameter s_max for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if power.imag < fp._q_min:
                    msg = f"The reactive power is lower than the parameter q_min for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if power.imag > fp._q_max:
                    msg = f"The reactive power is greater than the parameter q_max for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if fp.control_p.type == "p_max_u_production" and power.real > 0:
                    msg = f"There is a production control but a positive power for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
                if fp.control_p.type == "p_max_u_consumption" and power.real < 0:
                    msg = f"There is a consumption control but a negative power for flexible load {self.id!r}"
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_S_VALUE)
        self._powers = value
        self._invalidate_network_results()
        if self._cy_initialized:
            self._cy_element.update_powers(self._powers)

    def _refresh_results(self) -> None:
        if self._fetch_results:
            super()._refresh_results()
            if self.is_flexible:
                self._res_flexible_powers = self._cy_element.get_powers(self._n)

    def _res_flexible_powers_getter(self, warning: bool) -> ComplexArray:
        self._refresh_results()
        return self._res_getter(value=self._res_flexible_powers, warning=warning)

    @property
    @ureg_wraps("VA", (None,))
    def res_flexible_powers(self) -> Q_[ComplexArray]:
        """The load flow result of the load flexible powers (VA).

        This property is only available for flexible loads.

        It returns the "inner powers" of the load instead of the "line powers" flowing into the load
        connection points. This property is equivalent to the :attr:`res_inner_powers` property, not
        to the :attr:`res_powers` property. Prefer using ``res_inner_powers`` because it is available
        for all loads.
        """
        if not self.is_flexible:
            msg = f"The load {self.id!r} is not flexible and does not have flexible powers"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE)
        return self._res_flexible_powers_getter(warning=True)


class CurrentLoad(AbstractLoad[CyCurrentLoad | CyDeltaCurrentLoad]):
    """A constant current load."""

    type: Final = "current"

    def __init__(self, id: Id, bus: Bus, *, currents: ComplexScalarOrArrayLike1D, phases: str | None = None) -> None:
        """CurrentLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            currents:
                A single current value or an array-like of current values for each phase component.
                Either complex values (A) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values. The complex currents provided define the currents magnitudes and
                their phase shift from the voltages of the load. For example, a current of
                ``10*exp(-90°j)`` represents an inductive constant current of 10 A.

                When a scalar value is provided, it creates a balanced load with the same current
                for each phase. To create an unbalanced load, provide a vector of current values
                with the same length as the number of components of the load.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus.
        """
        super().__init__(id=id, phases=phases, bus=bus)

        if bus.short_circuits:
            msg = (
                f"The current load {self.id!r} is connected on bus {bus.id!r} that already has a short-circuit. "
                f"It makes the short-circuit calculation impossible."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT)
        if self.has_floating_neutral:
            msg = (
                f"Constant current loads cannot have a floating neutral. {type(self).__name__} "
                f"{id!r} has phases {phases!r} while bus {bus.id!r} has phases {bus.phases!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

        self.currents = currents  # handles size checks and unit conversion
        if self.phases == "abc":
            self._cy_element = CyDeltaCurrentLoad(n=self._n, currents=self._currents)
        else:
            self._cy_element = CyCurrentLoad(n=self._n, currents=self._currents)
        self._cy_connect()

    @property
    @ureg_wraps("A", (None,))
    def currents(self) -> Q_[ComplexArray]:
        """The currents of the load (Amps).

        Setting the currents will update the load's currents and invalidate the network results.
        """
        return self._currents

    @currents.setter
    @ureg_wraps(None, (None, "A"))
    def currents(self, value: ComplexScalarOrArrayLike1D) -> None:
        self._currents = self._validate_value(value)
        self._invalidate_network_results()
        if self._cy_initialized:
            self._cy_element.update_currents(self._currents)


class ImpedanceLoad(AbstractLoad[CyAdmittanceLoad | CyDeltaAdmittanceLoad]):
    """A constant impedance load."""

    type: Final = "impedance"

    def __init__(
        self,
        id: Id,
        bus: Bus,
        *,
        impedances: ComplexScalarOrArrayLike1D,
        phases: str | None = None,
        connect_neutral: bool | None = None,
    ) -> None:
        """ImpedanceLoad constructor.

        Args:
            id:
                A unique ID of the load in the network loads.

            bus:
                The bus to connect the load to.

            impedances:
                A single impedance value or an array-like of impedance values for each phase component.
                Either complex values (Ohms) or a :class:`Quantity <roseau.load_flow.units.Q_>` of
                complex values.

                When a scalar value is provided, it creates a balanced load with the same impedance
                for each phase. To create an unbalanced load, provide a vector of impedance values
                with the same length as the number of components of the load.

            phases:
                The phases of the load. A string like ``"abc"`` or ``"an"`` etc. The bus phases are
                used by default. The order of the phases is important. For a full list of supported
                phases, see the class attribute :attr:`allowed_phases`. All phases of the load must
                be present in the phases of the connected bus. Multiphase loads are allowed to be
                connected to buses that don't have a neutral if ``connect_neutral`` is not set to
                ``True``.

            connect_neutral:
                Specifies whether the load's neutral should be connected to the bus's neutral or
                left floating. By default, the load's neutral is connected when the bus has a
                neutral. If the bus does not have a neutral, the load's neutral is left floating
                by default. To override the default behavior, pass an explicit ``True`` or ``False``.
        """
        super().__init__(id=id, phases=phases, bus=bus, connect_neutral=connect_neutral)
        self.impedances = impedances
        if self.phases == "abc":
            self._cy_element = CyDeltaAdmittanceLoad(n=self._n, admittances=1.0 / self._impedances)
        else:
            self._cy_element = CyAdmittanceLoad(n=self._n, admittances=1.0 / self._impedances)
        self._cy_connect()

    @property
    @ureg_wraps("ohm", (None,))
    def impedances(self) -> Q_[ComplexArray]:
        """The impedances of the load (Ohms)."""
        return self._impedances

    @impedances.setter
    @ureg_wraps(None, (None, "ohm"))
    def impedances(self, impedances: ComplexScalarOrArrayLike1D) -> None:
        self._impedances = self._validate_value(impedances)
        self._invalidate_network_results()
        if self._cy_initialized:
            self._cy_element.update_admittances(1.0 / self._impedances)
