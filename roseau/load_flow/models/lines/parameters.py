import logging
import re
from typing import NoReturn, Optional

import numpy as np
import numpy.linalg as nplin
import pandas as pd
from typing_extensions import Self

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import (
    CX,
    EPSILON_0,
    EPSILON_R,
    MU_0,
    OMEGA,
    PI,
    RHO,
    TAN_D,
    ConductorType,
    Identifiable,
    InsulatorType,
    JsonMixin,
    LineType,
)

logger = logging.getLogger(__name__)


class LineParameters(Identifiable, JsonMixin):
    """Parameters that define electrical models of lines."""

    _type_re = "|".join("|".join(x) for x in LineType.CODES.values())
    _material_re = "|".join(x.code() for x in ConductorType)
    _section_re = r"[1-9][0-9]*"
    _REGEXP_LINE_TYPE_NAME: re.Pattern = re.compile(
        rf"^({_type_re})_({_material_re})_{_section_re}$", flags=re.IGNORECASE
    )

    @ureg_wraps(None, (None, None, "ohm/km", "S/km", "A"), strict=False)
    def __init__(
        self, id: Id, z_line: np.ndarray, y_shunt: Optional[np.ndarray] = None, max_current: Optional[float] = None
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
                An optional maximum current loading of the line (A). It is not used in the load flow.
        """
        super().__init__(id)
        self._z_line = np.asarray(z_line, dtype=complex)
        if y_shunt is None:
            self._with_shunt = False
            self._y_shunt = np.zeros_like(z_line, dtype=complex)
        else:
            self._with_shunt = not np.allclose(y_shunt, 0)
            self._y_shunt = np.asarray(y_shunt, dtype=complex)
        self.max_current = max_current
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
    @ureg_wraps("ohm/km", (None,), strict=False)
    def z_line(self) -> Q_[np.ndarray]:
        return self._z_line

    @property
    @ureg_wraps("S/km", (None,), strict=False)
    def y_shunt(self) -> Q_[np.ndarray]:
        return self._y_shunt

    @property
    def with_shunt(self) -> bool:
        return self._with_shunt

    @property
    def max_current(self) -> Optional[Q_[float]]:
        """The maximum current loading of the line (A) if it is set."""
        return None if self._max_current is None else Q_(self._max_current, "A")

    @max_current.setter
    @ureg_wraps(None, (None, "A"), strict=False)
    def max_current(self, value: Optional[float]) -> None:
        self._max_current = value

    @classmethod
    @ureg_wraps(
        None, (None, None, "ohm/km", "ohm/km", "S/km", "S/km", "ohm/km", "ohm/km", "S/km", "S/km", "A"), strict=False
    )
    def from_sym(
        cls,
        id: Id,
        z0: complex,
        z1: complex,
        y0: complex,
        y1: complex,
        zn: Optional[complex] = None,
        xpn: Optional[float] = None,
        bn: Optional[float] = None,
        bpn: Optional[float] = None,
        max_current: Optional[float] = None,
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
        zn: Optional[complex] = None,
        xpn: Optional[float] = None,
        bn: Optional[float] = None,
        bpn: Optional[float] = None,
    ) -> tuple[np.ndarray, np.ndarray]:
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
                z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=complex)
                y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=complex)
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
                    z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=complex)
                    y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=complex)
                else:
                    z_line = np.array(
                        [[zs, zm, zm, zpn], [zm, zs, zm, zpn], [zm, zm, zs, zpn], [zpn, zpn, zpn, zn]],
                        dtype=complex,
                    )
                    y_shunt = np.array(
                        [[ys, ym, ym, ypn], [ym, ys, ym, ypn], [ym, ym, ys, ypn], [ypn, ypn, ypn, yn]],
                        dtype=complex,
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
    @ureg_wraps(None, (None, None, None, None, None, "mm**2", "mm**2", "m", "m", "A"), strict=False)
    def from_geometry(
        cls,
        id: Id,
        line_type: LineType,
        conductor_type: ConductorType,
        insulator_type: InsulatorType,
        section: float,
        section_neutral: float,
        height: float,
        external_diameter: float,
        max_current: Optional[float] = None,
    ) -> Self:
        """Create line parameters from its geometry.

        Args:
            id:
                The id of the line parameters type.

            line_type:
                Overhead or underground.

            conductor_type:
                Type of the conductor

            insulator_type:
                Type of insulator.

            section:
                Surface of the phases (mm²).

            section_neutral:
                Surface of the neutral (mm²).

            height:
                 Height of the line (m).

            external_diameter:
                External diameter of the wire (m).

            max_current:
                An optional maximum current loading of the line (A). It is not used in the load flow.

        Returns:
            The created line parameters.

        See Also:
            :ref:`Line parameters alternative constructor documentation <models-line_parameters-alternative_constructors>`
        """
        z_line, y_shunt = cls._geometry_to_zy(
            id=id,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=insulator_type,
            section=section,
            section_neutral=section_neutral,
            height=height,
            external_diameter=external_diameter,
        )
        return cls(id=id, z_line=z_line, y_shunt=y_shunt, max_current=max_current)

    @staticmethod
    def _geometry_to_zy(
        id: Id,
        line_type: LineType,
        conductor_type: ConductorType,
        insulator_type: InsulatorType,
        section: float,
        section_neutral: float,
        height: float,
        external_diameter: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Create impedance and admittance matrix using a geometric model.

        Args:
            id:
                The id of the line parameters.

            line_type:
                Overhead or underground.

            conductor_type:
                Type of the conductor

            insulator_type:
                Type of insulator.

            section:
                Surface of the phases (mm²).

            section_neutral:
                Surface of the neutral (mm²).

            height:
                 Height of the line (m).

            external_diameter:
                External diameter of the wire (m).

        Returns:
            The impedance and admittance matrices.
        """
        # dpp = data["dpp"]  # Distance phase to phase (m)
        # dpn = data["dpn"]  # Distance phase to neutral (m)
        # dsh = data["dsh"]  # Diameter of the sheath (mm)

        # Geometric configuration
        if line_type in (LineType.OVERHEAD, LineType.TWISTED):
            # TODO This configuration is for twisted lines... Create a overhead configuration.
            # TODO Add some checks on provided geometric values...
            coord = np.array(
                [
                    [-np.sqrt(3) / 8 * external_diameter, height + external_diameter / 8],
                    [np.sqrt(3) / 8 * external_diameter, height + external_diameter / 8],
                    [0, height - external_diameter / 4],
                    [0, height],
                ]
            )  # m
            coord_prim = np.array(
                [
                    [-np.sqrt(3) / 8 * external_diameter, -height - external_diameter / 8],
                    [np.sqrt(3) / 8 * external_diameter, -height - external_diameter / 8],
                    [0, -height + external_diameter / 4],
                    [0, -height],
                ]
            )  # m
            epsilon = EPSILON_0.m_as("F/m")
        elif line_type == LineType.UNDERGROUND:
            coord = np.array(
                [
                    [-np.sqrt(2) / 8 * external_diameter, height - np.sqrt(2) / 8 * external_diameter],
                    [np.sqrt(2) / 8 * external_diameter, height - np.sqrt(2) / 8 * external_diameter],
                    [np.sqrt(2) / 8 * external_diameter, height + np.sqrt(2) / 8 * external_diameter],
                    [-np.sqrt(2) / 8 * external_diameter, height + np.sqrt(2) / 8 * external_diameter],
                ]
            )  # m
            coord_prim = np.array(
                [
                    [-np.sqrt(2) * 3 / 8 * external_diameter, height - np.sqrt(2) * 3 / 8 * external_diameter],
                    [np.sqrt(2) * 3 / 8 * external_diameter, height - np.sqrt(2) * 3 / 8 * external_diameter],
                    [np.sqrt(2) * 3 / 8 * external_diameter, height + np.sqrt(2) * 3 / 8 * external_diameter],
                    [-np.sqrt(2) * 3 / 8 * external_diameter, height + np.sqrt(2) * 3 / 8 * external_diameter],
                ]
            )  # m
            epsilon = (EPSILON_0 * EPSILON_R[insulator_type]).m_as("F/m")
        else:
            msg = f"The line type of the line {id!r} is unknown. It should have been filled in the reading."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)

        # Distance computation
        sections = np.array([section, section, section, section_neutral], dtype=float) * 1e-6  # surfaces (m2)
        radius = np.sqrt(sections / PI)  # radius (m)
        gmr = radius * np.exp(-0.25)  # geometric mean radius (m)
        # distance between two wires (m)
        coord_new_dim = coord[:, None, :]
        diff = coord_new_dim - coord
        distance = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
        # distance between a wire and the image of another wire (m)
        diff = coord_new_dim - coord_prim
        distance_prim = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))

        # Useful matrices
        mask_diagonal = np.eye(4, dtype=bool)
        mask_off_diagonal = ~mask_diagonal
        minus = -np.ones((4, 4), dtype=float)
        np.fill_diagonal(minus, 1)

        # Electrical parameters
        r = RHO[conductor_type].m_as("ohm*m") / sections * np.eye(4, dtype=float) * 1e3  # resistance (ohm/km)
        distance[mask_diagonal] = gmr
        inductance = MU_0.m_as("H/m") / (2 * PI) * np.log(1 / distance) * 1e3  # H/m->H/km
        distance[mask_diagonal] = radius
        lambdas = 1 / (2 * PI * epsilon) * np.log(distance_prim / distance)  # m/F

        # Extract the conductivity and the capacities from the lambda (potential coefficients)
        lambda_inv = nplin.inv(lambdas) * 1e3  # capacities (F/km)
        c = np.zeros((4, 4), dtype=float)  # capacities (F/km)
        c[mask_diagonal] = np.einsum("ij,ij->i", lambda_inv, minus)
        c[mask_off_diagonal] = -lambda_inv[mask_off_diagonal]
        g = np.zeros((4, 4), dtype=float)  # conductance (S/km)
        omega = OMEGA.m_as("rad/s")
        g[mask_diagonal] = TAN_D[insulator_type].magnitude * np.einsum("ii->i", c) * omega

        # Build the impedance and admittance matrices
        z_line = r + inductance * omega * 1j
        y = g + c * omega * 1j

        # Compute the shunt admittance matrix from the admittance matrix
        y_shunt = np.zeros((4, 4), dtype=complex)
        y_shunt[mask_diagonal] = np.einsum("ij->i", y)
        y_shunt[mask_off_diagonal] = -y[mask_off_diagonal]

        return z_line, y_shunt

    @classmethod
    @ureg_wraps(None, (None, None, "mm²", "m", "mm", "A"), strict=False)
    def from_name_lv(
        cls,
        name: str,
        section_neutral: Optional[float] = None,
        height: Optional[float] = None,
        external_diameter: Optional[float] = None,
        max_current: Optional[float] = None,
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
        """
        match = cls._REGEXP_LINE_TYPE_NAME.fullmatch(string=name)
        if not match:
            msg = f"The line type name does not follow the syntax rule. {name!r} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX)

        # Check the user input and retrieve enumerated types
        line_type, conductor_type, section = name.split("_")
        line_type = LineType.from_string(line_type)
        conductor_type = ConductorType.from_string(conductor_type)
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
    def from_name_mv(cls, name: str, max_current: Optional[float] = None) -> Self:
        """Method to get the electrical parameters of a MV line from its canonical name.

        Args:
            name:
                The name of the line the parameters must be computed. E.g. "U_AL_150".

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
        line_type = LineType.from_string(string=line_type)
        conductor_type = ConductorType.from_string(conductor_type)
        section = Q_(float(section), "mm**2")

        r = RHO[conductor_type] / section
        x = CX[line_type]
        if type == LineType.OVERHEAD:
            c_b1 = Q_(50, "µF/km")
            c_b2 = Q_(0, "µF/(km*mm**2)")
        elif type == LineType.TWISTED:
            # Twisted line
            c_b1 = Q_(1750, "µF/km")
            c_b2 = Q_(5, "µF/(km*mm**2)")
        else:
            if section <= Q_(50, "mm**2"):
                c_b1 = Q_(1120, "µF/km")
                c_b2 = Q_(33, "µF/(km*mm**2)")
            else:
                c_b1 = Q_(2240, "µF/km")
                c_b2 = Q_(15, "µF/(km*mm**2)")
        b = (c_b1 + c_b2 * section) * 1e-4 * OMEGA
        b = b.to("S/km")

        z_line = (r + x * 1j) * np.eye(3, dtype=float)  # in ohms/km
        y_shunt = b * 1j * np.eye(3, dtype=float)  # in siemens/km
        return cls(name, z_line=z_line, y_shunt=y_shunt, max_current=max_current)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict) -> Self:
        """Line parameters constructor from dict.

        Args:
            data:
                The dictionary data of the line parameters.

        Returns:
            The created line parameters.
        """
        z_line = np.asarray(data["z_line"][0]) + 1j * np.asarray(data["z_line"][1])
        y_shunt = np.asarray(data["y_shunt"][0]) + 1j * np.asarray(data["y_shunt"][1]) if "y_shunt" in data else None
        return cls(id=data["id"], z_line=z_line, y_shunt=y_shunt, max_current=data.get("max_current"))

    def to_dict(self, *, _lf_only: bool = False) -> JsonDict:
        """Return the line parameters information as a dictionary format."""
        res = {"id": self.id, "z_line": [self._z_line.real.tolist(), self._z_line.imag.tolist()]}
        if self.with_shunt:
            res["y_shunt"] = [self._y_shunt.real.tolist(), self._y_shunt.imag.tolist()]
        if not _lf_only and self.max_current is not None:
            res["max_current"] = self.max_current.magnitude
        return res

    def _results_to_dict(self, warning: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    def results_from_dict(self, data: JsonDict) -> None:
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
