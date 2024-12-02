import logging
import re
import warnings
from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from typing import Literal, NoReturn, TypeAlias, TypeVar

import numpy as np
import numpy.linalg as nplin
import pandas as pd
from numpy._typing import NDArray
from typing_extensions import Self

from roseau.load_flow._compat import StrEnum
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import (
    ComplexArray,
    ComplexArrayLike2D,
    Float,
    FloatArray,
    FloatScalarOrArrayLike1D,
    Id,
    JsonDict,
)
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import (
    EPSILON_0,
    EPSILON_R,
    MU_0,
    OMEGA,
    PI,
    RHO,
    TAN_D,
    CatalogueMixin,
    F,
    Identifiable,
    Insulator,
    JsonMixin,
    LineType,
    Material,
)
from roseau.load_flow.utils._exceptions import find_stack_level

logger = logging.getLogger(__name__)

_DEFAULT_MATERIAL = {
    LineType.OVERHEAD: Material.ACSR,
    LineType.TWISTED: Material.AL,
    LineType.UNDERGROUND: Material.AL,
}

_DEFAULT_INSULATOR = {
    LineType.OVERHEAD: Insulator.NONE,  # Not used for overhead lines
    LineType.TWISTED: Insulator.XLPE,
    LineType.UNDERGROUND: Insulator.PVC,
}

MaterialArray: TypeAlias = NDArray[Material]
InsulatorArray: TypeAlias = NDArray[Insulator]
_StrEnumType: TypeAlias = TypeVar("_StrEnumType", bound=StrEnum)


