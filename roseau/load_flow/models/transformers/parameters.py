import logging
import re
import textwrap
from importlib import resources
from pathlib import Path
from typing import NoReturn, Optional, Union

import numpy as np
import pandas as pd
import regex
from rich.table import Table
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import CatalogueMixin, Identifiable, JsonMixin, console

logger = logging.getLogger(__name__)


class TransformerParameters(Identifiable, JsonMixin, CatalogueMixin[pd.DataFrame]):
    """A class to store the parameters of the transformers.

    See Also:
        :ref:`Transformer parameters documentation <models-transformer_parameters>`
    """

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

    @ureg_wraps(None, (None, None, None, "V", "V", "VA", "W", "", "W", ""), strict=False)
    def __init__(
        self,
        id: Id,
        type: str,
        uhv: float,
        ulv: float,
        sn: float,
        p0: float,
        i0: float,
        psc: float,
        vsc: float,
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
        """
        super().__init__(id)
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
    @ureg_wraps("V", (None,), strict=False)
    def uhv(self) -> Q_[float]:
        """Phase-to-phase nominal voltages of the high voltages side (V)"""
        return self._uhv

    @property
    @ureg_wraps("V", (None,), strict=False)
    def ulv(self) -> Q_[float]:
        """Phase-to-phase nominal voltages of the low voltages side (V)"""
        return self._ulv

    @property
    @ureg_wraps("VA", (None,), strict=False)
    def sn(self) -> Q_[float]:
        """The nominal power of the transformer (VA)"""
        return self._sn

    @property
    @ureg_wraps("W", (None,), strict=False)
    def p0(self) -> Q_[float]:
        """Losses during off-load test (W)"""
        return self._p0

    @property
    @ureg_wraps("", (None,), strict=False)
    def i0(self) -> Q_[float]:
        """Current during off-load test (%)"""
        return self._i0

    @property
    @ureg_wraps("W", (None,), strict=False)
    def psc(self) -> Q_[float]:
        """Losses during short-circuit test (W)"""
        return self._psc

    @property
    @ureg_wraps("", (None,), strict=False)
    def vsc(self) -> Q_[float]:
        """Voltages on LV side during short-circuit test (%)"""
        return self._vsc

    @ureg_wraps(("ohm", "S", "", None), (None,), strict=False)
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
    def from_dict(cls, data: JsonDict) -> Self:
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
        )

    def to_dict(self, include_geometry: bool = True) -> JsonDict:
        return {
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

    def _results_to_dict(self, warning: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    def results_from_dict(self, data: JsonDict) -> NoReturn:
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
        return pd.read_csv(cls.catalogue_path() / "Catalogue.csv")

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, "VA", "V", "V"), strict=False)
    def from_catalogue(
        cls,
        id: Optional[Union[str, re.Pattern[str]]] = None,
        manufacturer: Optional[Union[str, re.Pattern[str]]] = None,
        range: Optional[Union[str, re.Pattern[str]]] = None,
        efficiency: Optional[Union[str, re.Pattern[str]]] = None,
        type: Optional[Union[str, re.Pattern[str]]] = None,
        sn: Optional[float] = None,
        uhv: Optional[float] = None,
        ulv: Optional[float] = None,
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

            mask = cls._filter_catalogue_str(value=value, catalogue_data=catalogue_data, column_name=column_name)
            if mask.sum() == 0:
                available_values = catalogue_data[column_name].unique().tolist()
                msg_part = textwrap.shorten(", ".join(repr(x) for x in available_values), width=500)
                if query_msg_list:
                    query_msg_part = ", ".join(query_msg_list)
                    msg = (
                        f"No {display_name} matching the name {value!r} has been found for the query {query_msg_part}. "
                        f"Available {display_name_plural} are {msg_part}."
                    )
                else:
                    msg = (
                        f"No {display_name} matching the name {value!r} has been found. "
                        f"Available {display_name_plural} are {msg_part}."
                    )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND)
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

            mask = cls._filter_catalogue_float(value=value, catalogue_data=catalogue_data, column_name=column_name)
            if mask.sum() == 0:
                available_values = catalogue_data[column_name].unique().tolist()
                msg_part = textwrap.shorten(
                    ", ".join(f"{x/1000:.1f} {display_unit}" for x in available_values), width=500
                )
                if query_msg_list:
                    query_msg_part = ", ".join(query_msg_list)
                    msg = (
                        f"No {display_name} matching {value/1000:.1f} {display_unit} has been found for the query"
                        f" {query_msg_part}. Available {display_name_plural} are {msg_part}."
                    )
                else:
                    msg = (
                        f"No {display_name} matching {value/1000:.1f} {display_unit} has been found. "
                        f"Available {display_name_plural} are {msg_part}."
                    )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND)
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{display_name}={value/1000:.1f} {display_unit}")

        # Final check
        if len(catalogue_data) == 0:  # pragma: no cover
            # This option should never happen as an error is raised when a filter is empty
            query_msg_part = ", ".join(query_msg_list)
            msg = (
                f"No transformers matching the query ({query_msg_part!r}) have been found. Please look at the "
                f"catalogue using the `print_catalogue` class method."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND)
        elif len(catalogue_data) > 1:
            query_msg_part = ", ".join(query_msg_list)
            msg = (
                f"Several transformers matching the query ({query_msg_part!r}) have been found. Please look at the "
                f"catalogue using the `print_catalogue` class method."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND)

        # A single one has been chosen
        idx = catalogue_data.index[0]
        manufacturer = catalogue_data.at[idx, "manufacturer"]
        range = catalogue_data.at[idx, "range"]
        efficiency = catalogue_data.at[idx, "efficiency"]
        nominal_power = int(catalogue_data.at[idx, "sn"] / 1000)

        # Get the data from the Json file
        path = cls.catalogue_path() / manufacturer / range / efficiency / f"{nominal_power}.json"
        if not path.exists():  # pragma: no cover
            msg = f"The file {path} has not been found while it should exist. Please post an issue on GitHub."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.CATALOGUE_MISSING)

        return cls.from_json(path=path)

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, "VA", "V", "V"), strict=False)
    def print_catalogue(
        cls,
        id: Optional[Union[str, re.Pattern[str]]] = None,
        manufacturer: Optional[Union[str, re.Pattern[str]]] = None,
        range: Optional[Union[str, re.Pattern[str]]] = None,
        efficiency: Optional[Union[str, re.Pattern[str]]] = None,
        type: Optional[Union[str, re.Pattern[str]]] = None,
        sn: Optional[float] = None,
        uhv: Optional[float] = None,
        ulv: Optional[float] = None,
    ) -> None:
        """Print the catalogue of available transformers.

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
        """
        # Get the catalogue data
        catalogue_data = cls.catalogue_data()

        # Start creating a table to display the results
        table = Table(title="Available Transformer Parameters")
        table.add_column("Id")
        table.add_column("Manufacturer", style="color(1)", header_style="color(1)")
        table.add_column("Product range", style="color(2)", header_style="color(2)")
        table.add_column("Efficiency", style="color(3)", header_style="color(3)")
        table.add_column("Type", style="color(4)", header_style="color(4)")
        table.add_column("Nominal power (kVA)", justify="right", style="color(5)", header_style="color(5)")
        table.add_column("High voltage (kV)", justify="right", style="color(6)", header_style="color(6)")
        table.add_column("Low voltage (kV)", justify="right", style="color(9)", header_style="color(9)")
        empty_table = True

        # Match on the manufacturer, range, efficiency and type
        catalogue_mask = pd.Series(True, index=catalogue_data.index)
        query_msg_list = []
        for value, column_name in (
            (id, "id"),
            (manufacturer, "manufacturer"),
            (range, "range"),
            (efficiency, "efficiency"),
            (type, "type"),
        ):
            if pd.isna(value):
                continue
            catalogue_mask &= cls._filter_catalogue_str(
                value=value, catalogue_data=catalogue_data, column_name=column_name
            )
            query_msg_list.append(f"{column_name}={value!r}")

        # Mask on nominal power, primary and secondary voltages
        for value, column_name, display_unit in ((uhv, "uhv", "kV"), (ulv, "ulv", "kV"), (sn, "sn", "kVA")):
            if pd.isna(value):
                continue
            catalogue_mask &= cls._filter_catalogue_float(
                value=value, catalogue_data=catalogue_data, column_name=column_name
            )
            query_msg_list.append(f"{column_name}={value/1000:.1f} {display_unit}")

        # Iterate over the transformers
        selected_index = catalogue_mask[catalogue_mask].index
        for idx in selected_index:
            empty_table = False
            table.add_row(
                catalogue_data.at[idx, "id"],
                catalogue_data.at[idx, "manufacturer"],
                catalogue_data.at[idx, "range"],
                catalogue_data.at[idx, "efficiency"],
                catalogue_data.at[idx, "type"],
                f"{catalogue_data.at[idx, 'sn']/1000:.1f}",  # VA to kVA
                f"{catalogue_data.at[idx, 'uhv']/1000:.1f}",  # V to kV
                f"{catalogue_data.at[idx, 'ulv']/1000:.1f}",  # V to kV
            )

        # Handle the case of an empty table
        if empty_table:
            query_msg_part = ", ".join(query_msg_list)
            msg = f"No transformers can be found in the catalogue matching your query: {query_msg_part}."
            console.print(msg)
        else:
            console.print(table)

    @staticmethod
    def _filter_catalogue_str(
        value: Union[str, re.Pattern[str]], catalogue_data: pd.DataFrame, column_name: str
    ) -> pd.Series:
        """Filter the catalogue using a string/regexp value.

        Args:
            value:
                The string or regular expression to use as a filter.

            catalogue_data:
                The catalogue data to use.

            column_name:
                The name of the column to use for the filter.

        Returns:
            The mask of matching results.
        """
        if isinstance(value, re.Pattern):
            return catalogue_data[column_name].str.match(value)
        else:
            try:
                pattern = re.compile(pattern=value, flags=re.IGNORECASE)
                return catalogue_data[column_name].str.match(pattern)
            except re.error:
                return catalogue_data[column_name].str.lower() == value.lower()

    @staticmethod
    def _filter_catalogue_float(value: float, catalogue_data: pd.DataFrame, column_name: str) -> pd.Series:
        """Filter the catalogue using a float/int value.

        Args:
            value:
                The float or integer to use as a filter.

            catalogue_data:
                The catalogue data to use.

            column_name:
                The name of the column to use for the filter.

        Returns:
            The mask of matching results.
        """
        if isinstance(value, int):
            return catalogue_data[column_name] == value
        else:
            return np.isclose(catalogue_data[column_name], value)

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
