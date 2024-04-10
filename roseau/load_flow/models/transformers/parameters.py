import logging
import re
from importlib import resources
from pathlib import Path
from typing import NoReturn

import numpy as np
import pandas as pd
import regex
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import CatalogueMixin, Identifiable, JsonMixin

logger = logging.getLogger(__name__)


class TransformerParameters(Identifiable, JsonMixin, CatalogueMixin[pd.DataFrame]):
    """Parameters that define electrical models of transformers."""

    _EXTRACT_WINDINGS_RE = regex.compile(
        "(?(DEFINE)(?P<y_winding>yn?)(?P<d_winding>d)(?P<z_winding>zn?)(?P<p_set_1>[06])"
        "(?P<p_set_2>5|11))"
        ""
        "(?|(?P<w1>(?&y_winding))(?P<w2>(?&y_winding))(?P<p>(?&p_set_1))"  # yy
        "|(?P<w1>(?&y_winding))(?P<w2>(?&d_winding))(?P<p>(?&p_set_2))"  # yd
        "|(?P<w1>(?&y_winding))(?P<w2>(?&z_winding))(?P<p>(?&p_set_2))"  # yz
        "|(?P<w1>(?&d_winding))(?P<w2>(?&z_winding))(?P<p>(?&p_set_1))"  # dz
        "|(?P<w1>(?&d_winding))(?P<w2>(?&y_winding))(?P<p>(?&p_set_2))"  # dy
        "|(?P<w1>(?&d_winding))(?P<w2>(?&d_winding))(?P<p>(?&p_set_1)))",  # dd
        regex.IGNORECASE,
    )
    """The pattern to extract the winding of the primary and of the secondary of the transformer."""

    @ureg_wraps(None, (None, None, None, "V", "V", "VA", "ohm", "S", "VA"))
    def __init__(
        self,
        id: Id,
        type: str,
        uhv: float | Q_[float],
        ulv: float | Q_[float],
        sn: float | Q_[float],
        z2: complex | Q_[complex],
        ym: complex | Q_[complex],
        max_power: float | Q_[float] | None = None,
    ):
        """TransformerParameters constructor.

        Args:
            id:
                A unique ID of the transformer parameters, typically its canonical name.

            type:
                The type of transformer parameters. It can be "single" for single-phase transformers, "center" for
                center-tapped transformers, or the name of the windings such as "Dyn11" for three-phase transformers.
                Allowed windings are "D" for delta, "Y" for wye (star), and "Z" for zigzag.

            uhv:
                Phase-to-phase nominal voltages of the high voltages side (V)

            ulv:
                Phase-to-phase nominal voltages of the low voltages side (V)

            sn:
                The nominal power of the transformer (VA)

            z2:
                The series impedance located at the secondary side of the transformer.

            ym:
                The magnetizing admittance located at the primary side of the transformer.

            max_power:
                The maximum power loading of the transformer (VA). It is not used in the load flow.
        """
        super().__init__(id)

        # Check
        if uhv < ulv:
            msg = (
                f"Transformer type {id!r} has the low voltages higher than the high voltages: "
                f"uhv={uhv:.2f} V and ulv={ulv:.2f} V."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES)

        self._sn = sn
        self._uhv = uhv
        self._ulv = ulv
        self._z2 = z2
        self._ym = ym
        self.type = type
        if type in ("single", "center"):
            self.winding1 = None
            self.winding2 = None
            self.phase_displacement = None
        else:
            self.winding1, self.winding2, self.phase_displacement = self.extract_windings(string=type)
        self.max_power = max_power

        # Compute the ratio of transformation and the orientation (direct or reverse windings)
        self._k, self._orientation = self._to_k()

        # Computed on demand or filled using alternative construction `from_tests`
        self._from_tests = False
        self._p0 = None
        self._i0 = None
        self._psc = None
        self._vsc = None

    @classmethod
    @ureg_wraps(None, (None, None, None, "V", "V", "VA", "W", "", "W", "", "VA"))
    def from_tests(
        cls,
        id: Id,
        type: str,
        uhv: float | Q_[float],
        ulv: float | Q_[float],
        sn: float | Q_[float],
        p0: float | Q_[float],
        i0: float | Q_[float],
        psc: float | Q_[float],
        vsc: float | Q_[float],
        max_power: float | Q_[float] | None = None,
    ) -> "TransformerParameters":
        """TransformerParameters alternative constructor based on the off-load and short circuit tests results.

        Args:
            id:
                A unique ID of the transformer parameters, typically its canonical name.

            type:
                The type of transformer parameters. It can be "single" for single-phase transformers, "center" for
                center-tapped transformers, or the name of the windings such as "Dyn11" for three-phase transformers.
                Allowed windings are "D" for delta, "Y" for wye (star), and "Z" for zigzag.

            uhv:
                Phase-to-phase nominal voltages of the high voltages side (V)

            ulv:
                Phase-to-phase nominal voltages of the low voltages side (V)

            sn:
                The nominal power of the transformer (VA)

            p0:
                Losses during off-load test (W)

            i0:
                Current during off-load test (%)

            psc:
                Losses during short-circuit test (W)

            vsc:
                Voltages on LV side during short-circuit test (%)

            max_power:
                The maximum power loading of the transformer (VA). It is not used in the load flow.
        """
        # Check
        if i0 > 1.0 or i0 < 0.0:
            msg = (
                f"Transformer type {id!r} has the 'current during off-load test' i0={i0}. It is a "
                f"percentage that should be between 0 and 1."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if vsc > 1.0 or vsc < 0.0:
            msg = (
                f"Transformer type {id!r} has the 'voltages on LV side during short-circuit test' "
                f"vsc={vsc}. It is a percentage that should be between 0 and 1."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if psc / sn > vsc:
            msg = (
                f"Transformer type {id!r} has parameters that can't be modeled. The following inequality should be "
                f"respected: psc/sn <= vsc"
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if i0 * sn < p0:
            logger.warning(
                f"Transformer type {id!r} doesn't respect the inequality: i0 * sn > p0. The magnetizing admittance "
                f"imaginary part will be null."
            )

        # Compute z2 and ym
        z2, ym = cls._to_zy(type=type, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc)

        # Create an instance
        instance = cls(id=id, type=type, uhv=uhv, ulv=ulv, sn=sn, z2=z2, ym=ym, max_power=max_power)

        # Fill tests parameters
        instance._p0 = p0
        instance._i0 = i0
        instance._psc = psc
        instance._vsc = vsc
        instance._from_tests = True
        return instance

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransformerParameters):
            return NotImplemented
        else:
            return (
                self.id == other.id
                and self.type == other.type
                and np.isclose(self._sn, other._sn)
                and np.isclose(self._uhv, other._uhv)
                and np.isclose(self._ulv, other._ulv)
                and np.isclose(self._z2, other._z2)
                and np.isclose(self._ym, other._ym)
            )

    @property
    @ureg_wraps("V", (None,))
    def uhv(self) -> Q_[float]:
        """Phase-to-phase nominal voltages of the high voltages side (V)"""
        return self._uhv

    @property
    @ureg_wraps("V", (None,))
    def ulv(self) -> Q_[float]:
        """Phase-to-phase nominal voltages of the low voltages side (V)"""
        return self._ulv

    @property
    @ureg_wraps("VA", (None,))
    def sn(self) -> Q_[float]:
        """The nominal power of the transformer (VA)"""
        return self._sn

    @property
    @ureg_wraps("ohm", (None,))
    def z2(self) -> Q_[complex]:
        """The series impedance of the transformer (Ohm)"""
        return self._z2

    @property
    @ureg_wraps("S", (None,))
    def ym(self) -> Q_[complex]:
        """The magnetizing admittance of the transformer (S)"""
        return self._ym

    @property
    def max_power(self) -> Q_[float] | None:
        """The maximum power loading of the transformer (VA) if it is set."""
        return None if self._max_power is None else Q_(self._max_power, "VA")

    @max_power.setter
    @ureg_wraps(None, (None, "VA"))
    def max_power(self, value: float | Q_[float] | None) -> None:
        self._max_power = value

    @ureg_wraps(("ohm", "S", "", None), (None,))
    def to_zyk(self) -> tuple[Q_[complex], Q_[complex], Q_[float], float]:
        """Compute the transformer parameters ``z2``, ``ym``, ``k`` and ``orientation`` mandatory for some models.

        Where:
            * ``z2``: The series impedance of the transformer (Ohms).
            * ``ym``: The magnetizing admittance of the transformer (Siemens).
            * ``k``: The transformation ratio.
            * ``orientation``: 1 for direct winding, -1 for reverse winding.

        Returns:
            The parameters (``z2``, ``ym``, ``k``, ``orientation``).
        """
        return self._z2, self._ym, self._k, self._orientation

    @classmethod
    def _to_zy(
        cls, type: str, uhv: float, ulv: float, sn: float, p0: float, i0: float, psc: float, vsc: float
    ) -> tuple[complex, complex]:
        if type in ("single", "center"):
            winding1, winding2 = None, None
        else:
            winding1, winding2, _ = cls.extract_windings(string=type)
            winding1, winding2 = winding1[0].upper(), winding2[0].lower()

        # Off-load test
        # Iron losses resistance (Ohm)
        r_iron = uhv**2 / p0
        # Magnetizing inductance (Henry) * omega (rad/s)
        s0 = i0 * sn
        if s0 > p0:
            lm_omega = uhv**2 / np.sqrt(s0**2 - p0**2)
            ym = 1 / r_iron + 1 / (1j * lm_omega)
        else:
            ym = 1 / r_iron

        # Short-circuit test
        r2 = psc * (ulv / sn) ** 2
        l2_omega = np.sqrt((vsc * ulv**2 / sn) ** 2 - r2**2)
        z2 = r2 + 1j * l2_omega

        if winding1 == "D":
            ym /= 3
        if winding2 == "d":
            z2 *= 3

        return z2, ym

    def _to_k(self) -> tuple[float, float]:
        """Compute the transformer parameters ``k`` and ``orientation`` mandatory for some models.

        Where:
            * ``k``: The transformation ratio.
            * ``orientation``: 1 for direct winding, -1 for reverse winding.

        Returns:
            The parameters (``k``, ``orientation``).
        """
        uhv = self._uhv
        ulv = self._ulv
        if self.type in ("single", "center"):
            orientation = 1.0
        else:
            # Change the voltages if the reference voltages is phase to neutral
            winding1, winding2 = self.winding1[0].upper(), self.winding2[0].lower()

            # Extract the windings of the primary and the secondary of the transformer
            if winding1 == "Y":
                uhv /= np.sqrt(3.0)
            if winding1 == "Z":
                uhv /= 3.0
            if winding2 == "y":
                ulv /= np.sqrt(3.0)
            if winding2 == "z":
                ulv /= 3.0
            if self.phase_displacement in (0, 11):  # Normal winding
                orientation = 1.0
            else:  # Reverse winding
                assert self.phase_displacement in (5, 6)
                orientation = -1.0

        return ulv / uhv, orientation

    #
    # Off-load tests
    #
    @ureg_wraps(("W", ""), (None, None))
    def compute_no_load_parameters(self, solve_kwargs: JsonDict | None = None) -> tuple[Q_[float], Q_[float]]:
        """Compute the no-load parameters of the transformer parameters solving a load flow on a small circuit.

        Args:
            solve_kwargs:
                The keywords arguments used by the :meth:`ElectricalNetwork.solve_load_flow` method. By default, the
                default arguments of the method are used.

        Returns:
            The values ``p0``, the losses (in W), and ``i0``, the current (in %) during off-load test.
        """
        return self._compute_no_load_parameters(solve_kwargs=solve_kwargs)

    def _compute_no_load_parameters(self, solve_kwargs: JsonDict | None = None) -> tuple[float, float]:
        from roseau.load_flow.converters import calculate_voltages
        from roseau.load_flow.models import Bus, PotentialRef, Transformer, VoltageSource
        from roseau.load_flow.network import ElectricalNetwork

        if solve_kwargs is None:
            solve_kwargs = {}

        if self.type == "single":
            phases_hv = "an"
            phases_lv = "an"
            voltages = [self._uhv / np.sqrt(3)]
        elif self.type == "center":
            phases_hv = "ab"
            phases_lv = "abn"
            voltages = [self._uhv]
        else:
            # Three-phase transformer
            phases_hv = "abc" if self.winding1.lower().startswith("d") else "abcn"
            phases_lv = "abc" if self.winding2.lower().startswith("d") else "abcn"
            if "n" in phases_hv:
                voltages = self._uhv / np.sqrt(3) * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
            else:
                voltages = calculate_voltages(
                    potentials=self._uhv / np.sqrt(3) * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), phases="abc"
                )

        bus_hv = Bus(id="BusHV", phases=phases_hv)
        bus_lv = Bus(id="BusLV", phases=phases_lv)
        PotentialRef(id="PRefHV", element=bus_hv)
        PotentialRef(id="PRefLV", element=bus_lv)
        VoltageSource(id="VS", bus=bus_hv, voltages=voltages)
        transformer = Transformer(id="Transformer", bus1=bus_hv, bus2=bus_lv, parameters=self)

        en = ElectricalNetwork.from_element(bus_hv)
        en.solve_load_flow(**solve_kwargs)
        p_primary = transformer.res_powers[0].m.sum().real
        i_primary = abs(transformer.res_currents[0].m[0])
        if self.type == "single":
            in_ = self._sn / (self._uhv / np.sqrt(3))
        elif self.type == "center":
            in_ = self._sn / self._uhv
        else:
            in_ = self._sn / (np.sqrt(3) * self._uhv)

        # Additional checks
        # u_secondary = abs(calculate_voltages(bus_lv.res_potentials.m, phases_lv))
        # np.testing.assert_allclose(u_secondary, self._ulv/np.sqrt(3))

        return p_primary, i_primary / in_

    @property
    @ureg_wraps("W", (None,))
    def p0(self) -> Q_[float]:
        """Losses during off-load test (W)"""
        if self._p0 is None:
            self._p0, self._i0 = self._compute_no_load_parameters()
        return self._p0

    @property
    @ureg_wraps("", (None,))
    def i0(self) -> Q_[float]:
        """Current during off-load test (%)"""
        if self._i0 is None:
            self._p0, self._i0 = self._compute_no_load_parameters()
        return self._i0

    #
    # Short circuit test
    #
    @ureg_wraps(("W", ""), (None, None))
    def compute_short_circuit_parameters(self, solve_kwargs: JsonDict | None = None) -> tuple[Q_[float], Q_[float]]:
        """Compute the short circuit parameters of the transformer parameters solving a load flow on a small circuit.

        Args:
            solve_kwargs:
                The keywords arguments used by the :meth:`ElectricalNetwork.solve_load_flow` method. By default, the
                default arguments of the method are used.

        Returns:
            The values ``psc``, the losses (in W), and ``vsc``, the voltages on LV side (in %) during short-circuit
            test.
        """
        return self._compute_short_circuit_parameters(solve_kwargs=solve_kwargs)

    def _compute_short_circuit_parameters(self, solve_kwargs: JsonDict | None = None) -> tuple[float, float]:
        from roseau.load_flow.converters import calculate_voltages
        from roseau.load_flow.models import Bus, PotentialRef, Transformer, VoltageSource
        from roseau.load_flow.network import ElectricalNetwork

        if solve_kwargs is None:
            solve_kwargs = {}

        if self.type == "single":
            phases_hv = "an"
            phases_lv = "an"
            vsc = abs(self._z2) * self._sn / self._ulv**2
            voltages = vsc * self._uhv / np.sqrt(3)
        elif self.type == "center":
            phases_hv = "ab"
            phases_lv = "abn"
            vsc = abs(self._z2) * self._sn / self._ulv**2
            voltages = vsc * self._uhv
        else:
            # Three-phase transformer
            phases_hv = "abc" if self.winding1.lower().startswith("d") else "abcn"
            phases_lv = "abc" if self.winding2.lower().startswith("d") else "abcn"
            vsc = abs(self._z2) * self._sn / self._ulv**2
            if "n" in phases_hv:
                voltages = vsc * self._uhv / np.sqrt(3) * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
            else:
                voltages = calculate_voltages(
                    potentials=vsc * self._uhv / np.sqrt(3) * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), phases="abc"
                )

        bus_hv = Bus(id="BusHV", phases=phases_hv)
        bus_lv = Bus(id="BusLV", phases=phases_lv)
        PotentialRef(id="PRefHV", element=bus_hv)
        PotentialRef(id="PRefLV", element=bus_lv)
        VoltageSource(id="VS", bus=bus_hv, voltages=voltages)
        transformer = Transformer(id="Transformer", bus1=bus_hv, bus2=bus_lv, parameters=self)
        bus_lv.add_short_circuit(*phases_lv)
        en = ElectricalNetwork.from_element(bus_hv)
        en.solve_load_flow(**solve_kwargs)
        p_primary = transformer.res_powers[0].m.sum().real

        # Additional check
        # in_ = self._sn / (np.sqrt(3) * self._ulv)
        # i_secondary = abs(transformer.res_currents[1].m[0])
        # np.testing.assert_allclose(i_secondary, in_)

        return p_primary, vsc

    @property
    @ureg_wraps("W", (None,))
    def psc(self) -> Q_[float]:
        """Losses during short-circuit test (W)"""
        if self._psc is None:
            self._psc, self._vsc = self._compute_short_circuit_parameters()
        return self._psc

    @property
    @ureg_wraps("", (None,))
    def vsc(self) -> Q_[float]:
        """Voltages on LV side during short-circuit test (%)"""
        if self._vsc is None:
            self._psc, self._vsc = self._compute_short_circuit_parameters()
        return self._vsc

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        if "p0" in data:
            return cls.from_tests(
                id=data["id"],
                type=data["type"],  # Type of the transformer
                uhv=data["uhv"],  # Phase-to-phase nominal voltages of the high voltages side (V)
                ulv=data["ulv"],  # Phase-to-phase nominal voltages of the low voltages side (V)
                sn=data["sn"],  # Nominal power
                p0=data["p0"],  # Losses during off-load test (W)
                i0=data["i0"],  # Current during off-load test (%)
                psc=data["psc"],  # Losses during short-circuit test (W)
                vsc=data["vsc"],  # Voltages on LV side during short-circuit test (%)
                max_power=data.get("max_power"),  # Maximum power loading (VA)
            )
        else:
            z2 = complex(*data["z2"])
            ym = complex(*data["ym"])
            return cls(
                id=data["id"],
                type=data["type"],  # Type of the transformer
                uhv=data["uhv"],  # Phase-to-phase nominal voltages of the high voltages side (V)
                ulv=data["ulv"],  # Phase-to-phase nominal voltages of the low voltages side (V)
                sn=data["sn"],  # Nominal power
                z2=z2,  # Series impedance (ohm)
                ym=ym,  # Magnetizing admittance (S)
                max_power=data.get("max_power"),  # Maximum power loading (VA)
            )

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id, "sn": self._sn, "uhv": self._uhv, "ulv": self._ulv, "type": self.type}
        if self._from_tests:
            res.update({"i0": self._i0, "p0": self._p0, "psc": self._psc, "vsc": self._vsc})
        else:
            res.update({"z2": [self._z2.real, self._z2.imag], "ym": [self._ym.real, self._ym.imag]})
        if self.max_power is not None:
            res["max_power"] = self.max_power.magnitude
        for k, v in res.items():
            if isinstance(v, np.integer):
                res[k] = int(v)
            elif isinstance(v, np.floating):
                res[k] = float(v)
        return res

    def _results_to_dict(self, warning: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    #
    # Catalogue Mixin
    #
    @classmethod
    def catalogue_path(cls) -> Path:
        return Path(resources.files("roseau.load_flow") / "data" / "transformers").expanduser().absolute()

    @classmethod
    def catalogue_data(cls) -> pd.DataFrame:
        file = cls.catalogue_path() / "Catalogue.csv"
        return pd.read_csv(file, parse_dates=False)

    @classmethod
    def _get_catalogue(
        cls,
        id: str | re.Pattern[str] | None,
        manufacturer: str | re.Pattern[str] | None,
        range: str | re.Pattern[str] | None,
        efficiency: str | re.Pattern[str] | None,
        type: str | re.Pattern[str] | None,
        sn: float | None,
        uhv: float | None,
        ulv: float | None,
        raise_if_not_found: bool,
    ) -> tuple[pd.DataFrame, str]:
        # Get the catalogue data
        catalogue_data = cls.catalogue_data().drop(
            columns=["du1", "du0.8", "eff1 100%", "eff0.8 100%", "eff1 75%", "eff0.8 75%"]
        )

        # Filter on string/regular expressions
        query_msg_list = []
        for value, column_name, display_name, display_name_plural in (
            (id, "id", "id", "ids"),
            (manufacturer, "manufacturer", "manufacturer", "manufacturers"),
            (range, "range", "range", "ranges"),
            (efficiency, "efficiency", "efficiency", "efficiencies"),
            (type, "type", "type", "types"),
        ):
            if pd.isna(value):
                continue

            mask = cls._filter_catalogue_str(value=value, strings=catalogue_data[column_name])
            if raise_if_not_found and mask.sum() == 0:
                cls._raise_not_found_in_catalogue(
                    value=repr(value),
                    name=display_name,
                    name_plural=display_name_plural,
                    strings=catalogue_data[column_name],
                    query_msg_list=query_msg_list,
                )
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{display_name}={value!r}")

        # Filter on float
        for value, column_name, display_name, display_name_plural, display_unit in (
            (sn, "sn", "nominal power", "nominal powers", "kVA"),
            (uhv, "uhv", "primary side voltage", "primary side voltages", "kV"),
            (ulv, "ulv", "secondary side voltage", "secondary side voltages", "kV"),
        ):
            if pd.isna(value):
                continue

            mask = np.isclose(catalogue_data[column_name], value)
            if raise_if_not_found and mask.sum() == 0:
                cls._raise_not_found_in_catalogue(
                    value=f"{value / 1000:.1f} {display_unit}",
                    name=display_name,
                    name_plural=display_name_plural,
                    strings=catalogue_data[column_name].apply(lambda x: f"{x/1000:.1f} {display_unit}"),  # noqa: B023
                    query_msg_list=query_msg_list,
                )
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{display_name}={value/1000:.1f} {display_unit}")

        return catalogue_data, ", ".join(query_msg_list)

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, "VA", "V", "V"))
    def from_catalogue(
        cls,
        id: str | re.Pattern[str] | None = None,
        manufacturer: str | re.Pattern[str] | None = None,
        range: str | re.Pattern[str] | None = None,
        efficiency: str | re.Pattern[str] | None = None,
        type: str | re.Pattern[str] | None = None,
        sn: float | Q_[float] | None = None,
        uhv: float | Q_[float] | None = None,
        ulv: float | Q_[float] | None = None,
    ) -> Self:
        """Build a transformer parameters from one in the catalogue.

        Args:
            id:
                The id of the transformer to get from the catalogue. It can be a regular expression.

            manufacturer:
                The name of the manufacturer to get. It can be a regular expression.

            range:
                The name of the product range to get. It can be a regular expression.

            efficiency:
                The efficiency of the transformer get. It can be a regular expression.

            type:
                The type of the transformer to get. It can be a regular expression.

            sn:
                The nominal power of the transformer to get.

            uhv:
                The primary side voltage of the transformer to get.

            ulv:
                The secondary side voltage of the transformer to get.

        Returns:
            The selected transformer. If several transformers fitting the filters are in the catalogue, an error is
            raised.
        """
        # Get the catalogue data
        catalogue_data, query_info = cls._get_catalogue(
            id=id,
            manufacturer=manufacturer,
            range=range,
            efficiency=efficiency,
            type=type,
            sn=sn,
            uhv=uhv,
            ulv=ulv,
            raise_if_not_found=True,
        )

        cls._assert_one_found(
            found_data=catalogue_data["id"].tolist(), display_name="transformers", query_info=query_info
        )

        # A single one has been chosen
        idx = catalogue_data.index[0]
        return cls.from_tests(
            id=catalogue_data.at[idx, "id"],
            type=catalogue_data.at[idx, "type"],
            uhv=catalogue_data.at[idx, "uhv"],
            ulv=catalogue_data.at[idx, "ulv"],
            sn=catalogue_data.at[idx, "sn"],
            p0=catalogue_data.at[idx, "p0"],
            i0=catalogue_data.at[idx, "i0"],
            psc=catalogue_data.at[idx, "psc"],
            vsc=catalogue_data.at[idx, "vsc"],
        )

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, "VA", "V", "V"))
    def get_catalogue(
        cls,
        id: str | re.Pattern[str] | None = None,
        manufacturer: str | re.Pattern[str] | None = None,
        range: str | re.Pattern[str] | None = None,
        efficiency: str | re.Pattern[str] | None = None,
        type: str | re.Pattern[str] | None = None,
        sn: float | Q_[float] | None = None,
        uhv: float | Q_[float] | None = None,
        ulv: float | Q_[float] | None = None,
    ) -> pd.DataFrame:
        """Get the catalogue of available transformers.

        You can use the parameters below to filter the catalogue. If you do not specify any
        parameter, all the catalogue will be returned.

        Args:
            id:
                An optional manufacturer to filter the output. It can be a regular expression.

            manufacturer:
                An optional manufacturer to filter the output. It can be a regular expression.

            range:
                An optional product range to filter the output. It can be a regular expression.

            efficiency:
                An optional efficiency to filter the output. It can be a regular expression.

            type:
                An optional type of the transformer. It can be a regular expression.

            sn:
                An optional nominal power of the transformer to filter the output.

            uhv:
                An optional primary side voltage to filter the output.

            ulv:
                An optional secondary side voltage to filter the output.

        Returns:
            The catalogue data as a dataframe.
        """
        catalogue_data, _ = cls._get_catalogue(
            id=id,
            manufacturer=manufacturer,
            range=range,
            efficiency=efficiency,
            type=type,
            sn=sn,
            uhv=uhv,
            ulv=ulv,
            raise_if_not_found=False,
        )
        catalogue_data["sn"] /= 1000  # kVA
        catalogue_data["uhv"] /= 1000  # kV
        catalogue_data["ulv"] /= 1000  # kV
        return (
            catalogue_data.drop(columns=["i0", "p0", "psc", "vsc"])
            .rename(
                columns={
                    "id": "Id",
                    "manufacturer": "Manufacturer",
                    "range": "Product range",
                    "efficiency": "Efficiency",
                    "type": "Type",
                    "sn": "Nominal power (kVA)",
                    "uhv": "High voltage (kV)",
                    "ulv": "Low voltage (kV)",
                    # # If we ever want to display these columns
                    # "i0": "No-load current (%)",
                    # "p0": "No-load losses (W)",
                    # "psc": "Load Losses at 75°C  (W)",
                    # "vsc": "Impedance voltage (%)",
                }
            )
            .set_index("Id")
        )

    #
    # Utils
    #
    @classmethod
    def extract_windings(cls, string: str) -> tuple[str, str, int]:
        """Extract the windings and phase displacement from a given string

        Args:
            string:
                The string to parse.

        Returns:
            The first winding, the second winding, and the phase displacement
        """
        match = cls._EXTRACT_WINDINGS_RE.fullmatch(string=string)
        if match:
            groups = match.groupdict()
            winding1, winding2, phase_displacement = groups["w1"], groups["w2"], groups["p"]
            return winding1.upper(), winding2.lower(), int(phase_displacement)
        else:
            msg = f"Transformer windings cannot be extracted from the string {string!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
