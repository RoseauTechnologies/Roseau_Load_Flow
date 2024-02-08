import json
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

    @ureg_wraps(None, (None, None, None, "V", "V", "VA", "W", "", "W", "", "VA"))
    def __init__(
        self,
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
    ) -> None:
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
        super().__init__(id)

        # Check
        if uhv < ulv:
            msg = (
                f"Transformer type {id!r} has the low voltages higher than the high voltages: "
                f"uhv={uhv:.2f} V and ulv={ulv:.2f} V."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES)
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

        self._sn = sn
        self._uhv = uhv
        self._ulv = ulv
        self._i0 = i0
        self._p0 = p0
        self._psc = psc
        self._vsc = vsc
        self.type = type
        if type in ("single", "center"):
            self.winding1 = None
            self.winding2 = None
            self.phase_displacement = None
        else:
            self.winding1, self.winding2, self.phase_displacement = self.extract_windings(string=type)
        self.max_power = max_power

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransformerParameters):
            return NotImplemented
        else:
            return (
                self.id == other.id
                and self.type == other.type
                and np.isclose(self._sn, other._sn)
                and np.isclose(self._p0, other._p0)
                and np.isclose(self._i0, other._i0)
                and np.isclose(self._uhv, other._uhv)
                and np.isclose(self._ulv, other._ulv)
                and np.isclose(self._psc, other._psc)
                and np.isclose(self._vsc, other._vsc)
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
    @ureg_wraps("W", (None,))
    def p0(self) -> Q_[float]:
        """Losses during off-load test (W)"""
        return self._p0

    @property
    @ureg_wraps("", (None,))
    def i0(self) -> Q_[float]:
        """Current during off-load test (%)"""
        return self._i0

    @property
    @ureg_wraps("W", (None,))
    def psc(self) -> Q_[float]:
        """Losses during short-circuit test (W)"""
        return self._psc

    @property
    @ureg_wraps("", (None,))
    def vsc(self) -> Q_[float]:
        """Voltages on LV side during short-circuit test (%)"""
        return self._vsc

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
        """Compute the transformer parameters ``z2``, ``ym``, ``k`` and ``orientation`` mandatory
        for some models.

        Where:
            * ``z2``: The series impedance of the transformer (Ohms).
            * ``ym``: The magnetizing admittance of the transformer (Siemens).
            * ``k``: The transformation ratio.
            * ``orientation``: 1 for direct winding, -1 for reverse winding.

        Returns:
            The parameters (``z2``, ``ym``, ``k``, ``orientation``).
        """
        # Off-load test
        # Iron losses resistance (Ohm)
        r_iron = self._uhv**2 / self._p0
        # Magnetizing inductance (Henry) * omega (rad/s)
        if self._i0 * self._sn > self._p0:
            lm_omega = self._uhv**2 / (np.sqrt((self._i0 * self._sn) ** 2 - self._p0**2))
            ym = 1 / r_iron + 1 / (1j * lm_omega)
        else:
            ym = 1 / r_iron

        # Short-circuit test
        r2 = self._psc * (self._ulv / self._sn) ** 2
        l2_omega = np.sqrt((self._vsc * self._ulv**2 / self._sn) ** 2 - r2**2)
        z2 = r2 + 1j * l2_omega

        # Change the voltages if the reference voltages is phase to neutral
        uhv = self._uhv
        ulv = self._ulv
        if self.type == "single" or self.type == "center":
            orientation = 1.0
        else:
            # Extract the windings of the primary and the secondary of the transformer
            if self.winding1[0] in ("y", "Y"):
                uhv /= np.sqrt(3.0)
            if self.winding2[0] in ("y", "Y"):
                ulv /= np.sqrt(3.0)
            if self.winding1[0] in ("z", "Z"):
                uhv /= 3.0
            if self.winding2[0] in ("z", "Z"):
                ulv /= 3.0
            if self.phase_displacement in (0, 11):  # Normal winding
                orientation = 1.0
            else:  # Reverse winding
                assert self.phase_displacement in (5, 6)
                orientation = -1.0

        return z2, ym, ulv / uhv, orientation

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        return cls(
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

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {
            "id": self.id,
            "sn": self._sn,
            "uhv": self._uhv,
            "ulv": self._ulv,
            "i0": self._i0,
            "p0": self._p0,
            "psc": self._psc,
            "vsc": self._vsc,
            "type": self.type,
        }
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

    def _results_from_dict(self, data: JsonDict) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to import."
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
        catalogue_data = cls.catalogue_data()

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
        manufacturer = str(catalogue_data.at[idx, "manufacturer"])
        range = str(catalogue_data.at[idx, "range"])
        efficiency = str(catalogue_data.at[idx, "efficiency"])
        nominal_power = int(catalogue_data.at[idx, "sn"] / 1000)

        # Get the data from the Json file
        path = cls.catalogue_path() / manufacturer / range / efficiency / f"{nominal_power}.json"
        try:
            json_dict = json.loads(path.read_text())
        except FileNotFoundError:
            msg = f"The file {path} has not been found while it should exist. Please post an issue on GitHub."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_MISSING) from None

        return cls.from_dict(json_dict)

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