class LineParameters(Identifiable, JsonMixin, CatalogueMixin[pd.DataFrame]):
    """Parameters that define electrical models of lines."""

    _type_re = "|".join(x.code() for x in LineType)
    _material_re = "|".join(x.code() for x in Material)
    _insulator_re = "|".join(x.code() for x in Insulator)
    _section_re = r"[1-9][0-9]*"
    _REGEXP_LINE_TYPE_NAME = re.compile(
        rf"^({_type_re})_({_material_re})_({_insulator_re}_)?{_section_re}$", flags=re.IGNORECASE
    )

    @ureg_wraps(None, (None, None, "ohm/km", "S/km", "A", None, None, None, "mm²"))
    def __init__(
        self,
        id: Id,
        z_line: ComplexArrayLike2D,
        y_shunt: ComplexArrayLike2D | None = None,
        ampacities: FloatScalarOrArrayLike1D | None = None,
        line_type: LineType | None = None,
        materials: Material | Sequence[Material] | None = None,
        insulators: Insulator | Sequence[Insulator] | None = None,
        sections: FloatScalarOrArrayLike1D | None = None,
    ) -> None:
        """LineParameters constructor.

        Args:
            id:
                A unique ID of the line parameters, typically its canonical name.

            z_line:
                 The Z matrix of the line (Ohm/km).

            y_shunt:
                The Y matrix of the line (Siemens/km). This field is optional if the line has no shunt part.

            ampacities:
                The ampacities of the line (A). The ampacities are optional, they are
                not used in the load flow but can be used to check for overloading.
                See also :meth:`Line.res_violated <roseau.load_flow.Line.res_violated>`.

                When a scalar value is provided, it creates an array with the same ampacity for each conductor.
                The scalar value passed is assumed to be the ampacity of each conductor. To create a
                different ampacity per conductor, provide a vector of current values with the same length as
                the number of conductor of the line.

            line_type:
                The type of the line (overhead, underground, twisted). The line type is optional,
                it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            materials:
                The types of the conductor material (Aluminum, Copper, ...). The materials are
                optional, they are informative only and are not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            insulators:
                The types of the cable insulator (PVC, XLPE, ...). The insulators are optional,
                they are informative only and are not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            sections:
                The sections of the conductor. The sections are optional, thy are informative only and are not used in
                the load flow. This field gets automatically filled when the line parameters are created from a
                geometric model or from the catalogue.

                When a scalar value is provided, it creates an array with the same section for each conductor. To
                create different sections per conductor, provide a vector of section values with the same length as
                the number of conductor of the line.
        """
        super().__init__(id)
        self._z_line = np.array(z_line, dtype=np.complex128)
        if y_shunt is None:
            self._with_shunt = False
            self._y_shunt = np.zeros_like(self._z_line, dtype=np.complex128)
        else:
            self._with_shunt = not np.allclose(y_shunt, 0)
            self._y_shunt = np.array(y_shunt, dtype=np.complex128)
        self._size = self._z_line.shape[0]
        self._ampacities = None
        self.ampacities = ampacities
        self._line_type = None if pd.isna(line_type) else LineType(line_type)
        self._materials = None
        self.materials = materials
        self._insulators = None
        self.insulators = insulators
        self._sections = None
        self.sections = sections
        self._check_matrix()

    def __repr__(self) -> str:
        s = f"<{type(self).__name__}: id={self.id!r}"
        if self._line_type is not None:
            s += f", line_type={str(self._line_type)!r}"
        if self._insulators is not None:
            s += f", insulators={self._insulators}"
        if self._materials is not None:
            s += f", materials={self._materials}"
        if self._sections is not None:
            s += f", sections={self._sections}"
        if self._ampacities is not None:
            s += f", ampacities={self._ampacities}"
        s += ">"
        return s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LineParameters):
            return NotImplemented
        return (
            self.id == other.id
            and self._z_line.shape == other._z_line.shape
            and np.allclose(self._z_line, other._z_line)
            and (
                (self._ampacities is None and other._ampacities is None)
                or (
                    self._ampacities is not None
                    and other._ampacities is not None
                    and self._ampacities.shape == other._ampacities.shape
                    and np.allclose(self._ampacities, other._ampacities)
                )
            )
            and self._line_type == other._line_type
            and (
                (self._materials is None and other._materials is None)
                or (
                    self._materials is not None
                    and other._materials is not None
                    and self._materials.shape == other._materials.shape
                    and np.array_equal(self._materials, other._materials)
                )
            )
            and (
                (self._insulators is None and other._insulators is None)
                or (
                    self._insulators is not None
                    and other._insulators is not None
                    and self._insulators.shape == other._insulators.shape
                    and np.array_equal(self._insulators, other._insulators)
                )
            )
            and (
                (self._sections is None and other._sections is None)
                or (
                    self._sections is not None
                    and other._sections is not None
                    and self._sections.shape == other._sections.shape
                    and np.allclose(self._sections, other._sections)
                )
            )
            and (
                (not self._with_shunt and not other._with_shunt)
                or (
                    self._with_shunt
                    and other._with_shunt
                    and self._y_shunt.shape == other._y_shunt.shape
                    and np.allclose(self._y_shunt, other._y_shunt)
                )
            )
        )

    @property
    @ureg_wraps("ohm/km", (None,))
    def z_line(self) -> Q_[ComplexArray]:
        return self._z_line

    @property
    @ureg_wraps("S/km", (None,))
    def y_shunt(self) -> Q_[ComplexArray]:
        return self._y_shunt

    @property
    def with_shunt(self) -> bool:
        return self._with_shunt

    @property
    def ampacities(self) -> Q_[FloatArray] | None:
        """The ampacities of the line (A) if it is set."""
        return None if self._ampacities is None else Q_(self._ampacities, "A")

    @property
    def line_type(self) -> LineType | None:
        """The type of the line. Informative only, it has no impact on the load flow."""
        return self._line_type

    @property
    def materials(self) -> MaterialArray | None:
        """The materials of the conductors. Informative only, it has no impact on the load flow."""
        return self._materials

    @property
    def insulators(self) -> InsulatorArray | None:
        """The insulators of the conductors. Informative only, it has no impact on the load flow."""
        return self._insulators

    @property
    def sections(self) -> Q_[FloatArray] | None:
        """The cross-section areas of the cable (in mm²). Informative only, it has no impact on the load flow."""
        return None if self._sections is None else Q_(self._sections, "mm**2")

    @ampacities.setter
    @ureg_wraps(None, (None, "A"))
    def ampacities(self, value: FloatScalarOrArrayLike1D | None) -> None:
        self._ampacities = self._check_positive_float_array(value=value, name="ampacities", unit="A", size=self._size)

    @materials.setter
    def materials(self, value: Material | Sequence[Material] | None) -> None:
        self._materials = self._check_enum_array(value=value, enum_class=Material, name="materials", size=self._size)

    @insulators.setter
    def insulators(self, value: Insulator | Sequence[Insulator] | None) -> None:
        self._insulators = self._check_enum_array(value=value, enum_class=Insulator, name="insulators", size=self._size)

    @sections.setter
    @ureg_wraps(None, (None, "mm**2"))
    def sections(self, value: FloatScalarOrArrayLike1D | None) -> None:
        self._sections = self._check_positive_float_array(value=value, name="sections", unit="mm²", size=self._size)

    @staticmethod
    def _sym_to_zy_simple(n, z0: complex, z1: complex, y0: complex, y1: complex) -> tuple[ComplexArray, ComplexArray]:
        """Symmetrical components to Z/Y matrices.

        Args:
            n:
                The number of conductors. The produced matrices are always `n x n`.

            z0, y0:
                The zero sequence impedance and admittance.

            z1, y1:
                The direct sequence impedance and admittance.

        Returns:
            The line impedance and shunt admittance matrices.
        """
        zs = (z0 + 2 * z1) / 3
        zm = (z0 - z1) / 3
        ys = (y0 + 2 * y1) / 3
        ym = (y0 - y1) / 3

        z = np.full((n, n), fill_value=zm, dtype=np.complex128)
        y = np.full((n, n), fill_value=ym, dtype=np.complex128)
        np.fill_diagonal(z, zs)
        np.fill_diagonal(y, ys)
        return z, y

    @staticmethod
    def _check_z_line_matrix(id: Id, z_line: ComplexArray) -> None:
        """Check that the z_line matrix is not singular."""
        if nplin.det(z_line) == 0:
            msg = f"The symmetric model data provided for line type {id!r} produces invalid line impedance matrix."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE)

    @classmethod
    @ureg_wraps(None, (None, None, "ohm/km", "ohm/km", "S/km", "S/km", "ohm/km", "ohm/km", "S/km", "S/km", "A"))
    def from_sym(
        cls,
        id: Id,
        z0: complex | Q_[complex],
        z1: complex | Q_[complex],
        y0: complex | Q_[complex],
        y1: complex | Q_[complex],
        zn: complex | Q_[complex] | None = None,
        xpn: float | Q_[float] | None = None,
        bn: float | Q_[float] | None = None,
        bpn: float | Q_[float] | None = None,
        ampacities: FloatScalarOrArrayLike1D | None = None,
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

            zn:
                Neutral impedance - :math:`r_{\\mathrm{n}}+x_{\\mathrm{n}}\\cdot j` (ohms/km)

            xpn:
                Phase-to-neutral reactance (ohms/km)

            bn:
                Neutral susceptance (siemens/km)

            bpn:
                Phase-to-neutral susceptance (siemens/km)

            ampacities:
                An optional ampacities loading of the line (A). It is not used in the load flow.

        Returns:
            The created line parameters.

        Notes:
            As explained in the :ref:`Line parameters alternative constructor documentation
            <models-line_parameters-alternative_constructors-symmetric>`, the model may be "degraded" if the computed
            impedance matrix is not invertible.
        """
        zpn = None if pd.isna(xpn) else 1j * xpn
        z_line, y_shunt = cls._sym_to_zy(id=id, z0=z0, z1=z1, y0=y0, y1=y1, zn=zn, zpn=zpn, bn=bn, bpn=bpn)
        return cls(id=id, z_line=z_line, y_shunt=y_shunt, ampacities=ampacities)

    @classmethod
    def _sym_to_zy(
        cls,
        id: Id,
        z0: complex,
        z1: complex,
        y0: complex,
        y1: complex,
        zn: complex | None = None,
        zpn: complex | None = None,
        bn: float | None = None,
        bpn: float | None = None,
    ) -> tuple[ComplexArray, ComplexArray]:
        """Create impedance and admittance matrix from a symmetrical model.

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

            zn:
                Neutral impedance - :math:`r_{\\mathrm{n}}+x_{\\mathrm{n}}\\cdot j` (ohms/km)

            zpn:
                Phase-to-neutral impedance (ohms/km)

            bn:
                Neutral susceptance (siemens/km)

            bpn:
                Phase-to-neutral susceptance (siemens/km)

        Returns:
            The impedance and admittance matrices.
        """
        # Check if all neutral parameters are valid
        any_neutral_na = any(pd.isna([zpn, bn, bpn, zn]))

        # Two possible choices. The first one is the best but sometimes PwF data forces us to choose the second one
        for choice in (0, 1):
            if choice == 0:
                # We trust the manual !!! can give singular matrix !!!
                z_line, y_shunt = cls._sym_to_zy_simple(n=3, z0=z0, y0=y0, z1=z1, y1=y1)
            else:
                # Do not read the manual, it is useless: in pwf we trust
                # No mutual components (z0=z1 and y0=y1)
                z_line, y_shunt = cls._sym_to_zy_simple(n=3, z0=z1, y0=y1, z1=z1, y1=y1)

            # If all the neutral data have not been filled, the matrix is a 3x3 matrix
            if not any_neutral_na:
                # Build the complex
                yn = bn * 1j  # Neutral shunt admittance (Siemens/km)
                ypn = bpn * 1j  # Phase-to-neutral shunt admittance (Siemens/km)

                if np.isclose(zpn, 0) and np.isclose(zn, 0):
                    warnings.warn(
                        f"The line model {id!r} does not have neutral elements. It will be modelled as a 3 wires line "
                        f"instead.",
                        category=UserWarning,
                        stacklevel=find_stack_level(),
                    )
                else:
                    z_line = np.pad(z_line, (0, 1), mode="constant", constant_values=zpn)
                    z_line[-1, -1] = zn
                    y_shunt = np.pad(y_shunt, (0, 1), mode="constant", constant_values=ypn)
                    y_shunt[-1, -1] = yn

            # Check the validity of the resulting matrices
            det_z = nplin.det(z_line)
            if np.isclose(abs(det_z), 0):
                if choice == 0:
                    # Warn the user that the PwF data are bad...
                    logger.warning(
                        f"The symmetric model data provided for line type {id!r} produces invalid "
                        f"line impedance matrix... It is often the case with line models coming from "
                        f"PowerFactory. Trying to handle the data in a 'degraded' line model."
                    )
                    # Go to choice == 1
                else:
                    assert choice == 1
                    msg = (
                        f"The symmetric model data provided for line type {id!r} produces invalid "
                        f"line impedance matrix."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE)
            else:
                # Break: the current choice is good!
                break

        return z_line, y_shunt

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, None, "mm**2", "mm**2", "m", "m", "A", "A"))
    def from_geometry(
        cls,
        id: Id,
        *,
        line_type: LineType,
        material: Material | None = None,
        material_neutral: Material | None = None,
        insulator: Insulator | None = None,
        insulator_neutral: Insulator | None = None,
        section: float | Q_[float],
        section_neutral: float | Q_[float] | None = None,
        height: float | Q_[float],
        external_diameter: float | Q_[float],
        ampacity: float | Q_[float] | None = None,
        ampacity_neutral: float | Q_[float] | None = None,
    ) -> Self:
        """Create line parameters from its geometry.

        Args:
            id:
                The id of the line parameters type.

            line_type:
                Overhead or underground. See also :class:`~roseau.load_flow.LineType`.

            material:
                Material of the conductor. If ``None``, ``ACSR`` is used for overhead lines and  ``AL``
                for underground or twisted lines. See also :class:`~roseau.load_flow.Material`.

            material_neutral:
                Material of the conductor If ``None``, it will be the same as the insulator of the
                other phases.

            insulator:
                Type of insulator. If ``None``, ``XLPE`` is used for twisted lines and ``PVC`` for
                underground lines. See also :class:`~roseau.load_flow.Insulator`. Please provide
                :attr:`~roseau.load_flow.Insulator.NONE` for cable without insulator.

            insulator_neutral:
                Type of insulator. If ``None``, it will be the same as the insulator of the other phases. See also
                :class:`~roseau.load_flow.Insulator`. Please provide :attr:`~roseau.load_flow.Insulator.NONE` for
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

            ampacity_neutral:
                An optional ampacity of the neutral of the line (A). It is not used in the load flow.
                If ``None`` it will be the same as the ampacity of the other phases.

        Returns:
            The created line parameters.

        See Also:
            :ref:`Line parameters alternative constructor documentation <models-line_parameters-alternative_constructors>`
        """
        z_line, y_shunt, line_type, materials, insulators, sections = cls._from_geometry(
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
        )
        ampacities = [ampacity, ampacity, ampacity, ampacity_neutral]
        return cls(
            id=id,
            z_line=z_line,
            y_shunt=y_shunt,
            ampacities=ampacities,
            line_type=line_type,
            materials=materials,
            insulators=insulators,
            sections=sections,
        )

    @classmethod
    def _from_geometry(
        cls,
        id: Id,
        line_type: LineType,
        material: Material | None,
        material_neutral: Material | None,
        insulator: Insulator | None,
        insulator_neutral: Insulator | None,
        section: float,
        section_neutral: float | None,
        height: float,
        external_diameter: float,
    ) -> tuple[ComplexArray, ComplexArray, LineType, MaterialArray, InsulatorArray, FloatArray]:
        """Create impedance and admittance matrices using a geometric model.

        Args:
            id:
                The id of the line parameters.

            line_type:
                Overhead, twisted overhead, or underground.

            material:
                Type of the conductor material (Aluminum, Copper, ...) for the phases.

            material_neutral:
                Type of the conductor material (Aluminum, Copper, ...) for the neutral. If ``None`` it will be the same
                as the material of the other phases.

            insulator:
                Type of insulator. If ``None``, ``XLPE`` is used for twisted lines and ``PVC`` for
                underground lines. See also :class:`~roseau.load_flow.Insulator`. Please provide
                :attr:`~roseau.load_flow.Insulator.NONE` for cable without insulator.

            insulator_neutral:
                Type of insulator. If ``None``, it will be the same as the insulator of the other phases. See also
                :class:`~roseau.load_flow.Insulator`. Please provide :attr:`~roseau.load_flow.Insulator.NONE` for
                cable without insulator.

            section:
                Surface of the phases (mm²).

            section_neutral:
                Surface of the neutral (mm²). If ``None`` it will be the same as the section of the
                other phases.

            height:
                Height of the line (m). Positive for overhead lines and negative for underground
                lines.

            external_diameter:
                External diameter of the wire (m).

        Returns:
            The impedance matrix, the admittance matrix, the materials array, the insulators array and
            the sections array.
        """
        # dpp = data["dpp"]  # Distance phase-to-phase (m)
        # dpn = data["dpn"]  # Distance phase-to-neutral (m)
        # dsh = data["dsh"]  # Diameter of the sheath (mm)

        line_type = LineType(line_type)
        if material is None:
            material = _DEFAULT_MATERIAL[line_type]
        if insulator is None:
            insulator = _DEFAULT_INSULATOR[line_type]
        if material_neutral is None:
            material_neutral = material
        if insulator_neutral is None:
            insulator_neutral = insulator
        if section_neutral is None:
            section_neutral = section
        material = Material(material)
        material_neutral = Material(material_neutral)
        if insulator is not None:
            insulator = Insulator(insulator)
        if insulator_neutral is not None:
            insulator_neutral = Insulator(insulator_neutral)

        # Geometric configuration
        coord, coord_prim, epsilon, epsilon_neutral = cls._get_geometric_configuration(
            line_type=line_type,
            insulator=insulator,
            insulator_neutral=insulator_neutral,
            height=height,
            external_diameter=external_diameter,
        )

        # Distance computation
        sections_mm2 = np.array([section, section, section, section_neutral], dtype=np.float64)
        sections_m2 = sections_mm2 * 1e-6  # surfaces (m2)
        radius = np.sqrt(sections_m2 / PI)  # radius (m)
        phase_radius, neutral_radius = radius[0], radius[3]
        if line_type == LineType.TWISTED:
            max_radii = external_diameter / 4
            if phase_radius + neutral_radius > max_radii:
                msg = (
                    f"Conductors too big for 'twisted' line parameter of id {id!r}. Inequality "
                    f"`neutral_radius + phase_radius <= external_diameter / 4` is not satisfied."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
        elif line_type == LineType.UNDERGROUND:
            max_radii = external_diameter / 4 * np.sqrt(2)
            if phase_radius + neutral_radius > max_radii:
                msg = (
                    f"Conductors too big for 'underground' line parameter of id {id!r}. Inequality "
                    f"`neutral_radius + phase_radius <= external_diameter * sqrt(2) / 4` is not satisfied."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            if phase_radius * 2 > max_radii:
                msg = (
                    f"Conductors too big for 'underground' line parameter of id {id!r}. Inequality "
                    f"`phase_radius*2 <= external_diameter * sqrt(2) / 4` is not satisfied."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
        else:
            pass  # TODO Overhead lines check
        gmr = radius * np.exp(-0.25)  # geometric mean radius (m)
        # distance between two wires (m)
        coord_new_dim = coord[:, None, :]
        diff = coord_new_dim - coord
        distance = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
        # distance between a wire and the image of another wire (m)
        diff = coord_new_dim - coord_prim
        distance_prim = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))

        # Useful matrices
        minus = -np.ones((4, 4), dtype=np.float64)
        np.fill_diagonal(minus, 1)

        # Electrical parameters
        materials = np.array([material, material, material, material_neutral], dtype=np.object_)
        rho = np.array([RHO[x].m for x in materials], dtype=np.float64)
        r = rho / sections_m2 * np.eye(4, dtype=np.float64) * 1e3  # resistance (ohm/km)
        np.fill_diagonal(distance, gmr)
        inductance = MU_0.m / (2 * PI) * np.log(1 / distance) * 1e3  # H/m->H/km
        np.fill_diagonal(distance, radius)
        epsilons = np.array([epsilon, epsilon, epsilon, epsilon_neutral], dtype=np.float64)
        lambdas = 1 / (2 * PI * epsilons) * np.log(distance_prim / distance)  # m/F

        # Extract the conductivity and the capacities from the lambda (potential coefficients)
        lambda_inv = nplin.inv(lambdas) * 1e3  # capacities (F/km)
        c = -lambda_inv.copy()  # capacities (F/km)
        np.fill_diagonal(c, np.einsum("ij,ij->i", lambda_inv, minus))
        g = np.zeros((4, 4), dtype=np.float64)  # conductance (S/km)
        omega = OMEGA.m
        insulators = np.array([insulator, insulator, insulator, insulator_neutral], dtype=np.object_)
        tan_d = np.array([TAN_D[x].m for x in insulators], dtype=np.float64)
        np.fill_diagonal(g, tan_d * np.einsum("ii->i", c) * omega)

        # Build the impedance and admittance matrices
        z_line = r + inductance * omega * 1j
        y = g + c * omega * 1j

        # Compute the shunt admittance matrix from the admittance matrix
        y_shunt = -(y.copy())
        np.fill_diagonal(y_shunt, np.einsum("ij->i", y))

        return z_line, y_shunt, line_type, materials, insulators, sections_mm2

    @staticmethod
    def _get_geometric_configuration(
        line_type: LineType,
        insulator: Insulator | None,
        insulator_neutral: Insulator | None,
        height: float,
        external_diameter: float,
    ) -> tuple[FloatArray, FloatArray, float, float]:
        """A utility function to retrieve the geometric configurations of the lines for the `from_geometry` method.

        Args:
            line_type:
                Overhead, twisted overhead, or underground.

            insulator:
                Type of insulator for the phases.

            insulator_neutral:
                Type of insulator for the neutral. If ``None`` it will be the same as the insulator of the other phases.

            height:
                Height of the line (m). Positive for overhead lines and negative for underground
                lines.

            external_diameter:
                External diameter of the wire (m).

        Returns:
            Four elements in a tuple:
                * the coordinates of the centers of the conductors (4x2 array)
                * the coordinates of the images of the centers of the conductors (4x2 array)
                * the permittivity for the phase insulator (F/m).
                * the permittivity for the neutral insulator (F/m).
        """
        if line_type in (LineType.OVERHEAD, LineType.TWISTED):
            # TODO This configuration is for twisted lines... Create a overhead configuration.
            if height <= 0:
                msg = f"The height of a '{line_type}' line must be a positive number."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            x = np.sqrt(3) * external_diameter / 8
            coord = np.array(
                [
                    [-x, height + external_diameter / 8],
                    [x, height + external_diameter / 8],
                    [0, height - external_diameter / 4],
                    [0, height],
                ]
            )  # m
            coord_prim = np.array(
                [
                    [-x, -height - external_diameter / 8],
                    [x, -height - external_diameter / 8],
                    [0, -height + external_diameter / 4],
                    [0, -height],
                ]
            )  # m
            epsilon = EPSILON_0.m
            epsilon_neutral = EPSILON_0.m  # TODO assume no insulator. Maybe valid for overhead but not for twisted...
        elif line_type == LineType.UNDERGROUND:
            if height >= 0:
                msg = f"The height of a '{line_type}' line must be a negative number."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            x = np.sqrt(2) * external_diameter / 8
            coord = np.array([[-x, height - x], [x, height - x], [x, height + x], [-x, height + x]])  # m
            xp = x * 3
            coord_prim = np.array([[-xp, height - xp], [xp, height - xp], [xp, height + xp], [-xp, height + xp]])  # m
            epsilon = (EPSILON_0 * EPSILON_R[insulator]).m
            epsilon_neutral = (EPSILON_0 * EPSILON_R[insulator_neutral]).m
        else:
            msg = f"The line type {line_type!r} of the line {id!r} is unknown."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)

        return coord, coord_prim, epsilon, epsilon_neutral

    @classmethod
    def from_coiffier_model(cls, name: str, nb_phases: int = 3, id: Id | None = None) -> Self:  # noqa: C901
        """Get the electrical parameters of a MV line using Alain Coiffier's method (France specific model).

        Args:
            name:
                The canonical name of the line parameters. It must be in the format
                `LineType_Material_CrossSection`. E.g. "U_AL_150".

            nb_phases:
                The number of phases of the line between 1 and 4, defaults to 3. It represents the
                size of the ``z_line`` and ``y_shunt`` matrices.

            id:
                A unique ID for the created line parameters object (optional). If ``None``
                (default), the id of the created object will be the canonical name.

        Returns:
            The corresponding line parameters.
        """
        # Check the user input and retrieve enumerated types
        try:
            if cls._REGEXP_LINE_TYPE_NAME.fullmatch(string=name) is None:
                raise AssertionError
            line_type_s, material_s, section_s = name.split("_")
            line_type = LineType(line_type_s)
            material = Material(material_s)
            section = Q_(float(section_s), "mm**2")
        except Exception:
            msg = (
                f"The Coiffier line parameter name {name!r} is not valid, expected format is "
                "'LineType_Material_CrossSection'."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX) from None

        r = RHO[material] / section
        if line_type == LineType.OVERHEAD:
            c_b1 = Q_(50, "µF/km")
            c_b2 = Q_(0, "µF/(km*mm**2)")
            x = Q_(0.35, "ohm/km")
            if material == Material.AA:
                if section <= 50:
                    c_imax = 14.20
                elif 50 < section <= 100:
                    c_imax = 12.10
                else:
                    c_imax = 15.70
            elif material in {Material.AL, Material.AM}:
                c_imax = 16.40
            elif material == Material.CU:
                c_imax = 21
            elif material == Material.LA:
                if section <= 50:
                    c_imax = 13.60
                elif 50 < section <= 100:
                    c_imax = 12.10
                else:
                    c_imax = 15.60
            else:
                c_imax = 15.90
        elif line_type == LineType.TWISTED:
            c_b1 = Q_(1750, "µF/km")
            c_b2 = Q_(5, "µF/(km*mm**2)")
            c_imax = 12
            x = Q_(0.1, "ohm/km")
        elif line_type == LineType.UNDERGROUND:
            if section <= Q_(50, "mm**2"):
                c_b1 = Q_(1120, "µF/km")
                c_b2 = Q_(33, "µF/(km*mm**2)")
            else:
                c_b1 = Q_(2240, "µF/km")
                c_b2 = Q_(15, "µF/(km*mm**2)")
            if material == Material.AL:
                c_imax = 16.5
            elif material == Material.CU:
                c_imax = 20
            else:  # Other material: AA, AM, LA.
                c_imax = 16.5
            x = Q_(0.1, "ohm/km")
        else:
            msg = f"The line type {line_type!r} of the line {name!r} is unknown."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)
        b = (c_b1 + c_b2 * section) * 1e-4 * OMEGA
        b = b.to("S/km")

        z_line = (r + x * 1j) * np.eye(nb_phases, dtype=np.float64)  # in ohms/km
        y_shunt = b * 1j * np.eye(nb_phases, dtype=np.float64)  # in siemens/km
        ampacities = c_imax * section.m**0.62  # A
        if id is None:
            id = name
        return cls(
            id=id,
            z_line=z_line,
            y_shunt=y_shunt,
            line_type=line_type,
            materials=material,
            sections=section,
            ampacities=ampacities,
        )

    #
    # Constructors from other software
    #
    @classmethod
    @ureg_wraps(
        None,
        (
            None,
            None,
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "µS/km",
            "µS/km",
            "ohm/km",
            "ohm/km",
            "µS/km",
            "ohm/km",
            "ohm/km",
            "µS/km",
            None,
            None,
            None,
            "kA",
            None,
            None,
            "mm²",
        ),
    )
    def from_power_factory(  # noqa: C901
        cls,
        id: Id,
        *,
        r0: float | Q_[float],
        r1: float | Q_[float],
        x0: float | Q_[float],
        x1: float | Q_[float],
        b0: float | Q_[float],
        b1: float | Q_[float],
        rn: float | Q_[float] | None = None,
        xn: float | Q_[float] | None = None,
        bn: float | Q_[float] | None = None,
        rpn: float | Q_[float] | None = None,
        xpn: float | Q_[float] | None = None,
        bpn: float | Q_[float] | None = None,
        nphase: int = 3,
        nneutral: int = 0,
        inom: float | Q_[float] | None = None,
        cohl: Literal[0, "Cable", 1, "OHL"] = "Cable",
        conductor: Literal["Al", "Cu", "Ad", "As", "Ds"] | None = None,
        insulation: Literal[0, "PVC", 1, "XLPE", 2, "Mineral", 3, "Paper", 4, "EPR"] | None = None,
        section: float | Q_[float] | None = None,
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

            rn:
                PwF parameter `rnline` (AC-Resistance Rn'). Neutral resistance in (ohms/km).

            xn:
                PwF parameter `xnline` (Reactance Xn'). Neutral reactance in (ohms/km).

            bn:
                PwF parameter `bnline` (Susceptance Bn'). Neutral susceptance in (µS/km).

            rpn:
                PwF parameter `rnpline` (AC-Resistance Rpn'). Phase-Neutral coupling resistance in (ohms/km).

            xpn:
                PwF parameter `xnpline` (Reactance Xpn'). Phase-Neutral coupling reactance in (ohms/km).

            bpn:
                PwF parameter `bnpline` (Susceptance Bpn'). Phase-Neutral coupling susceptance in (µS/km).

            nphase:
                PwF parameter `nlnph` (Phases). The number of phases of the line between 1 and 3.
                This should not count the neutral conductor.

            nneutral:
                PwF parameter `nneutral` (Number of Neutrals). The number of neutrals of the line.
                It can be either `0` or `1`.

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
        # TODO Maybe split section into section and section_neutral
        if nphase not in {1, 2, 3}:
            msg = f"Expected nphase=1, 2 or 3, got {nphase!r} for line parameters {id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        if nneutral not in {0, 1}:
            msg = f"Expected nneutral=0 or 1, got {nneutral!r} for line parameters {id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

        cohl_norm = str(cohl).upper()
        if cohl_norm == "CABLE" or cohl_norm == "0":
            line_type = LineType.UNDERGROUND
        elif cohl_norm == "OHL" or cohl_norm == "1":
            line_type = LineType.OVERHEAD
        else:
            msg = f"Expected cohl='Cable' or 'OHL', got {cohl!r} for line parameters {id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)

        mlei_norm = conductor.upper() if conductor is not None else None
        if mlei_norm is None:
            material = None
        elif mlei_norm in ("AL", "ALUMINIUM", "ALUMINUM"):
            material = Material.AL
        elif mlei_norm in ("CU", "COPPER"):
            material = Material.CU
        elif mlei_norm in ("AD", "ALDREY"):
            material = Material.AM
        elif mlei_norm in ("AS", "ALUMINIUM-STEEL", "ALUMINUM-STEEL"):
            material = Material.AA
        elif mlei_norm in ("DS", "ALDREY-STEEL"):
            material = Material.LA
        else:
            msg = f"Expected conductor='Al', 'Cu', 'Ad', 'As' or 'Ds', got {conductor!r} for line parameters {id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_MATERIAL)

        imiso_norm = str(insulation).upper() if insulation is not None else None
        if imiso_norm is None:
            insulator = None
        elif imiso_norm == "PVC" or imiso_norm == "0":
            insulator = Insulator.PVC
        elif imiso_norm == "XLPE" or imiso_norm == "1":
            insulator = Insulator.XLPE
        elif imiso_norm == "MINERAL" or imiso_norm == "2":
            insulator = Insulator.NONE  # not supported yet
        elif imiso_norm == "PAPER" or imiso_norm == "3":
            insulator = Insulator.IP
        elif imiso_norm == "EPR" or imiso_norm == "4":
            insulator = Insulator.EPR
        else:
            msg = (
                f"Expected insulation='PVC', 'XLPE', 'MINERAL', 'PAPER' or 'EPR', got {insulation!r} "
                f"for line parameters {id!r}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_INSULATOR)

        ampacities = inom * 1e3 if inom is not None else None

        z_line, y_shunt = cls._sym_to_zy_simple(
            n=nphase, z0=r0 + 1j * x0, z1=r1 + 1j * x1, y0=1j * b0 * 1e-6, y1=1j * b1 * 1e-6
        )
        if nneutral:
            if pd.isna([rn, xn, bn, rpn, xpn, bpn]).any():
                msg = f"Missing rn, xn, bn, rpn, xpn or bpn required with nneutral=1 for line parameters {id!r}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            z_line = np.pad(z_line, (0, 1), mode="constant", constant_values=rpn + 1j * xpn)
            z_line[-1, -1] = rn + 1j * xn
            y_shunt = np.pad(y_shunt, (0, 1), mode="constant", constant_values=1j * bpn * 1e-6)
            y_shunt[-1, -1] = 1j * bn * 1e-6
        cls._check_z_line_matrix(id=id, z_line=z_line)

        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", message=r".* off-diagonal elements ", category=UserWarning)
            obj = cls(
                id=id,
                z_line=z_line,
                y_shunt=y_shunt,
                ampacities=ampacities,
                line_type=line_type,
                materials=material,
                insulators=insulator,
                sections=section,
            )
        return obj

    @classmethod
    @ureg_wraps(None, (None, None, None, "ohm/km", "ohm/km", "ohm/km", "ohm/km", "nF/km", "nF/km", "Hz", "A", None))
    def from_open_dss(
        cls,
        id: Id,
        *,
        nphases: int,
        r1: float | Q_[float],
        r0: float | Q_[float],
        x1: float | Q_[float],
        x0: float | Q_[float],
        c1: float | Q_[float] = 3.4,  # default value used in OpenDSS
        c0: float | Q_[float] = 1.6,  # default value used in OpenDSS
        basefreq: float | Q_[float] = F,
        normamps: FloatScalarOrArrayLike1D | None = None,
        linetype: str | None = None,
    ) -> Self:
        """Create a line parameters object from OpenDSS "LineCode" data.

        Args:
            id:
                The unique ID of the line parameters.

            nphases:
                OpenDSS parameter: `NPhases`. Number of phases in the line this line code represents.
                To create single-phase lines with a neutral pass nphases=2, for three-phase lines with
                a neutral nphases=4, etc.

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
                This value is passed to `ampacities` and used for violation checks.

            linetype:
                OpenDSS parameter: `LineType`. Code designating the type of line. Only ``"OH"``
                (overhead) and ``"UG"`` (underground) are currently supported.

        Returns:
            The corresponding line parameters object.

        Example usage::

            # DSS command: `New linecode.240sq nphases=3 R1=0.127 X1=0.072 R0=0.342 X0=0.089 units=km`
            lp = LineParameters.from_open_dss(
                id="linecode-240sq",
                nphases=3,  #  creates 3x3 Z,Y matrices
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
                nphases=1,  # creates 1x1 Z,Y matrices
                r1=Q_(0.350, "ohm/kft"),
                x1=Q_(0.025, "ohm/kft"),
                r0=Q_(0.366, "ohm/kft"),
                x0=Q_(0.025, "ohm/kft"),
                c1=Q_(1.036, "nF/kft"),
                c0=Q_(0.488, "nF/kft"),
                normamps=Q_(400, "A"),
            )
        """
        if nphases not in {1, 2, 3, 4}:
            msg = f"Expected 'nphases' from OpenDSS to be in (1, 2, 3, 4), got {nphases}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)

        # Create the symmetric components
        omega = 2 * np.pi * basefreq
        z1 = r1 + 1j * x1
        z0 = r0 + 1j * x0
        yc1 = 1j * omega * c1 * 1e-9  # C is in nF
        yc0 = 1j * omega * c0 * 1e-9  # C is in nF

        # Get the number of conductors
        # OpenDSS says in a comment: "For a line, NPhases = NCond, for now"
        n_cond = nphases

        # Create the matrices of the series impedance and shunt admittance in ohm/km
        z, yc = cls._sym_to_zy_simple(n=n_cond, z0=z0, y0=yc0, z1=z1, y1=yc1)
        cls._check_z_line_matrix(id=id, z_line=z)

        # Convert OpenDSS line type to RLF line type
        if linetype is None:
            line_type = None
        else:
            line_type_upper = linetype.upper()
            if line_type_upper == "OH":
                line_type = LineType.OVERHEAD
            elif line_type_upper == "UG":
                line_type = LineType.UNDERGROUND
            else:
                # TODO other line types
                # ['OH', 'UG', 'UG_TS', 'UG_CN', 'SWT_LDBRK', 'SWT_FUSE', 'SWT_SECT',
                #  'SWT_REC', 'SWT_DISC', 'SWT_BRK', 'SWT_ELBOW', 'BUSBAR']
                logger.warning(f"Line type {linetype} from OpenDSS is not supported, it is ignored.")
                line_type = None

        # Create the RLF line parameters with off-diagonal resistance allowed
        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", message=r".* off-diagonal elements ", category=UserWarning)
            obj = cls(id=id, z_line=z, y_shunt=yc, ampacities=normamps, line_type=line_type)
        return obj

    #
    # Catalogue Mixin
    #
    @classmethod
    def catalogue_path(cls) -> Path:
        return Path(resources.files("roseau.load_flow") / "data" / "lines").expanduser().absolute()

    @classmethod
    def catalogue_data(cls) -> pd.DataFrame:
        file = cls.catalogue_path() / "Catalogue.csv"
        return pd.read_csv(file, parse_dates=False).astype(
            {"insulator": pd.StringDtype(), "insulator_neutral": pd.StringDtype()}
        )

    @classmethod
    def _get_catalogue(
        cls,
        name: str | re.Pattern[str] | None,
        line_type: str | None,
        material: str | None,
        material_neutral: str | None,
        insulator: str | None,
        insulator_neutral: str | None,
        section: float | None,
        section_neutral: float | None,
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
            (material_neutral, "material_neutral", "neutral material", Material),
            (insulator, "insulator", "insulator", Insulator),
            (insulator_neutral, "insulator_neutral", "neutral insulator", Insulator),
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
            except RoseauLoadFlowException:
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
            (section_neutral, "section_neutral", "neutral cross-section", "neutral cross-sections", "mm²"),
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
    @ureg_wraps(None, (None, None, None, None, None, None, None, "mm**2", "mm**2", None, None))
    def from_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        line_type: str | None = None,
        material: str | None = None,
        material_neutral: str | None = None,
        insulator: str | None = None,
        insulator_neutral: str | None = None,
        section: float | Q_[float] | None = None,
        section_neutral: float | Q_[float] | None = None,
        id: Id | None = None,
        nb_phases: int = 3,
    ) -> Self:
        """Create line parameters from a catalogue.

        Args:
            name:
                The name of the line parameters to get from the catalogue. It can be a regular
                expression.

            line_type:
                The type of the line parameters to get. It can be ``"overhead"``, ``"twisted"``, or
                ``"underground"``. See also :class:`~roseau.load_flow.LineType`.

            material:
                The type of the conductor material (Al, Cu, ...) of the phases. See also
                :class:`~roseau.load_flow.Material`.

            material_neutral:
                The type of the conductor material (Al, Cu, ...) of the neutral. See also
                :class:`~roseau.load_flow.Material`.

            insulator:
                The insulator of the phases. See also :class:`~roseau.load_flow.Insulator`. Please provide
                :attr:`~roseau.load_flow.Insulator.NONE` for cable without insulator.

            insulator_neutral:
                The insulator of the neutral. See also :class:`~roseau.load_flow.Insulator`. Please provide
                :attr:`~roseau.load_flow.Insulator.NONE` for cable without insulator.

            section:
                The cross-section surface area of the phases (mm²).

            section_neutral:
                The cross-section surface area of the neutral (mm²).

            id:
                A unique ID for the created line parameters object (optional). If ``None``
                (default), the id of the created object will be its name in the catalogue. Note
                that this parameter is not used in the data filtering.

            nb_phases:
                The number of phases of the line between 1 and 4, defaults to 3. It represents the
                size of the ``z_line`` and ``y_shunt`` matrices.

        Returns:
            The created line parameters.
        """
        if nb_phases not in {1, 2, 3, 4}:
            msg = f"Expected nb_phases to be one of (1, 2, 3, 4), got {nb_phases!r} instead."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
        catalogue_data, query_info = cls._get_catalogue(
            name=name,
            line_type=line_type,
            material=material,
            material_neutral=material_neutral,
            insulator=insulator,
            insulator_neutral=insulator_neutral,
            section=section,
            section_neutral=section_neutral,
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
        rn = catalogue_data.at[idx, "resistance_neutral"]
        x = catalogue_data.at[idx, "reactance"]
        xn = catalogue_data.at[idx, "reactance_neutral"]
        b = catalogue_data.at[idx, "susceptance"]
        bn = catalogue_data.at[idx, "susceptance_neutral"]
        line_type = LineType(catalogue_data.at[idx, "type"])
        material = Material(catalogue_data.at[idx, "material"])
        material_neutral = Material(catalogue_data.at[idx, "material_neutral"])
        insulator = catalogue_data.at[idx, "insulator"]  # Converted in the LineParameters creator
        insulator_neutral = catalogue_data.at[idx, "insulator_neutral"]  # Converted in the LineParameters creator
        section = catalogue_data.at[idx, "section"]
        section_neutral = catalogue_data.at[idx, "section_neutral"]
        ampacity = catalogue_data.at[idx, "ampacity"]
        if pd.isna(ampacity):
            ampacity = None
        ampacity_neutral = catalogue_data.at[idx, "ampacity_neutral"]
        if pd.isna(ampacity_neutral):
            ampacity_neutral = None
        nb_phases_m1 = nb_phases - 1
        z_line = (r + x * 1j) * np.eye(nb_phases, dtype=np.complex128)
        z_line[nb_phases_m1, nb_phases_m1] = rn + 1j * xn
        y_shunt = (b * 1j) * np.eye(nb_phases, dtype=np.complex128)
        y_shunt[nb_phases_m1, nb_phases_m1] = bn * 1j
        ampacities = [ampacity] * nb_phases_m1 + [ampacity_neutral]
        materials = [material] * nb_phases_m1 + [material_neutral]
        insulators = [insulator] * nb_phases_m1 + [insulator_neutral]
        sections = [section] * nb_phases_m1 + [section_neutral]
        if id is None:
            id = name
        return cls(
            id=id,
            z_line=z_line,
            y_shunt=y_shunt,
            ampacities=ampacities,
            line_type=line_type,
            materials=materials,
            insulators=insulators,
            sections=sections,
        )

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, None, "mm**2", "mm**2"))
    def get_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        line_type: str | None = None,
        material: str | None = None,
        material_neutral: str | None = None,
        insulator: str | None = None,
        insulator_neutral: str | None = None,
        section: float | Q_[float] | None = None,
        section_neutral: float | Q_[float] | None = None,
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
                ``"underground"``. See also :class:`~roseau.load_flow.LineType`.

            material:
                The type of the conductor material (Al, Cu, ...) of the phases. See also
                :class:`~roseau.load_flow.Material`.

            material_neutral:
                The type of the conductor material (Al, Cu, ...) of the neutral. See also
                :class:`~roseau.load_flow.Material`.

            insulator:
                The insulator of the phases. See also :class:`~roseau.load_flow.Insulator`. Please provide
                :attr:`~roseau.load_flow.Insulator.NONE` for cable without insulator.

            insulator_neutral:
                The insulator of the neutral. See also :class:`~roseau.load_flow.Insulator`. Please provide
                :attr:`~roseau.load_flow.Insulator.NONE` for cable without insulator.

            section:
                The cross-section surface area of the phases (mm²).

            section_neutral:
                The cross-section surface area of the neutral (mm²).

        Returns:
            The catalogue data as a dataframe.
        """
        catalogue_data, _ = cls._get_catalogue(
            name=name,
            line_type=line_type,
            material=material,
            material_neutral=material_neutral,
            insulator=insulator,
            insulator_neutral=insulator_neutral,
            section=section,
            section_neutral=section_neutral,
            raise_if_not_found=False,
        )
        return catalogue_data.rename(
            columns={
                "name": "Name",
                "resistance": "Phase resistance (ohm/km)",
                "resistance_neutral": "Neutral resistance (ohm/km)",
                "reactance": "Phase reactance (ohm/km)",
                "reactance_neutral": "Neutral reactance (ohm/km)",
                "susceptance": "Phase susceptance (S/km)",
                "susceptance_neutral": "Neutral susceptance (S/km)",
                "ampacity": "Phase ampacity (A)",
                "ampacity_neutral": "Neutral ampacity (A)",
                "type": "Line type",
                "material": "Phase material",
                "material_neutral": "Neutral material",
                "insulator": "Phase insulator",
                "insulator_neutral": "Neutral insulator",
                "section": "Phase cross-section (mm²)",
                "section_neutral": "Neutral cross-section (mm²)",
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
        z_line = np.array(data["z_line"][0]) + 1j * np.array(data["z_line"][1])
        y_shunt = np.array(data["y_shunt"][0]) + 1j * np.array(data["y_shunt"][1]) if "y_shunt" in data else None
        return cls(
            id=data["id"],
            z_line=z_line,
            y_shunt=y_shunt,
            ampacities=data.get("ampacities"),
            line_type=data.get("line_type"),
            materials=data.get("materials"),
            insulators=data.get("insulators"),
            sections=data.get("sections"),
        )

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id, "z_line": [self._z_line.real.tolist(), self._z_line.imag.tolist()]}
        if self.with_shunt:
            res["y_shunt"] = [self._y_shunt.real.tolist(), self._y_shunt.imag.tolist()]
        if self.ampacities is not None:
            res["ampacities"] = self._ampacities.tolist()
        if self._line_type is not None:
            res["line_type"] = self._line_type.name
        if self._materials is not None:
            res["materials"] = [x.name for x in self._materials]
        if self._insulators is not None:
            res["insulators"] = [x.name for x in self._insulators]
        if self._sections is not None:
            res["sections"] = self._sections.tolist()
        return res

    def _results_to_dict(self, warning: bool, full: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    #
    # Utility
    #
    def _check_matrix(self) -> None:
        """Check the coefficients of the matrix."""
        for matrix, matrix_name, code in [
            (self._y_shunt, "y_shunt", RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE),
            (self._z_line, "z_line", RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE),
        ]:
            if matrix_name == "y_shunt" and not self.with_shunt:
                continue
            if matrix.shape[0] != matrix.shape[1]:
                msg = f"The {matrix_name} matrix of line type {self.id!r} has incorrect dimensions {matrix.shape}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=code)

        # Check of the coefficients value
        for matrix, matrix_name, code in [
            (self._z_line, "z_line", RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE),
            (self._y_shunt, "y_shunt", RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_VALUE),
        ]:
            if matrix_name == "y_shunt" and not self.with_shunt:
                continue

            # Check that the off-diagonal element have a zero real part
            off_diagonal_elements = matrix[~np.eye(*matrix.shape, dtype=np.bool_)]
            if not np.allclose(off_diagonal_elements.real, 0):
                warnings.warn(
                    f"The {matrix_name} matrix of line type {self.id!r} has off-diagonal elements "
                    f"with a non-zero real part.",
                    category=UserWarning,
                    stacklevel=find_stack_level(),
                )

            # Check that the real coefficients are non-negative
            if (matrix.real < 0.0).any():
                msg = f"The {matrix_name} matrix of line type {self.id!r} has coefficients with negative real part."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=code)

    @staticmethod
    def _check_enum_array(
        value: _StrEnumType | Sequence[_StrEnumType] | None,
        enum_class: type[_StrEnumType],
        name: Literal["insulators", "materials"],
        size: int,
    ) -> NDArray[_StrEnumType] | None:
        value_isna = pd.isna(value)
        if np.isscalar(value_isna):
            return None if value_isna else np.array([enum_class(value) for _ in range(size)], dtype=np.object_)
        elif np.all(value_isna):
            return None
        else:
            if np.any(value_isna):
                msg = f"{name.title()} cannot contain null values: [{', '.join(f'{x}' for x in value)}] was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{name.upper()}_VALUE"])

            # Build the numpy array fails with pd.NA inside
            values = np.array([enum_class(v) for v in value], dtype=np.object_)
            if len(value) != size:
                msg = f"Incorrect number of {name}: {len(value)} instead of {size}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{name.upper()}_SIZE"])
            return values

    @staticmethod
    def _check_positive_float_array(
        value: FloatArray | Sequence[Float] | Float | None,
        name: Literal["sections", "ampacities"],
        unit: str,
        size: int,
    ) -> FloatArray | None:
        value_isna = pd.isna(value)
        if np.isscalar(value_isna):
            if value_isna:
                return None
            elif value <= 0:
                msg = f"{name.title()} must be positive: {value} {unit} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{name.upper()}_VALUE"])
            else:
                return np.array([value for _ in range(size)], dtype=np.float64)
        else:
            if np.all(value_isna):
                return None
            if np.any(value_isna):
                msg = (
                    f"{name.title()} cannot contain null values: [{', '.join(f'{x}' for x in value)}] {unit} "
                    f"was provided."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{name.upper()}_VALUE"])

            # Build the numpy array fails with pd.NA inside
            values = np.array(value, dtype=np.float64)
            if len(value) != size:
                msg = f"Incorrect number of {name}: {len(value)} instead of {size}."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{name.upper()}_SIZE"])
            if (values <= 0).any():
                msg = f"{name.title()} must be positive: {values.tolist()} {unit} was provided."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode[f"BAD_{name.upper()}_VALUE"])

            return values
