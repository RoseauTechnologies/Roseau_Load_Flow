import cmath
import logging
import re
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, NoReturn, Self, TypeVar

import numpy as np
import pandas as pd

from roseau.load_flow import Insulator, LineType, Material, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow import LineParameters as MultiLineParameters
from roseau.load_flow.constants import F
from roseau.load_flow.typing import Complex, Float, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import CatalogueMixin, Identifiable, JsonMixin

logger = logging.getLogger(__name__)

_StrEnumT = TypeVar("_StrEnumT", bound=StrEnum)


class LineParameters(Identifiable, JsonMixin, CatalogueMixin[pd.DataFrame]):
    """Parameters that define electrical models of lines."""

    is_multi_phase: Final = False

    @ureg_wraps(None, (None, None, "ohm/km", "S/km", "A", None, None, None, "mm**2"))
    def __init__(
        self,
        id: Id,
        z_line: Complex | Q_[Complex],
        y_shunt: Complex | Q_[Complex] | None = None,
        ampacity: Float | Q_[Float] | None = None,
        line_type: LineType | str | None = None,
        material: Material | str | None = None,
        insulator: Insulator | str | None = None,
        section: Float | Q_[Float] | None = None,
    ) -> None:
        """LineParameters constructor.

        Args:
            id:
                A unique ID of the line parameters, typically its canonical name.

            z_line:
                 The Z of the line (Ohm/km).

            y_shunt:
                The Y of the line (Siemens/km). This field is optional if the line has no shunt part.

            ampacity:
                The ampacity of the line (A). The ampacity is optional, it is
                not used in the load flow but can be used to check for overloading.
                See also :meth:`Line.res_violated <roseau.load_flow_single.Line.res_violated>`.

            line_type:
                The type of the line (overhead, underground, twisted). The line type is optional,
                it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            material:
                The type of the conductor material (Aluminum, Copper, ...). The material is
                optional, it is informative only and are not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            insulator:
                The type of the cable insulator (PVC, XLPE, ...). The insulator is optional,
                it is informative only and are not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            section:
                The section of the conductor. The section is optional, it is informative only and is not used in
                the load flow. This field gets automatically filled when the line parameters are created from a
                geometric model or from the catalogue.
        """
        super().__init__(id)
        self._z_line = self._check_value(id=id, value=z_line, name="z_line")
        if y_shunt is None:
            self._y_shunt = 0j
            self._with_shunt = False
        else:
            self._y_shunt = self._check_value(id=id, value=y_shunt, name="y_shunt")
            self._with_shunt = not cmath.isclose(self._y_shunt, 0)

        # Parameters that are not used in the load flow
        self.line_type = line_type
        self.ampacity = ampacity
        self.material = material
        self.insulator = insulator
        self.section = section

        self._elements = set()  # Set of elements using this line parameters object

    def __repr__(self) -> str:
        s = f"<{type(self).__name__}: id={self.id!r}"
        if self._line_type is not None:
            s += f", line_type='{self._line_type!s}'"
        if self._insulator is not None:
            s += f", insulator='{self._insulator!s}'"
        if self._material is not None:
            s += f", material='{self._material!s}'"
        if self._section is not None:
            s += f", section={self._section}"
        if self._ampacity is not None:
            s += f", ampacity={self._ampacity}"
        s += ">"
        return s

    @property
    @ureg_wraps("ohm/km", (None,))
    def z_line(self) -> Q_[complex]:
        """The impedance matrix of the line."""
        return self._z_line

    @property
    @ureg_wraps("S/km", (None,))
    def y_shunt(self) -> Q_[complex]:
        """The shunt admittance matrix of the line."""
        return self._y_shunt

    @property
    def with_shunt(self) -> bool:
        """`True` if the shunt admittance matrix is not null."""
        return self._with_shunt

    @property
    def line_type(self) -> LineType | None:
        """The type of the line. Informative only, it has no impact on the load flow."""
        return self._line_type

    @line_type.setter
    def line_type(self, value: LineType | str | None) -> None:
        self._line_type = self._check_str_enum(
            value, enum_class=LineType, error_code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE
        )

    @property
    def material(self) -> Material | None:
        """The material of the conductor. Informative only, it has no impact on the load flow."""
        return self._material

    @material.setter
    def material(self, value: Material | str | None) -> None:
        self._material = self._check_str_enum(
            value, enum_class=Material, error_code=RoseauLoadFlowExceptionCode.BAD_MATERIAL
        )

    @property
    def insulator(self) -> Insulator | str | None:
        """The insulator of the conductor. Informative only, it has no impact on the load flow."""
        return self._insulator

    @insulator.setter
    def insulator(self, value: Insulator | str | None) -> None:
        self._insulator = self._check_str_enum(
            value, enum_class=Insulator, error_code=RoseauLoadFlowExceptionCode.BAD_INSULATOR
        )

    @property
    def section(self) -> Q_[float] | None:
        """The cross-section of the cable (mm²). Informative only, it has no impact on the load flow."""
        return None if self._section is None else Q_(self._section, "mm**2")

    @section.setter
    @ureg_wraps(None, (None, "mm**2"))
    def section(self, value: Float | Q_[Float] | None) -> None:
        self._section = self._check_positive_float(value=value, name="section", unit="mm²")

    @property
    def ampacity(self) -> Q_[float] | None:
        """The ampacity of the line (A). Informative only, it has no impact on the load flow."""
        return None if self._ampacity is None else Q_(self._ampacity, "A")

    @ampacity.setter
    @ureg_wraps(None, (None, "A"))
    def ampacity(self, value: Float | Q_[Float] | None) -> None:
        self._ampacity = self._check_positive_float(value=value, name="ampacity", unit="A")

    @classmethod
    @ureg_wraps(None, (None, None, "ohm/km", "ohm/km", "S/km", "S/km", "A"))
    def from_sym(
        cls,
        id: Id,
        z0: Complex | Q_[Complex],
        z1: Complex | Q_[Complex],
        y0: Complex | Q_[Complex],
        y1: Complex | Q_[Complex],
        ampacity: Float | Q_[Float] | None = None,
    ) -> Self:
        """Create line parameters from a symmetric model.

        Args:
            id:
                A unique ID of the line parameters, typically its canonical name.

            z0:
                Impedance - zero sequence - :math:`r_0+x_0\\cdot j` (ohms/km)

            z1:
                Impedance - direct sequence - :math:`r_1+x_1\\cdot j` (ohms/km)

            y0:
                Admittance - zero sequence - :math:`g_0+b_0\\cdot j` (Siemens/km)

            y1:
                Conductance - direct sequence - :math:`g_1+b_1\\cdot j` (Siemens/km)

            ampacity
                An optional ampacity for the line parameters (A). It is not used in the load flow.

        Returns:
            The created line parameters.
        """
        zs = (z0 + 2 * z1) / 3
        ys = (y0 + 2 * y1) / 3
        return cls(id=id, z_line=zs, y_shunt=ys, ampacity=ampacity)

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, None, "mm**2", "mm**2", "m", "m", "A"))
    def from_geometry(
        cls,
        id: Id,
        *,
        line_type: LineType,
        material: Material | None = None,
        material_neutral: Material | None = None,
        insulator: Insulator | None = None,
        insulator_neutral: Insulator | None = None,
        section: Float | Q_[Float],
        section_neutral: Float | Q_[Float] | None = None,
        height: Float | Q_[Float],
        external_diameter: Float | Q_[Float],
        ampacity: Float | Q_[Float] | None = None,
    ) -> Self:
        """Create line parameters from its geometry.

        Args:
            id:
                The id of the line parameters type.

            line_type:
                Overhead or underground. See also :class:`~roseau.load_flow_single.LineType`.

            material:
                Material of the conductor. If ``None``, ``ACSR`` is used for overhead lines and  ``AL``
                for underground or twisted lines. See also :class:`~roseau.load_flow_single.Material`.

            material_neutral:
                Material of the conductor If ``None``, it will be the same as the insulator of the
                other phases.

            insulator:
                Type of insulator. If ``None``, ``XLPE`` is used for twisted lines and ``PVC`` for
                underground lines. See also :class:`~roseau.load_flow_single.Insulator`. Please provide
                :attr:`~roseau.load_flow_single.Insulator.NONE` for cable without insulator.

            insulator_neutral:
                Type of insulator. If ``None``, it will be the same as the insulator of the other phases. See also
                :class:`~roseau.load_flow_single.Insulator`. Please provide :attr:`~roseau.load_flow_single.Insulator.NONE` for
                cable without insulator.

            section:
                Cross-section surface area of the phases (mm²).

            section_neutral:
                Cross-section surface area of the neutral (mm²). If ``None`` it will be the same as the
                section of the other phases.

            height:
                Height of the line (m). It must be positive for overhead lines and negative for
                underground lines.

            external_diameter:
                External diameter of the cable (m).

            ampacity:
                An optional ampacity of the phases of the line (A). It is not used in the load flow.

        Returns:
            The created line parameters.

        See Also:
            :ref:`Line parameters alternative constructor documentation <models-line_parameters-alternative_constructors>`
        """
        parameters = MultiLineParameters.from_geometry(
            id=id,
            line_type=line_type,
            material=material,
            material_neutral=material_neutral,
            insulator=insulator,
            insulator_neutral=insulator_neutral,
            section=section,
            section_neutral=section_neutral,
            height=height,
            external_diameter=external_diameter,
            ampacity=ampacity,
        )
        return cls.from_roseau_load_flow(parameters=parameters)

    @classmethod
    def from_coiffier_model(cls, name: str, id: Id | None = None) -> Self:
        """Get the electrical parameters of a MV line using Alain Coiffier's method (France specific model).

        Args:
            name:
                The canonical name of the line parameters. It must be in the format
                `LineType_Material_CrossSection`. E.g. "U_AL_150".

            id:
                A unique ID for the created line parameters object (optional). If ``None``
                (default), the id of the created object will be the canonical name.

        Returns:
            The corresponding line parameters.
        """
        parameters = MultiLineParameters.from_coiffier_model(name=name, id=id)
        return cls.from_roseau_load_flow(parameters=parameters)

    #
    # Constructors from other software
    #
    @classmethod
    def from_roseau_load_flow(cls, parameters: MultiLineParameters) -> Self:
        """Create a *Roseau Load Flow Single* line parameters from a multiphase *Roseau Load Flow* line parameter.

        Args:
            parameters:
                The multiphase line parameter.

        Returns:
            The single phase line parameter
        """
        materials = parameters.materials
        sections = parameters.sections
        insulators = parameters.insulators
        ampacities = parameters.ampacities

        return cls(
            id=parameters.id,
            z_line=parameters.z_line[0, 0],
            y_shunt=parameters.y_shunt[0, 0],
            line_type=parameters.line_type,
            material=materials[0] if materials is not None else None,
            section=sections[0] if sections is not None else None,
            insulator=insulators[0] if insulators is not None else None,
            ampacity=ampacities[0] if ampacities is not None else None,
        )

    @classmethod
    @ureg_wraps(
        None, (None, None, "ohm/km", "ohm/km", "ohm/km", "ohm/km", "µS/km", "µS/km", "kA", None, None, None, "mm**2")
    )
    def from_power_factory(
        cls,
        id: Id,
        *,
        r0: Float | Q_[Float],
        r1: Float | Q_[Float],
        x0: Float | Q_[Float],
        x1: Float | Q_[Float],
        b0: Float | Q_[Float],
        b1: Float | Q_[Float],
        inom: Float | Q_[Float] | None = None,
        cohl: Literal[0, "Cable", 1, "OHL"] = "Cable",
        conductor: Literal["Al", "Cu", "Ad", "As", "Ds"] | None = None,
        insulation: Literal[0, "PVC", 1, "XLPE", 2, "Mineral", 3, "Paper", 4, "EPR"] | None = None,
        section: Float | Q_[Float] | None = None,
    ) -> Self:
        """Create a line parameters object from PowerFactory "TypLne" data.

        Args:
            id:
                A unique ID of the line parameters.

            r0:
                PwF parameter `rline0` (AC-Resistance R0'). Zero sequence resistance in (ohms/km).

            r1:
                PwF parameter `rline` (AC-Resistance R1'). Direct sequence resistance in (ohms/km).

            x0:
                PwF parameter `xline0` (Reactance X0'). Zero sequence reactance in (ohms/km).

            x1:
                PwF parameter `xline` (Reactance X1'). Direct sequence reactance in (ohms/km).

            b0:
                PwF parameter `bline0` (Susceptance B0'). Zero sequence susceptance in (µS/km).

            b1:
                PwF parameter `bline` (Susceptance B'). Direct sequence susceptance in (µS/km).

            cohl:
                PwF parameter `cohl_` (Cable/OHL). The type of the line; `'Cable'` or `0` mean an
                underground cable and `'OHL'` or `1` mean an overhead line.

            inom:
                PwF parameter `sline` or `InomAir` (Rated Current in ground or in air). The rated
                current in (kA) of the line. It is used as the ampacity for analysis of network
                constraint violations. Pass the `sline` parameter if the line is an underground
                cable (cohl='Cable') or the `InomAir` parameter if the line is an overhead line
                (cohl='OHL').

            conductor:
                PwF parameter `mlei` (Conductor Material). The material used for the conductors.
                It can be one of: `'Al'` (Aluminium), `'Cu'` (Copper), `'Ad'` (Aldrey AlMgSi),
                `'As'` (Aluminium-Steel), `'Ds'` (Aldrey-Steel).

            insulation:
                PwF parameter `imiso` (Insulation Material). The material used for the conductor's
                insulation. It can be one of `'PVC'` (`0`), `'XLPE'` (`1`), `'Mineral'` (`2`),
                `'Paper'` (`3`) or `'EPR'` (`4`). If ``None`` is provided, the insulation is not filled in the
                resulting instance.

            section:
                PwF parameter `qurs` (Nominal Cross-Section). The nominal cross-sectional area of
                the conductors in (mm²).

        Returns:
            The created line parameters.
        """
        parameters = MultiLineParameters.from_power_factory(
            id=id,
            r0=r0,
            r1=r1,
            x0=x0,
            x1=x1,
            b0=b0,
            b1=b1,
            inom=inom,
            cohl=cohl,
            conductor=conductor,
            insulation=insulation,
            section=section,
            nphase=1,
            nneutral=0,
        )
        return cls.from_roseau_load_flow(parameters=parameters)

    @classmethod
    @ureg_wraps(None, (None, None, "ohm/km", "ohm/km", "ohm/km", "ohm/km", "nF/km", "nF/km", "Hz", "A", None))
    def from_open_dss(
        cls,
        id: Id,
        *,
        r1: Float | Q_[Float],
        r0: Float | Q_[Float],
        x1: Float | Q_[Float],
        x0: Float | Q_[Float],
        c1: Float | Q_[Float] = 3.4,  # default value used in OpenDSS
        c0: Float | Q_[Float] = 1.6,  # default value used in OpenDSS
        basefreq: Float | Q_[Float] = F,
        normamps: Float | Q_[Float] | None = None,
        linetype: str | None = None,
    ) -> Self:
        """Create a line parameters object from OpenDSS "LineCode" data.

        Args:
            id:
                The unique ID of the line parameters.

            r1:
                OpenDSS parameter: `R1`. Positive-sequence resistance in (ohm/km).

            r0:
                OpenDSS parameter: `R0`. Positive-sequence resistance in (ohm/km).

            x1:
                OpenDSS parameter: `X1`. Positive-sequence reactance in (ohm/km).

            x0:
                OpenDSS parameter: `X0`. Positive-sequence reactance in (ohm/km).

            c1:
                OpenDSS parameter: `C1`. Positive-sequence capacitance in (nF/km).

            c0:
                OpenDSS parameter: `C0`. Positive-sequence capacitance in (nF/km).

            basefreq:
                OpenDSS parameter: `BaseFreq`. Frequency at which impedances are specified (Hz).
                Defaults to 50 Hz.

            normamps:
                OpenDSS parameter: `NormAmps`. Normal ampere limit on line (A). This is the so-called
                Planning Limit. It may also be the value above which load will have to be dropped
                in a contingency. Usually about 75% - 80% of the emergency (one-hour) rating.
                This value is passed to `ampacity` and used for violation checks.

            linetype:
                OpenDSS parameter: `LineType`. Code designating the type of line. Only ``"OH"``
                (overhead) and ``"UG"`` (underground) are currently supported.

        Returns:
            The corresponding line parameters object.

        Example usage::

            # DSS command: `New linecode.240sq nphases=3 R1=0.127 X1=0.072 R0=0.342 X0=0.089 units=km`
            lp = LineParameters.from_open_dss(
                id="linecode-240sq",
                r1=Q_(0.127, "ohm/km"),
                x1=Q_(0.072, "ohm/km"),
                r0=Q_(0.342, "ohm/km"),
                x0=Q_(0.089, "ohm/km"),
                c1=Q_(3.4, "nF/km"),  # default value used in OpenDSS code
                c0=Q_(1.6, "nF/km"),  # default value used in OpenDSS code
            )

            # DSS command: `New LineCode.16sq NPhases=1 R1=0.350, X1=0.025, R0=0.366, X0=0.025, C1=1.036, C0=0.488 Units=kft NormAmps=400`
            lp = LineParameters.from_open_dss(
                id="linecode-16sq",
                r1=Q_(0.350, "ohm/kft"),
                x1=Q_(0.025, "ohm/kft"),
                r0=Q_(0.366, "ohm/kft"),
                x0=Q_(0.025, "ohm/kft"),
                c1=Q_(1.036, "nF/kft"),
                c0=Q_(0.488, "nF/kft"),
                normamps=Q_(400, "A"),
            )
        """
        parameters = MultiLineParameters.from_open_dss(
            id=id,
            r1=r1,
            r0=r0,
            x1=x1,
            x0=x0,
            c1=c1,
            c0=c0,
            basefreq=basefreq,
            normamps=normamps,
            linetype=linetype,
            nphases=1,
        )
        return cls.from_roseau_load_flow(parameters=parameters)

    #
    # Catalogue Mixin
    #
    @classmethod
    def catalogue_path(cls) -> Path:
        return MultiLineParameters.catalogue_path()

    @classmethod
    def catalogue_data(cls) -> pd.DataFrame:
        # TODO: Delete from the catalogue of RLF lines with a different neutral section to only keep one version of
        #  each. Currently, all the lines have the same phase section and neutral section

        return MultiLineParameters.catalogue_data().drop(
            columns=[
                "resistance_neutral",
                "reactance_neutral",
                "susceptance_neutral",
                "ampacity_neutral",
                "material_neutral",
                "insulator_neutral",
                "section_neutral",
            ]
        )

    @classmethod
    def _get_catalogue(
        cls,
        name: str | re.Pattern[str] | None,
        line_type: LineType | str | None,
        material: Material | str | None,
        insulator: Insulator | str | None,
        section: Float | None,
        raise_if_not_found: bool,
    ) -> tuple[pd.DataFrame, str]:
        catalogue_data = cls.catalogue_data()

        # Filter on strings/regular expressions
        query_msg_list = []
        for value, column_name, display_name, display_name_plural in [
            (name, "name", "name", "names"),
        ]:
            if pd.isna(value):
                continue

            mask = cls._filter_catalogue_str(value, strings=catalogue_data[column_name])
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

        # Filter on enumerated types
        for value, column_name, display_name, enum_class in (
            (line_type, "type", "line_type", LineType),
            (material, "material", "material", Material),
            (insulator, "insulator", "insulator", Insulator),
        ):
            if pd.isna(value):
                continue

            enum_series = pd.Series(
                data=[
                    None if isna else enum_class(x)
                    for isna, x in zip(
                        catalogue_data[column_name].isna(), catalogue_data[column_name].values, strict=True
                    )
                ],
                index=catalogue_data.index,
            )
            try:
                mask = enum_series == enum_class(value)
            except ValueError:
                mask = pd.Series(data=False, index=catalogue_data.index)
            if raise_if_not_found and mask.sum() == 0:
                cls._raise_not_found_in_catalogue(
                    value=repr(value),
                    name=display_name,
                    name_plural=display_name + "s",
                    strings=enum_series,
                    query_msg_list=query_msg_list,
                )
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{display_name}={value!r}")

        # Filter on floats
        for value, column_name, display_name, display_name_plural, unit in [
            (section, "section", "cross-section", "cross-sections", "mm²"),
        ]:
            if value is None:
                continue

            mask = np.isclose(catalogue_data[column_name], value)
            if raise_if_not_found and mask.sum() == 0:
                cls._raise_not_found_in_catalogue(
                    value=f"{value:.1f} {unit}",
                    name=display_name,
                    name_plural=display_name_plural,
                    strings=catalogue_data[column_name].apply(lambda x: f"{x:.1f} {unit}"),  # noqa: B023
                    query_msg_list=query_msg_list,
                )
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{display_name}={value!r} {unit}")

        return catalogue_data, ", ".join(query_msg_list)

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, "mm**2", None))
    def from_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        line_type: LineType | str | None = None,
        material: Material | str | None = None,
        insulator: Insulator | str | None = None,
        section: Float | Q_[Float] | None = None,
        id: Id | None = None,
    ) -> Self:
        """Create line parameters from a catalogue.

        Args:
            name:
                The name of the line parameters to get from the catalogue. It can be a regular
                expression.

            line_type:
                The type of the line parameters to get. It can be ``"overhead"``, ``"twisted"``, or
                ``"underground"``. See also :class:`~roseau.load_flow_single.LineType`.

            material:
                The type of the conductor material (Al, Cu, ...) of the phases. See also
                :class:`~roseau.load_flow_single.Material`.

            insulator:
                The insulator of the phases. See also :class:`~roseau.load_flow_single.Insulator`. Please provide
                :attr:`~roseau.load_flow_single.Insulator.NONE` for cable without insulator.

            section:
                The cross-section surface area of the phases (mm²).

            id:
                A unique ID for the created line parameters object (optional). If ``None``
                (default), the id of the created object will be its name in the catalogue. Note
                that this parameter is not used in the data filtering.

        Returns:
            The created line parameters.
        """
        catalogue_data, query_info = cls._get_catalogue(
            name=name,
            line_type=line_type,
            material=material,
            insulator=insulator,
            section=section,
            raise_if_not_found=True,
        )

        try:
            cls._assert_one_found(
                found_data=catalogue_data["name"].tolist(), display_name="line parameters", query_info=query_info
            )
        except RoseauLoadFlowException as e:
            if name is None and id is not None:
                e.msg += " Did you mean to filter by name instead of id?"
            raise
        idx = catalogue_data.index[0]
        name = str(catalogue_data.at[idx, "name"])
        r = catalogue_data.at[idx, "resistance"]
        x = catalogue_data.at[idx, "reactance"]
        b = catalogue_data.at[idx, "susceptance"]
        line_type = LineType(catalogue_data.at[idx, "type"])
        material = Material(catalogue_data.at[idx, "material"])
        insulator = catalogue_data.at[idx, "insulator"]  # Converted in the LineParameters creator
        section = catalogue_data.at[idx, "section"]
        ampacity = catalogue_data.at[idx, "ampacity"]
        if pd.isna(ampacity):
            ampacity = None
        z_line = r + x * 1j
        y_shunt = b * 1j
        if id is None:
            id = name
        return cls(
            id=id,
            z_line=z_line,
            y_shunt=y_shunt,
            ampacity=ampacity,
            line_type=line_type,
            material=material,
            insulator=insulator,
            section=section,
        )

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, "mm**2"))
    def get_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        line_type: LineType | str | None = None,
        material: Material | str | None = None,
        insulator: Insulator | str | None = None,
        section: Float | Q_[Float] | None = None,
    ) -> pd.DataFrame:
        """Get the catalogue of available lines.

        You can use the parameters below to filter the catalogue. If you do not specify any
        parameter, all the catalogue will be returned.

        Args:
            name:
                The name of the line parameters to get from the catalogue. It can be a regular
                expression.

            line_type:
                The type of the line parameters to get. It can be ``"overhead"``, ``"twisted"``, or
                ``"underground"``. See also :class:`~roseau.load_flow_single.LineType`.

            material:
                The type of the conductor material (Al, Cu, ...) of the phases. See also
                :class:`~roseau.load_flow_single.Material`.

            insulator:
                The insulator of the phases. See also :class:`~roseau.load_flow_single.Insulator`. Please provide
                :attr:`~roseau.load_flow_single.Insulator.NONE` for cable without insulator.

            section:
                The cross-section surface area of the phases (mm²).

        Returns:
            The catalogue data as a dataframe.
        """
        catalogue_data, _ = cls._get_catalogue(
            name=name,
            line_type=line_type,
            material=material,
            insulator=insulator,
            section=section,
            raise_if_not_found=False,
        )
        return catalogue_data.rename(
            columns={
                "name": "Name",
                "resistance": "Phase resistance (ohm/km)",
                "reactance": "Phase reactance (ohm/km)",
                "susceptance": "Phase susceptance (S/km)",
                "ampacity": "Phase ampacity (A)",
                "type": "Line type",
                "material": "Phase material",
                "insulator": "Phase insulator",
                "section": "Phase cross-section (mm²)",
            }
        ).set_index("Name")

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        """Line parameters constructor from dict.

        Args:
            data:
                The dictionary data of the line parameters.

            include_results:
                If True (default) and the results of the load flow are included in the dictionary,
                the results are also loaded into the element. Useless here as line parameters don't contain results.

        Returns:
            The created line parameters.
        """
        z_line = complex(data["z_line"][0], data["z_line"][1])
        y_shunt = complex(data["y_shunt"][0], data["y_shunt"][1]) if "y_shunt" in data else None
        return cls(
            id=data["id"],
            z_line=z_line,
            y_shunt=y_shunt,
            ampacity=data.get("ampacity"),
            line_type=data.get("line_type"),
            material=data.get("material"),
            insulator=data.get("insulator"),
            section=data.get("section"),
        )

    def _to_dict(self, include_results: bool) -> JsonDict:
        data = {"id": self.id, "z_line": [self._z_line.real, self._z_line.imag]}
        if self._with_shunt:
            data["y_shunt"] = [self._y_shunt.real, self._y_shunt.imag]
        if self._ampacity is not None:
            data["ampacity"] = self._ampacity
        if self._line_type is not None:
            data["line_type"] = self._line_type.name
        if self._material is not None:
            data["material"] = self._material.name
        if self._insulator is not None:
            data["insulator"] = self._insulator.name
        if self._section is not None:
            data["section"] = self._section
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    #
    # Utilities
    #
    @staticmethod
    def _check_value(id: Id, value: Complex, name: Literal["z_line", "y_shunt"]) -> complex:
        """Check the z_line and y_shunt values."""
        # Check that the real coefficients are non-negative
        if value.real < 0.0:
            msg = f"The {name} value of line type {id!r} has coefficients with negative real part."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{name.upper()}_VALUE"])

        # Ensure that z_line is not 0
        if name == "z_line" and cmath.isclose(value, 0):
            msg = f"The z_line value of line type {id!r} can't be zero."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE)
        return complex(value)

    @staticmethod
    def _check_positive_float(value: Float | None, name: Literal["section", "ampacity"], unit: str) -> float | None:
        value_isna = pd.isna(value)
        if value_isna:
            return None
        elif value <= 0:
            msg = f"{name.title()} must be positive: {value} {unit} was provided."
            logger.error(msg)
            error_code = (
                RoseauLoadFlowExceptionCode.BAD_AMPACITIES_VALUE
                if name == "ampacity"
                else RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE
            )
            raise RoseauLoadFlowException(msg=msg, code=error_code)
        else:
            return float(value)

    @staticmethod
    def _check_str_enum(value: _StrEnumT | str | None, enum_class: type[_StrEnumT], error_code) -> _StrEnumT | None:
        if pd.isna(value):
            return None
        try:
            return enum_class(value)
        except ValueError as e:
            msg = str(e)
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=error_code) from None
