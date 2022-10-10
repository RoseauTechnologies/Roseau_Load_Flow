import logging
import re
from typing import Any, Optional

import numpy as np
import numpy.linalg as nplin

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils import ConductorType, IsolationType, LineModel, LineType
from roseau.load_flow.utils.constants import CX, EPSILON_0, EPSILON_R, MU_0, OMEGA, PI, RHO, TAN_D
from roseau.load_flow.utils.units import Q_, ureg

logger = logging.getLogger(__name__)


class LineCharacteristics:
    """A class to store the line characteristics of lines"""

    _type_re = "|".join(x.code() for x in LineType)
    _material_re = "|".join(x.code() for x in ConductorType)
    _section_re = r"[1-9][0-9]*"
    _REGEXP_LINE_TYPE_NAME: re.Pattern = re.compile(
        rf"^({_type_re})_({_material_re})_{_section_re}$", flags=re.IGNORECASE
    )

    @ureg.wraps(None, (None, None, "ohm/km", "S/km"), strict=False)
    def __init__(self, type_name: str, z_line: np.ndarray, y_shunt: Optional[np.ndarray] = None):
        """LineCharacteristics constructor.

        Args:
            type_name:
                The name of the line characteristics.

            z_line:
                 The Z matrix of the line (Ohm/km).

            y_shunt:
                The Y matrix of the line (Siemens/km). This field is optional if the line has no shunt part.
        """
        self.type_name = type_name
        self.z_line = z_line
        self.y_shunt = y_shunt
        self._check_matrix()

    def __eq__(self, other):
        if not isinstance(other, LineCharacteristics):
            return NotImplemented
        return (
            self.type_name == other.type_name
            and self.z_line.shape == other.z_line.shape
            and np.allclose(self.z_line, other.z_line)
            and (
                (self.y_shunt is None and other.y_shunt is None)
                or (
                    self.y_shunt is not None
                    and other.y_shunt is not None
                    and self.y_shunt.shape == other.y_shunt.shape
                    and np.allclose(self.y_shunt, other.y_shunt)
                )
            )
        )

    @classmethod
    @ureg.wraps(
        None,
        (
            None,
            None,
            None,
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "S/km",
            "S/km",
            "S/km",
            "S/km",
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "S/km",
            "S/km",
        ),
        strict=False,
    )
    def from_sym(
        cls,
        type_name: str,
        model: LineModel,
        r0: float,
        x0: float,
        r1: float,
        x1: float,
        g0: float,
        b0: float,
        g1: float,
        b1: float,
        rn: Optional[float] = None,
        xn: Optional[float] = None,
        xpn: Optional[float] = None,
        bn: Optional[float] = None,
        bpn: Optional[float] = None,
    ):
        """Create line characteristics from sym model.

        Args:
            type_name:
                The name of the line characteristics.

            model:
                The required model. It can be SYM or SYM_NEUTRAL. Be careful, it can be downgraded...

            r0:
                Resistance - zero sequence (ohms/km)

            x0:
                reactance - zero sequence  (ohms/km)

            r1:
                resistance - direct sequence (ohms/km)

            x1:
                reactance - direct sequence (ohms/km)

            g0:
                Conductance - zero sequence (Siemens/km)

            b0:
                Conductance - direct sequence (Siemens/km)

            g1:
                Susceptance - zero sequence (Siemens/km)

            b1:
                Susceptance - direct sequence (Siemens/km)

            rn:
                Neutral resistance (ohms/km)

            xn:
                Neutral reactance  (ohms/km)

            xpn:
                Phase to neutral reactance  (ohms/km)

            bn:
                Neutral susceptance (siemens/km)

            bpn:
                Phase to neutral susceptance (siemens/km)

        Returns:
            The created line characteristics.
        """
        z_line, y_shunt, model = cls._sym_to_zy(
            type_name=type_name,
            model=model,
            r0=r0,
            x0=x0,
            r1=r1,
            x1=x1,
            g0=g0,
            b0=b0,
            g1=g1,
            b1=b1,
            rn=rn,
            xn=xn,
            xpn=xpn,
            bn=bn,
            bpn=bpn,
        )
        return cls(type_name=type_name, z_line=z_line, y_shunt=y_shunt)

    @staticmethod
    @ureg.wraps(
        ("ohm/km", "S/km", None),
        (
            None,
            None,
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "S/km",
            "S/km",
            "S/km",
            "S/km",
            "ohm/km",
            "ohm/km",
            "ohm/km",
            "S/km",
            "S/km",
        ),
        strict=False,
    )
    def _sym_to_zy(
        type_name: str,
        model: LineModel,
        r0: float,
        x0: float,
        r1: float,
        x1: float,
        g0: float,
        b0: float,
        g1: float,
        b1: float,
        rn: Optional[float] = None,
        xn: Optional[float] = None,
        xpn: Optional[float] = None,
        bn: Optional[float] = None,
        bpn: Optional[float] = None,
    ) -> tuple[np.ndarray, np.ndarray, LineModel]:
        """Create impedance and admittance matrix from a symmetrical model.

        Args:
            type_name:
                The name of this type.

            model:
                The required model. It can be SYM or SYM_NEUTRAL. Be careful, it can be downgraded...

            r0:
                Resistance - zero sequence (ohms/km)

            x0:
                reactance - zero sequence  (ohms/km)

            r1:
                resistance - direct sequence (ohms/km)

            x1:
                reactance - direct sequence (ohms/km)

            g0:
                Conductance - zero sequence (Siemens/km)

            b0:
                Conductance - direct sequence (Siemens/km)

            g1:
                Susceptance - zero sequence (Siemens/km)

            b1:
                Susceptance - direct sequence (Siemens/km)

            rn:
                Neutral resistance (ohms/km)

            xn:
                Neutral reactance  (ohms/km)

            xpn:
                Phase to neutral reactance  (ohms/km)

            bn:
                Neutral susceptance (siemens/km)

            bpn:
                Phase to neutral susceptance (siemens/km)

        Returns:
            The impedance and admittance matrices and the line model. The line model may be downgraded from
            SYM_NEUTRAL to SYM if the model of the neutral is not possible.
        """
        # Extract the data
        z0 = r0 + 1j * x0
        z1 = r1 + 1j * x1
        y0 = g0 + 1j * b0
        y1 = g1 + 1j * b1

        # Two possible choices. The first one is the best but sometimes PwF data forces us to choose the second one
        for choice in (0, 1):
            if choice == 0:
                # We trust the manual !!! can gives singular matrix !!!
                zs = (z0 + 2 * z1) / 3  # Serie impedance (ohms/km)
                zm = (z0 - z1) / 3  # Mutual impedance (ohms/km)

                ys = (y0 + 2 * y1) / 3  # Serie shunt admittance (siemens/km)
                ym = (y0 - y1) / 3  # Mutual shunt admittance (siemens/km)
            else:
                # Do not read the manual, it is useless: in pwf we trust
                zs = r1 + 1j * x1  # Serie impedance (ohms/km)
                zm = 0 + 0j  # Mutual impedance (ohms/km)

                ys = g1 + 1j * b1  # Serie shunt admittance (siemens/km)
                ym = 0 + 0j  # Mutual shunt admittance (siemens/km)

            if model == LineModel.SYM_NEUTRAL:
                # Add the neutral
                # Build the complex
                zn = rn + 1j * xn  # Neutral serie impedance (ohm/km)
                zpn = xpn * 1j  # Phase-to-neutral serie impedance (ohm/km)
                yn = bn * 1j  # Neutral shunt admittance (Siemens/km)
                ypn = bpn * 1j  # Phase to neutral shunt admittance (Siemens/km)

                if zpn == 0 and zn == 0:
                    logger.warning(
                        f"The low voltages line {type_name!r} does not have neutral elements. It will model as an "
                        f"medium voltages line."
                    )
                    z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=complex)

                    y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=complex)
                    # We downgrade the model to sym
                    model = LineModel.SYM
                else:

                    z_line = np.array(
                        [[zs, zm, zm, zpn], [zm, zs, zm, zpn], [zm, zm, zs, zpn], [zpn, zpn, zpn, zn]],
                        dtype=complex,
                    )

                    y_shunt = np.array(
                        [[ys, ym, ym, ypn], [ym, ys, ym, ypn], [ym, ym, ys, ypn], [ypn, ypn, ypn, yn]],
                        dtype=complex,
                    )

            else:
                assert model == LineModel.SYM
                z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=complex)

                y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=complex)

            # Check the validity of the resulting matrices
            det_z = nplin.det(z_line)
            if abs(det_z) == 0:
                if choice == 0:
                    # Warn the user that the PwF data are bad...
                    logger.warning(
                        f"The conversion of the symmetric model of {type_name!r} to its matrix model reached invalid "
                        f"line impedance matrix... It is often the case with line models coming from "
                        "PowerFactory. We pass to a 'degraded' model of lines to handle the provided data."
                    )
                    # Go to choice == 1
                else:
                    assert choice == 1
                    msg = (
                        f"The data provided for the line type {type_name!r} does not allow us to create a valid shunt "
                        f"admittance and line impedance."
                    )
                    logger.error(msg)
                    raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_VALUE)
            else:
                # Break: the current choice is good!
                break

        return z_line, y_shunt, model

    @classmethod
    @ureg.wraps(
        None,
        (None, None, None, None, None, "mm**2", "mm**2", "m", "m"),
        strict=False,
    )
    def from_lv_exact(
        cls,
        type_name: str,
        line_type: LineType,
        conductor_type: ConductorType,
        isolation_type: IsolationType,
        section: float,
        section_neutral: float,
        height: float,
        external_diameter: float,
    ) -> "LineCharacteristics":
        """Create line characteristics from LV exact model.

        Args:
            type_name:
                The name of the line characteristics.

            line_type:
                Overhead or underground.

            conductor_type:
                Type of the conductor

            isolation_type:
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
            The created line characteristics.

        TODO: Documentation on the line data
        """
        z_line, y_shunt, model = cls._lv_exact_to_zy(
            type_name=type_name,
            line_type=line_type,
            conductor_type=conductor_type,
            insulator_type=isolation_type,
            section=section,
            section_neutral=section_neutral,
            height=height,
            external_diameter=external_diameter,
        )
        return cls(type_name=type_name, z_line=z_line, y_shunt=y_shunt)

    @staticmethod
    @ureg.wraps(
        ("ohm/km", "S/km", None),
        (None, None, None, None, "mm**2", "mm**2", "m", "m"),
        strict=False,
    )
    def _lv_exact_to_zy(
        type_name: str,
        line_type: LineType,
        conductor_type: ConductorType,
        insulator_type: IsolationType,
        section: float,
        section_neutral: float,
        height: float,
        external_diameter: float,
    ) -> tuple[np.ndarray, np.ndarray, LineModel]:
        """Create impedance and admittance matrix from a LV exact model.

        Args:
            type_name:
                The name of this type.

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
            The impedance and admittance matrices and the line model.
        """
        # dpp = data["dpp"]  # Distance phase to phase (m)
        # dpn = data["dpn"]  # Distance phase to neutral (m)
        # dsh = data["dsh"]  # Diameter of the sheath (mm)

        # Geometric configuration
        if line_type == LineType.OVERHEAD or line_type == LineType.TWISTED:
            coord = Q_(
                np.array(
                    [
                        [
                            -np.sqrt(3) / 8 * external_diameter,
                            height + external_diameter / 8,
                            -np.sqrt(3) / 8 * external_diameter,
                            -height - external_diameter / 8,
                        ],
                        [
                            np.sqrt(3) / 8 * external_diameter,
                            height + external_diameter / 8,
                            np.sqrt(3) / 8 * external_diameter,
                            -height - external_diameter / 8,
                        ],
                        [0, height - external_diameter / 4, 0, -height + external_diameter / 4],
                        [0, height, 0, -height],
                    ]
                ),
                "m",
            )
            epsilon = EPSILON_0
        elif line_type == LineType.UNDERGROUND:
            coord = Q_(
                np.array(
                    [
                        [
                            -np.sqrt(2) / 8 * external_diameter,
                            height - np.sqrt(2) / 8 * external_diameter,
                            -np.sqrt(2) * 3 / 8 * external_diameter,
                            height - np.sqrt(2) * 3 / 8 * external_diameter,
                        ],
                        [
                            np.sqrt(2) / 8 * external_diameter,
                            height - np.sqrt(2) / 8 * external_diameter,
                            np.sqrt(2) * 3 / 8 * external_diameter,
                            height - np.sqrt(2) * 3 / 8 * external_diameter,
                        ],
                        [
                            np.sqrt(2) / 8 * external_diameter,
                            height + np.sqrt(2) / 8 * external_diameter,
                            np.sqrt(2) * 3 / 8 * external_diameter,
                            height + np.sqrt(2) * 3 / 8 * external_diameter,
                        ],
                        [
                            -np.sqrt(2) / 8 * external_diameter,
                            height + np.sqrt(2) / 8 * external_diameter,
                            -np.sqrt(2) * 3 / 8 * external_diameter,
                            height + np.sqrt(2) * 3 / 8 * external_diameter,
                        ],
                    ]
                ),
                "m",
            )
            epsilon = EPSILON_0 * EPSILON_R[insulator_type]
        else:
            msg = f"The line type of the line {type_name!r} is unknown. It should have been filled in the reading."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_TYPE)

        # Electrical parameters
        sections = Q_([section, section, section, section_neutral], "mm**2")  # surfaces (m2)
        radius = Q_(np.zeros(4, dtype=float), "m")  # radius (m)
        gmr = Q_(np.zeros(4, dtype=float), "m")  # geometric mean radius (m)
        # d = Q_(np.zeros((4, 4), dtype=float), "m")  # distance between projections of two wires (m)
        distance = Q_(np.zeros((4, 4), dtype=float), "m")  # distance between two wires (m)
        distance_prim = Q_(np.zeros((4, 4), dtype=float), "m")  # distance between a wire and the image of another
        # wire (m)
        r = Q_(np.zeros((4, 4), dtype=float), "ohm/km")  # resistance (ohm/km)
        inductance = Q_(np.zeros((4, 4), dtype=float), "H/km")  # inductance (H/km)
        lambdas = Q_(np.zeros((4, 4), dtype=float), "m/F")  # potential coefficient (m/F)
        for i in range(4):
            radius[i] = np.sqrt(sections[i] / PI)
            gmr[i] = radius[i].to("m") * np.exp(-0.25)
            r[i, i] = RHO[conductor_type] / sections[i]
            for j in range(4):
                # d[i, j] = abs(coord[i][0] - coord[j][0])
                distance[i, j] = np.sqrt((coord[i][0] - coord[j][0]) ** 2 + (coord[i][1] - coord[j][1]) ** 2)
                distance_prim[i, j] = np.sqrt((coord[i][0] - coord[j][2]) ** 2 + (coord[i][1] - coord[j][3]) ** 2)
                if j != i:
                    inductance[i, j] = MU_0 / (2 * PI) * np.log(Q_(1, "m") / distance[i, j])
                    inductance[j, i] = inductance[i, j]
                    lambdas[i, j] = 1 / (2 * PI * epsilon) * np.log(distance_prim[i, j] / distance[i, j])
                    lambdas[j, i] = lambdas[i, j]
            inductance[i, i] = MU_0 / (2 * PI) * np.log(Q_(1, "m") / gmr[i])
            lambdas[i, i] = 1 / (2 * PI * epsilon) * np.log(distance_prim[i, i] / radius[i])
        lambda_inv = Q_(nplin.inv(lambdas.magnitude), 1 / lambdas.units).to("F/km")  # capacities (F/km)
        c = Q_(np.zeros((4, 4), dtype=float), "F/km")  # capacities (F/km)
        g = Q_(np.zeros((4, 4), dtype=float), "S/km")  # conductance (S/km)
        for i in range(4):
            c[i, i] = lambda_inv[i, i]
            for j in range(4):
                if j != i:
                    c[i, i] -= lambda_inv[i, j]
                    c[i, j] = -lambda_inv[i, j]
            g[i, i] = TAN_D[insulator_type] * c[i, i] * OMEGA

        z_line = r + inductance * OMEGA * 1j
        y = g + c * OMEGA * 1j

        y_shunt = Q_(np.zeros((4, 4), dtype=complex), "S/km")
        for i in range(4):
            for k in range(4):
                y_shunt[i, i] += y[i, k]
            for j in range(4):
                if i != j:
                    y_shunt[i, j] = -y[i, j]

        return z_line, y_shunt, LineModel.LV_EXACT

    @classmethod
    def from_name_lv(
        cls,
        name: str,
        section_neutral: Optional[float] = None,
        height: Optional[float] = None,
        external_diameter: Optional[float] = None,
    ) -> "LineCharacteristics":
        """Method to get the electrical characteristics of a LV line from its canonical name.
        Some hypothesis will be made: the section of the neutral is the same as the other sections, the height and
        external diameter are pre-defined, and the isolation is PVC.

        Args:
            name:
                The name of the line the characteristics must be computed. Eg. "S_AL_150".

            section_neutral:
                Surface of the neutral (mm²). If None it will be the same as the section of the other phases.

            height:
                 Height of the line (m). If None a default value will be used.

            external_diameter:
                External diameter of the wire (mm). If None a default value will be used.

        Returns:
            The corresponding line characteristics.
        """
        match: re.Match = cls._REGEXP_LINE_TYPE_NAME.fullmatch(string=name)
        if not match:
            msg = f"The line type name does not follow the syntax rule. {name!r} was provided."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX)

        # Check the user input and retrieve enumerated types
        line_type, conductor_type, section = name.split("_")
        line_type = LineType.from_string(string=line_type)
        conductor_type = ConductorType.from_string(conductor_type)
        isolation_type = IsolationType.PVC

        section = float(section)

        if section_neutral is None:
            section_neutral = section
        if height is None:
            height = Q_(-1.5, "m") if line_type == LineType.UNDERGROUND else Q_(10.0, "m")
        if external_diameter is None:
            external_diameter = Q_(40, "mm")

        return cls.from_lv_exact(
            type_name=name,
            line_type=line_type,
            conductor_type=conductor_type,
            isolation_type=isolation_type,
            section=section,
            section_neutral=section_neutral,
            height=height,
            external_diameter=external_diameter,
        )

    @classmethod
    def from_name_mv(cls, name: str):
        """Method to get the electrical characteristics of a MV line from its canonical name.

        Args:
            name:
                The name of the line the characteristics must be computed. Eg. "S_AL_150".

        Returns:
            The corresponding line characteristics.
        """
        match: re.Match = cls._REGEXP_LINE_TYPE_NAME.fullmatch(string=name)
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

        z_line = (r + x * 1j) * np.eye(3)  # in ohms/km
        y_shunt = b * 1j * np.eye(3)  # in siemens/km
        return cls(type_name=name, z_line=z_line, y_shunt=y_shunt)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Line characteristics constructor from dict.

        Args:
            data:
                The dictionary data of the line characteristics.

        Returns:
            The created line characteristics.
        """
        type_name = data["name"]
        model = LineModel.from_string(data["model"])
        if model == LineModel.LV_EXACT:
            return cls.from_lv_exact(type_name=type_name, **data)
        elif model in (LineModel.SYM_NEUTRAL, LineModel.SYM):
            return cls.from_sym(type_name=type_name, **data)
        elif model in (LineModel.ZY_NEUTRAL, LineModel.ZY, LineModel.Z, LineModel.Z_NEUTRAL):
            z_line = np.asarray(data["z_line"][0]) + 1j * np.asarray(data["z_line"][1])
            if "y_shunt" in data:
                y_shunt = np.asarray(data["y_shunt"][0]) + 1j * np.asarray(data["y_shunt"][1])
            else:
                y_shunt = None
            return cls(type_name=type_name, z_line=z_line, y_shunt=y_shunt)
        else:
            msg = f"The line {type_name!r} has an unknown model... We can do nothing."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_LINE_MODEL)

    def to_dict(self) -> dict[str, Any]:
        """Return the line characteristics information as a dictionary format."""
        res = {
            "name": self.type_name,
            "model": "zy_neutral" if self.y_shunt is not None else "z_neutral",
            "z_line": [self.z_line.real.tolist(), self.z_line.imag.tolist()],
        }
        if self.y_shunt is not None:
            res["y_shunt"] = [self.y_shunt.real.tolist(), self.y_shunt.imag.tolist()]
        return res

    def _check_matrix(self):
        """Check the coefficients of the matrix."""
        for matrix, matrix_name, code in [
            (self.y_shunt, "y_shunt", RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE),
            (self.z_line, "z_line", RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE),
        ]:
            if matrix_name == "y_shunt" and self.y_shunt is None:
                continue
            if matrix.shape[0] != matrix.shape[1]:
                msg = f"Incorrect {matrix_name} dimensions for line characteristics {self.type_name!r}: {matrix.shape}"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=code)

        # Check of the coefficients value
        for matrix, matrix_name, code in [
            (self.z_line, "line impedance", RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE),
            (self.y_shunt, "shunt admittance", RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_VALUE),
        ]:
            if matrix_name == "shunt admittance" and self.y_shunt is None:
                continue
            # Check that the off-diagonal element have a zero real part
            off_diagonal_elements = matrix[~np.eye(*matrix.shape, dtype=np.bool_)]
            if not np.allclose(off_diagonal_elements.real, 0):
                msg = (
                    f"The {matrix_name} matrix of {self.type_name!r} has off-diagonal elements with a non-zero real "
                    f"part."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=code)
            # Check that the real coefficients are positive
            if (matrix.real < 0.0).any():
                msg = f"Some real part coefficients of the {matrix_name} matrix of {self.type_name!r} are negative..."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=code)
