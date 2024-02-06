import logging
import re
from importlib import resources
from pathlib import Path
from typing import NoReturn

import numpy as np
import numpy.linalg as nplin
import pandas as pd
from typing_extensions import Self, deprecated

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import ComplexArray, ComplexArrayLike2D, Id, JsonDict
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
    ConductorType,
    Identifiable,
    InsulatorType,
    JsonMixin,
    LineType,
)

logger = logging.getLogger(__name__)

_DEFAULT_CONDUCTOR_TYPE = {
    LineType.OVERHEAD: ConductorType.ACSR,
    LineType.TWISTED: ConductorType.AL,
    LineType.UNDERGROUND: ConductorType.AL,
}

_DEFAULT_INSULATION_TYPE = {
    LineType.OVERHEAD: InsulatorType.UNKNOWN,  # Not used for overhead lines
    LineType.TWISTED: InsulatorType.XLPE,
    LineType.UNDERGROUND: InsulatorType.PVC,
}


class LineParameters(Identifiable, JsonMixin, CatalogueMixin[pd.DataFrame]):
    """Parameters that define electrical models of lines."""

    _type_re = "|".join(x.code() for x in LineType)
    _material_re = "|".join(x.code() for x in ConductorType)
    _section_re = r"[1-9][0-9]*"
    _REGEXP_LINE_TYPE_NAME = re.compile(rf"^({_type_re})_({_material_re})_{_section_re}$", flags=re.IGNORECASE)

    @ureg_wraps(None, (None, None, "ohm/km", "S/km", "A", None, None, None, "mm²"))
    def __init__(
        self,
        id: Id,
        z_line: ComplexArrayLike2D,
        y_shunt: ComplexArrayLike2D | None = None,
        max_current: float | None = None,
        line_type: LineType | None = None,
        conductor_type: ConductorType | None = None,
        insulator_type: InsulatorType | None = None,
        section: float | Q_[float] | None = None,
    ) -> None:
        """LineParameters constructor.

        Args:
            id:
                A unique ID of the line parameters, typically its canonical name.

            z_line:
                 The Z matrix of the line (Ohm/km).

            y_shunt:
                The Y matrix of the line (Siemens/km). This field is optional if the line has no shunt part.

            max_current:
                The maximum current loading of the line (A). The maximum current is optional, it is
                not used in the load flow but can be used to check for overloading.
                See also :meth:`Line.res_violated <roseau.load_flow.Line.res_violated>`.

            line_type:
                The type of the line (overhead, underground, twisted). The line type is optional,
                it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            conductor_type:
                The type of the conductor material (Aluminum, Copper, ...). The conductor type is
                optional, it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.

            insulator_type:
                The type of the cable insulator (PVC, XLPE, ...). The insulator type is optional,
                it is informative only and is not used in the load flow. This field gets
                automatically filled when the line parameters are created from a geometric model or
                from the catalogue.
        """
        super().__init__(id)
        self._z_line = np.array(z_line, dtype=np.complex128)
        if y_shunt is None:
            self._with_shunt = False
            self._y_shunt = np.zeros_like(self._z_line, dtype=np.complex128)
        else:
            self._with_shunt = not np.allclose(y_shunt, 0)
            self._y_shunt = np.array(y_shunt, dtype=np.complex128)
        self.max_current = max_current
        self._line_type = line_type
        self._conductor_type = conductor_type
        self._insulator_type = insulator_type
        self._section: float = section
        self._check_matrix()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LineParameters):
            return NotImplemented
        return (
            self.id == other.id
            and self._z_line.shape == other._z_line.shape
            and np.allclose(self._z_line, other._z_line)
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
    def max_current(self) -> Q_[float] | None:
        """The maximum current loading of the line (A) if it is set."""
        return None if self._max_current is None else Q_(self._max_current, "A")

    @property
    def line_type(self) -> LineType | None:
        """The type of the line. Informative only, it has no impact on the load flow."""
        return self._line_type

    @property
    def conductor_type(self) -> ConductorType | None:
        """The type of the conductor material. Informative only, it has no impact on the load flow."""
        return self._conductor_type

    @property
    def insulator_type(self) -> InsulatorType | None:
        """The type of the cable insulator. Informative only, it has no impact on the load flow."""
        return self._insulator_type

    @property
    def section(self) -> Q_[float] | None:
        """The cross section area of the cable (in mm²). Informative only, it has no impact on the load flow."""
        return None if self._section is None else Q_(self._section, "mm**2")

    @max_current.setter
    @ureg_wraps(None, (None, "A"))
    def max_current(self, value: float | Q_[float] | None) -> None:
        self._max_current = value

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
        max_current: float | Q_[float] | None = None,
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
                Phase to neutral reactance (ohms/km)

            bn:
                Neutral susceptance (siemens/km)

            bpn:
                Phase to neutral susceptance (siemens/km)

            max_current:
                An optional maximum current loading of the line (A). It is not used in the load flow.

        Returns:
            The created line parameters.

        Notes:
            As explained in the :ref:`Line parameters alternative constructor documentation
            <models-line_parameters-alternative_constructors-symmetric>`, the model may be "degraded" if the computed
            impedance matrix is not invertible.
        """
        z_line, y_shunt = cls._sym_to_zy(id=id, z0=z0, z1=z1, y0=y0, y1=y1, zn=zn, xpn=xpn, bn=bn, bpn=bpn)
        return cls(id=id, z_line=z_line, y_shunt=y_shunt, max_current=max_current)

    @staticmethod
    def _sym_to_zy(
        id: Id,
        z0: complex,
        z1: complex,
        y0: complex,
        y1: complex,
        zn: complex | None = None,
        xpn: float | None = None,
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

            xpn:
                Phase to neutral reactance (ohms/km)

            bn:
                Neutral susceptance (siemens/km)

            bpn:
                Phase to neutral susceptance (siemens/km)

        Returns:
            The impedance and admittance matrices.
        """
        # Check if all neutral parameters are valid
        any_neutral_na = any(pd.isna([xpn, bn, bpn, zn]))

        # Two possible choices. The first one is the best but sometimes PwF data forces us to choose the second one
        for choice in (0, 1):
            if choice == 0:
                # We trust the manual !!! can give singular matrix !!!
                zs = (z0 + 2 * z1) / 3  # Series impedance (ohms/km)
                zm = (z0 - z1) / 3  # Mutual impedance (ohms/km)

                ys = (y0 + 2 * y1) / 3  # Series shunt admittance (siemens/km)
                ym = (y0 - y1) / 3  # Mutual shunt admittance (siemens/km)
            else:
                # Do not read the manual, it is useless: in pwf we trust
                # NB (Ali): this is equivalent to setting z0 to z1 and y0 to y1
                zs = z1  # Series impedance (ohms/km)
                zm = 0 + 0j  # Mutual impedance (ohms/km)

                ys = y1  # Series shunt admittance (siemens/km)
                ym = 0 + 0j  # Mutual shunt admittance (siemens/km)

            # If all the neutral data have not been filled, the matrix is a 3x3 matrix
            if any_neutral_na:
                # No neutral data so retrieve a 3x3 matrix
                z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=np.complex128)
                y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=np.complex128)
            else:
                # Build the complex
                # zn: Neutral series impedance (ohm/km)
                zpn = xpn * 1j  # Phase-to-neutral series impedance (ohm/km)
                yn = bn * 1j  # Neutral shunt admittance (Siemens/km)
                ypn = bpn * 1j  # Phase to neutral shunt admittance (Siemens/km)

                if zpn == 0 and zn == 0:
                    logger.warning(
                        f"The line model {id!r} does not have neutral elements. It will be modelled as a 3 wires line "
                        f"instead."
                    )
                    z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=np.complex128)
                    y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=np.complex128)
                else:
                    z_line = np.array(
                        [[zs, zm, zm, zpn], [zm, zs, zm, zpn], [zm, zm, zs, zpn], [zpn, zpn, zpn, zn]],
                        dtype=np.complex128,
                    )
                    y_shunt = np.array(
                        [[ys, ym, ym, ypn], [ym, ys, ym, ypn], [ym, ym, ys, ypn], [ypn, ypn, ypn, yn]],
                        dtype=np.complex128,
                    )

            # Check the validity of the resulting matrices
            det_z = nplin.det(z_line)
            if abs(det_z) == 0:
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
    @ureg_wraps(None, (None, None, None, None, None, "mm**2", "mm**2", "m", "m", "A"))
    def from_geometry(
        cls,
        id: Id,
        *,
        line_type: LineType,
        conductor_type: ConductorType | None = None,
        insulator_type: InsulatorType | None = None,
        section: float | Q_[float],
        section_neutral: float | Q_[float] | None = None,
        height: float | Q_[float],
        external_diameter: float | Q_[float],
        max_current: float | Q_[float] | None = None,
    ) -> Self:
        """Create line parameters from its geometry.

        Args:
            id:
                The id of the line parameters type.

            line_type:
                Overhead or underground. See also :class:`~roseau.load_flow.LineType`.

            conductor_type:
                Type of the conductor. If ``None``, ``ACSR`` is used for overhead lines and ``AL``
                for underground or twisted lines. See also :class:`~roseau.load_flow.ConductorType`.

            insulator_type:
                Type of insulator. If ``None``, ``XLPE`` is used for twisted lines and ``PVC`` for
                underground lines. See also :class:`~roseau.load_flow.InsulatorType`.

            section:
                Cross-section surface area of the phases (mm²).

            section_neutral:
                Cross-section surface area of the neutral (mm²). If None it will be the same as the
                section of the other phases.

            height:
                Height of the line (m). It must be positive for overhead lines and negative for
                underground lines.

            external_diameter:
                External diameter of the cable (m).

            max_current:
                An optional maximum current loading of the line (A). It is not used in the load flow.

        Returns:
            The created line parameters.

        See Also:
            :ref:`Line parameters alternative constructor documentation <models-line_parameters-alternative_constructors>`
        """
        z_line, y_shunt, line_type, conductor_type, insulator_type, section = cls._from_geometry(
            id=id,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
            section_neutral=section_neutral,
            height=height,
            external_diameter=external_diameter,
        )
        return cls(
            id=id,
            z_line=z_line,
            y_shunt=y_shunt,
            max_current=max_current,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
        )

    @staticmethod
    def _from_geometry(
        id: Id,
        line_type: LineType,
        conductor_type: ConductorType | None,
        insulator_type: InsulatorType | None,
        section: float,
        section_neutral: float | None,
        height: float,
        external_diameter: float,
    ) -> tuple[ComplexArray, ComplexArray, LineType, ConductorType, InsulatorType, float]:
        """Create impedance and admittance matrices using a geometric model.

        Args:
            id:
                The id of the line parameters.

            line_type:
                Overhead, twisted overhead, or underground.

            conductor_type:
                Type of the conductor material (Aluminum, Copper, ...).

            insulator_type:
                Type of insulator.

            section:
                Surface of the phases (mm²).

            section_neutral:
                Surface of the neutral (mm²). If None it will be the same as the section of the
                other phases.

            height:
                Height of the line (m). Positive for overhead lines and negative for underground
                lines.

            external_diameter:
                External diameter of the wire (m).

        Returns:
            The impedance and admittance matrices.
        """
        # dpp = data["dpp"]  # Distance phase to phase (m)
        # dpn = data["dpn"]  # Distance phase to neutral (m)
        # dsh = data["dsh"]  # Diameter of the sheath (mm)

        if conductor_type is None:
            conductor_type = _DEFAULT_CONDUCTOR_TYPE[line_type]
        if insulator_type is None:
            insulator_type = _DEFAULT_INSULATION_TYPE[line_type]
        if section_neutral is None:
            section_neutral = section
        line_type = LineType(line_type)
        conductor_type = ConductorType(conductor_type)
        insulator_type = InsulatorType(insulator_type)

        # Geometric configuration
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
            epsilon = EPSILON_0.m_as("F/m")
        elif line_type == LineType.UNDERGROUND:
            if height >= 0:
                msg = f"The height of a '{line_type}' line must be a negative number."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)
            x = np.sqrt(2) * external_diameter / 8
            coord = np.array([[-x, height - x], [x, height - x], [x, height + x], [-x, height + x]])  # m
            xp = x * 3
            coord_prim = np.array([[-xp, height - xp], [xp, height - xp], [xp, height + xp], [-xp, height + xp]])  # m
            epsilon = (EPSILON_0 * EPSILON_R[insulator_type]).m_as("F/m")
        else:
            msg = f"The line type {line_type!r} of the line {id!r} is unknown."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)

        # Distance computation
        sections = np.array([section, section, section, section_neutral], dtype=np.float64) * 1e-6  # surfaces (m2)
        radius = np.sqrt(sections / PI)  # radius (m)
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
        mask_diagonal = np.eye(4, dtype=np.bool_)
        mask_off_diagonal = ~mask_diagonal
        minus = -np.ones((4, 4), dtype=np.float64)
        np.fill_diagonal(minus, 1)

        # Electrical parameters
        r = RHO[conductor_type].m_as("ohm*m") / sections * np.eye(4, dtype=np.float64) * 1e3  # resistance (ohm/km)
        distance[mask_diagonal] = gmr
        inductance = MU_0.m_as("H/m") / (2 * PI) * np.log(1 / distance) * 1e3  # H/m->H/km
        distance[mask_diagonal] = radius
        lambdas = 1 / (2 * PI * epsilon) * np.log(distance_prim / distance)  # m/F

        # Extract the conductivity and the capacities from the lambda (potential coefficients)
        lambda_inv = nplin.inv(lambdas) * 1e3  # capacities (F/km)
        c = np.zeros((4, 4), dtype=np.float64)  # capacities (F/km)
        c[mask_diagonal] = np.einsum("ij,ij->i", lambda_inv, minus)
        c[mask_off_diagonal] = -lambda_inv[mask_off_diagonal]
        g = np.zeros((4, 4), dtype=np.float64)  # conductance (S/km)
        omega = OMEGA.m_as("rad/s")
        g[mask_diagonal] = TAN_D[insulator_type].magnitude * np.einsum("ii->i", c) * omega

        # Build the impedance and admittance matrices
        z_line = r + inductance * omega * 1j
        y = g + c * omega * 1j

        # Compute the shunt admittance matrix from the admittance matrix
        y_shunt = np.zeros((4, 4), dtype=np.complex128)
        y_shunt[mask_diagonal] = np.einsum("ij->i", y)
        y_shunt[mask_off_diagonal] = -y[mask_off_diagonal]

        return z_line, y_shunt, line_type, conductor_type, insulator_type, section

    @classmethod
    @deprecated(
        "The method LineParameters.from_name_lv() is deprecated and will be removed in a future "
        "version. Use LineParameters.from_geometry() instead.",
        category=FutureWarning,
    )
    @ureg_wraps(None, (None, None, "mm²", "m", "mm", "A"))
    def from_name_lv(
        cls,
        name: str,
        section_neutral: float | Q_[float] | None = None,
        height: float | Q_[float] | None = None,
        external_diameter: float | Q_[float] | None = None,
        max_current: float | Q_[float] | None = None,
    ) -> Self:
        """Method to get the electrical parameters of a LV line from its canonical name.
        Some hypothesis will be made: the section of the neutral is the same as the other sections, the height and
        external diameter are pre-defined, and the insulator is PVC.

        Args:
            name:
                The name of the line the parameters must be computed. E.g. "U_AL_150".

            section_neutral:
                Surface of the neutral (mm²). If None it will be the same as the section of the other phases.

            height:
                 Height of the line (m). If None a default value will be used.

            external_diameter:
                External diameter of the wire (mm). If None a default value will be used.

            max_current:
                An optional maximum current loading of the line (A). It is not used in the load flow.

        Returns:
            The corresponding line parameters.

        .. deprecated:: 0.6.0
            Use :meth:`LineParameters.from_geometry` instead.
        """
        match = cls._REGEXP_LINE_TYPE_NAME.fullmatch(string=name)
        if not match:
            msg = f"The line type name does not follow the syntax rule. {name!r} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX)

        # Check the user input and retrieve enumerated types
        line_type, conductor_type, section = name.split("_")
        line_type = LineType(line_type)
        conductor_type = ConductorType(conductor_type)
        insulator_type = InsulatorType.PVC

        section = float(section)

        if section_neutral is None:
            section_neutral = section
        if height is None:
            height = Q_(-1.5, "m") if line_type == LineType.UNDERGROUND else Q_(10.0, "m")
        if external_diameter is None:
            external_diameter = Q_(40, "mm")

        return cls.from_geometry(
            name,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
            section_neutral=section_neutral,
            height=height,
            external_diameter=external_diameter,
            max_current=max_current,
        )

    @classmethod
    # @deprecated(
    #     "The method LineParameters.from_name_mv() is deprecated and will be removed in a future "
    #     "version. Use LineParameters.from_catalogue() instead.",
    #     category=FutureWarning,
    # )
    @ureg_wraps(None, (None, None, "A"))
    def from_name_mv(cls, name: str, max_current: float | Q_[float] | None = None) -> Self:
        """Get the electrical parameters of a MV line from its canonical name (France specific model)

        Args:
            name:
                The canonical name of the line parameters. It must be in the format
                `lineType_conductorType_crossSection`. E.g. "U_AL_150".

            max_current:
                An optional maximum current loading of the line (A). It is not used in the load flow.

        Returns:
            The corresponding line parameters.
        """
        match = cls._REGEXP_LINE_TYPE_NAME.fullmatch(string=name)
        if not match:
            msg = f"The line type name does not follow the syntax rule. {name!r} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX)

        # Check the user input and retrieve enumerated types
        line_type, conductor_type, section = name.split("_")
        line_type = LineType(line_type)
        conductor_type = ConductorType(conductor_type)
        section = Q_(float(section), "mm**2")

        r = RHO[conductor_type] / section
        if line_type == LineType.OVERHEAD:
            c_b1 = Q_(50, "µF/km")
            c_b2 = Q_(0, "µF/(km*mm**2)")
            x = Q_(0.35, "ohm/km")
        elif line_type == LineType.TWISTED:
            c_b1 = Q_(1750, "µF/km")
            c_b2 = Q_(5, "µF/(km*mm**2)")
            x = Q_(0.1, "ohm/km")
        elif line_type == LineType.UNDERGROUND:
            if section <= Q_(50, "mm**2"):
                c_b1 = Q_(1120, "µF/km")
                c_b2 = Q_(33, "µF/(km*mm**2)")
            else:
                c_b1 = Q_(2240, "µF/km")
                c_b2 = Q_(15, "µF/(km*mm**2)")
            x = Q_(0.1, "ohm/km")
        else:
            msg = f"The line type {line_type!r} of the line {name!r} is unknown."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)
        b = (c_b1 + c_b2 * section) * 1e-4 * OMEGA
        b = b.to("S/km")

        z_line = (r + x * 1j) * np.eye(3, dtype=np.float64)  # in ohms/km
        y_shunt = b * 1j * np.eye(3, dtype=np.float64)  # in siemens/km
        return cls(name, z_line=z_line, y_shunt=y_shunt, max_current=max_current)

    #
    # Catalogue Mixin
    #
    @classmethod
    def catalogue_path(cls) -> Path:
        return Path(resources.files("roseau.load_flow") / "data" / "lines").expanduser().absolute()

    @classmethod
    def catalogue_data(cls) -> pd.DataFrame:
        file = cls.catalogue_path() / "Catalogue.csv"
        return pd.read_csv(file, parse_dates=False).fillna({"insulator": ""})

    @classmethod
    def _get_catalogue(
        cls,
        name: str | re.Pattern[str] | None,
        line_type: str | None,
        conductor_type: str | None,
        insulator_type: str | None,
        section: float | None,
        raise_if_not_found: bool,
    ) -> tuple[pd.DataFrame, str]:
        catalogue_data = cls.catalogue_data()

        # Filter on strings/regular expressions
        query_msg_list = []
        for value, column_name, display_name, display_name_plural in [
            (name, "name", "name", "names"),
        ]:
            if value is None:
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
            (conductor_type, "material", "conductor_type", ConductorType),
            (insulator_type, "insulator", "insulator_type", InsulatorType),
        ):
            if value is None:
                continue

            enum_series = catalogue_data[column_name].apply(enum_class)
            try:
                mask = enum_series == enum_class(value)
            except RoseauLoadFlowException:
                mask = pd.Series(False, index=catalogue_data.index)
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
    @ureg_wraps(None, (None, None, None, None, None, "mm²", None))
    def from_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        line_type: str | None = None,
        conductor_type: str | None = None,
        insulator_type: str | None = None,
        section: float | Q_[float] | None = None,
        id: Id | None = None,
    ) -> Self:
        """Create line parameters from a catalogue.

        Args:
            name:
                The name of the line parameters to get from the catalogue. It can be a regular
                expression.

            line_type:
                The type of the line parameters to get. It can be ``"overhead"``, ``"twisted"``, or
                ``"underground"``. See also :class:`~roseau.load_flow.LineType`.

            conductor_type:
                The type of the conductor material (Al, Cu, ...). See also
                :class:`~roseau.load_flow.ConductorType`.

            insulator_type:
                The type of insulator. See also :class:`~roseau.load_flow.InsulatorType`.

            section:
                The cross-section surface area of the phases (mm²).

            id:
                A unique ID for the created line parameters object (optional). If ``None``
                (default), the id of the created object will be its name in the catalogue.

        Returns:
            The created line parameters.
        """
        catalogue_data, query_info = cls._get_catalogue(
            name=name,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
            raise_if_not_found=True,
        )

        cls._assert_one_found(
            found_data=catalogue_data["name"].tolist(), display_name="line parameters", query_info=query_info
        )
        idx = catalogue_data.index[0]
        name = str(catalogue_data.at[idx, "name"])
        r = catalogue_data.at[idx, "r"]
        x = catalogue_data.at[idx, "x"]
        b = catalogue_data.at[idx, "b"]
        line_type = LineType(catalogue_data.at[idx, "type"])
        conductor_type = ConductorType(catalogue_data.at[idx, "material"])
        insulator_type = InsulatorType(catalogue_data.at[idx, "insulator"])
        section = catalogue_data.at[idx, "section"]
        max_current = catalogue_data.at[idx, "maximal_current"]
        if pd.isna(max_current):
            max_current = None
        z_line = (r + x * 1j) * np.eye(3, dtype=np.complex128)
        y_shunt = (b * 1j) * np.eye(3, dtype=np.complex128)
        if id is None:
            id = name
        return cls(
            id=id,
            z_line=z_line,
            y_shunt=y_shunt,
            max_current=max_current,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
        )

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, "mm²"))
    def get_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        line_type: str | None = None,
        conductor_type: str | None = None,
        insulator_type: str | None = None,
        section: float | Q_[float] | None = None,
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

            conductor_type:
                The type of the conductor material (Al, Cu, ...). See also
                :class:`~roseau.load_flow.ConductorType`.

            insulator_type:
                The type of insulator. See also :class:`~roseau.load_flow.InsulatorType`.

            section:
                The cross-section surface area of the phases (mm²).

        Returns:
            The catalogue data as a dataframe.
        """
        catalogue_data, _ = cls._get_catalogue(
            name=name,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
            raise_if_not_found=False,
        )
        return catalogue_data.rename(
            columns={
                "name": "Name",
                "r": "Resistance (ohm/km)",
                "x": "Reactance (ohm/km)",
                "b": "Susceptance (µS/km)",
                "maximal_current": "Maximal current (A)",
                "type": "Line type",
                "material": "Conductor material",
                "insulator": "Insulator type",
                "section": "Cross-section (mm²)",
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

        Returns:
            The created line parameters.
        """
        z_line = np.array(data["z_line"][0]) + 1j * np.array(data["z_line"][1])
        y_shunt = np.array(data["y_shunt"][0]) + 1j * np.array(data["y_shunt"][1]) if "y_shunt" in data else None
        line_type = LineType(data["line_type"]) if "line_type" in data else None
        conductor_type = ConductorType(data["conductor_type"]) if "conductor_type" in data else None
        insulator_type = InsulatorType(data["insulator_type"]) if "insulator_type" in data else None
        return cls(
            id=data["id"],
            z_line=z_line,
            y_shunt=y_shunt,
            max_current=data.get("max_current"),
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=data.get("section"),
        )

    def _to_dict(self, include_results: bool) -> JsonDict:
        res = {"id": self.id, "z_line": [self._z_line.real.tolist(), self._z_line.imag.tolist()]}
        if self.with_shunt:
            res["y_shunt"] = [self._y_shunt.real.tolist(), self._y_shunt.imag.tolist()]
        if self.max_current is not None:
            res["max_current"] = self.max_current.magnitude
        if self._line_type is not None:
            res["line_type"] = self._line_type.name
        if self._conductor_type is not None:
            res["conductor_type"] = self._conductor_type.name
        if self._insulator_type is not None:
            res["insulator_type"] = self._insulator_type.name
        if self._section is not None:
            res["section"] = self._section
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

    def _results_from_dict(self, data: JsonDict) -> None:
        msg = f"The {type(self).__name__} has no results to import."
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
                msg = (
                    f"The {matrix_name} matrix of line type {self.id!r} has off-diagonal elements "
                    f"with a non-zero real part."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=code)
            # Check that the real coefficients are non-negative
            if (matrix.real < 0.0).any():
                msg = f"The {matrix_name} matrix of line type {self.id!r} has coefficients with negative real part."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=code)
