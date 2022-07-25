import copy
import logging
from typing import Any, Optional

import numpy as np
import numpy.linalg as nplin

from roseau.load_flow.utils import (
    ConductorType,
    IsolationType,
    LineModel,
    LineType,
    ThundersIOError,
    ThundersValueError,
)
from roseau.load_flow.utils.constants import EPSILON_0, EPSILON_R, MU_0, OMEGA, PI, RHO, TAN_D

logger = logging.getLogger(__name__)


class LineCharacteristics:
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

    @classmethod
    def from_sym(cls, type_name: str, line_data: dict[str, float]):
        """Create line characteristics from sym model.

        Args:
            type_name:
                The name of the line characteristics.

            line_data:
                The data of the sym model.

        Returns:
            The created line characteristics.
        """
        z_line, y_shunt, model = cls.sym_to_zy(type_name=type_name, line_data=line_data)
        return cls(type_name=type_name, z_line=z_line, y_shunt=y_shunt)

    @staticmethod
    def sym_to_zy(type_name: str, line_data: dict[str, float]):
        # Extract the data
        r0 = line_data["r0"]  # resistance - zero sequence (ohms/km)
        x0 = line_data["x0"]  # reactance - zero sequence  (ohms/km)
        r1 = line_data["r1"]  # resistance - direct sequence (ohms/km)
        x1 = line_data["x1"]  # reactance - direct sequence (ohms/km)
        g0 = line_data["g0"]  # Conductance - zero sequence (Siemens/km)
        b0 = line_data["b0"]  # Conductance - direct sequence (Siemens/km)
        g1 = line_data["g1"]  # Susceptance - zero sequence (Siemens/km)
        b1 = line_data["b1"]  # Susceptance - direct sequence (Siemens/km)
        z0 = r0 + 1j * x0
        z1 = r1 + 1j * x1
        y0 = g0 + 1j * b0
        y1 = g1 + 1j * b1

        model = copy.copy(line_data["model"])
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

            if line_data["model"] == LineModel.SYM_NEUTRAL:
                # Add the neutral
                # Extract the data
                rn = line_data["rn"]  # neutral resistance (ohms/km)
                xn = line_data["xn"]  # neutral reactance  (ohms/km)
                xpn = line_data["xpn"]  # phase to neutral reactance  (ohms/km)
                bn = line_data["bn"]  # neutral susceptance (siemens/km)
                bpn = line_data["bpn"]  # phase to neutral susceptance (siemens/km)

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
                    z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=np.complex_)

                    y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=np.complex_)
                    # We downgrade the model to sym
                    model = LineModel.SYM
                else:

                    z_line = np.array(
                        [[zs, zm, zm, zpn], [zm, zs, zm, zpn], [zm, zm, zs, zpn], [zpn, zpn, zpn, zn]],
                        dtype=np.complex_,
                    )

                    y_shunt = np.array(
                        [[ys, ym, ym, ypn], [ym, ys, ym, ypn], [ym, ym, ys, ypn], [ypn, ypn, ypn, yn]],
                        dtype=np.complex_,
                    )

            else:
                assert line_data["model"] == LineModel.SYM
                z_line = np.array([[zs, zm, zm], [zm, zs, zm], [zm, zm, zs]], dtype=np.complex_)

                y_shunt = np.array([[ys, ym, ym], [ym, ys, ym], [ym, ym, ys]], dtype=np.complex_)

            # Check the validity of the resulting matrices
            det_z = nplin.det(z_line)
            if abs(det_z) == 0:
                if choice == 0:
                    # Warn the user that the PwF data are bad...
                    logger.warning(
                        f"The conversion of the symmetric model of {type_name!r} to its matrix model reached invalid "
                        f"line impedance matrix... It is often the case with line models coming from "
                        "PowerFactory. We pass to a 'degraded' model of lines to handle the provided "
                        f"data."
                    )
                    # Go to choice == 1
                else:
                    assert choice == 1
                    msg = (
                        f"The data provided for the line type {type_name!r} does not allow us to create a valid shunt "
                        f"admittance and line impedance."
                    )
                    logger.error(msg)
                    raise ThundersIOError(msg)
            else:
                # Break: the current choice is good!
                break
        return z_line, y_shunt, model

    @classmethod
    def from_lv_exact(cls, type_name: str, line_data: dict[str, Any]) -> "LineCharacteristics":
        """Create line characteristics from LV exact model.

        Args:
            type_name:
                The name of the line characteristics.

            line_data:
                The data of the LV exact model.

        Returns:
            The created line characteristics.
        """
        z_line, y_shunt, model = cls.lv_exact_to_zy(type_name=type_name, line_data=line_data)
        return cls(type_name=type_name, z_line=z_line, y_shunt=y_shunt)

    @staticmethod
    def lv_exact_to_zy(type_name: str, line_data: dict[str, Any]):
        line_type: LineType = line_data["type"]  # overhead or underground
        sec = line_data["section"]  # Surface of the phases (mm2)
        sec_n = line_data["section_n"]  # Surface of the neutral (mm2)
        # dpp = data["dpp"]  # Distance phase to phase (m)
        # dpn = data["dpn"]  # Distance phase to neutral (m)
        h = line_data["height"]  # Height of the line (m)
        dext = line_data["dext"]  # External diameter of the wire (mm)
        # dsh = data["dsh"]  # Diameter of the sheath (mm)
        conductor_type: ConductorType = line_data["conductor"]  # type of conductor
        isolation_type: IsolationType = line_data["isolation"]  # type of isolation

        # Geometric configuration
        if line_type == LineType.OVERHEAD:
            coord = [
                [-np.sqrt(3) / 8 * dext, h + dext / 8, -np.sqrt(3) / 8 * dext, -h - dext / 8],
                [np.sqrt(3) / 8 * dext, h + dext / 8, np.sqrt(3) / 8 * dext, -h - dext / 8],
                [0, h - dext / 4, 0, -h + dext / 4],
                [0, h, 0, -h],
            ]
            epsilon = EPSILON_0
        elif line_type == LineType.UNDERGROUND:
            coord = [
                [
                    -np.sqrt(2) / 8 * dext,
                    h - np.sqrt(2) / 8 * dext,
                    -np.sqrt(2) * 3 / 8 * dext,
                    h - np.sqrt(2) * 3 / 8 * dext,
                ],
                [
                    np.sqrt(2) / 8 * dext,
                    h - np.sqrt(2) / 8 * dext,
                    np.sqrt(2) * 3 / 8 * dext,
                    h - np.sqrt(2) * 3 / 8 * dext,
                ],
                [
                    np.sqrt(2) / 8 * dext,
                    h + np.sqrt(2) / 8 * dext,
                    np.sqrt(2) * 3 / 8 * dext,
                    h + np.sqrt(2) * 3 / 8 * dext,
                ],
                [
                    -np.sqrt(2) / 8 * dext,
                    h + np.sqrt(2) / 8 * dext,
                    -np.sqrt(2) * 3 / 8 * dext,
                    h + np.sqrt(2) * 3 / 8 * dext,
                ],
            ]
            epsilon = EPSILON_0 * EPSILON_R[isolation_type]
        elif line_type == LineType.UNKNOWN:
            msg = f"The line type of the line {type_name!r} is unknown. It should have been filled in the reading."
            logger.error(msg)
            raise ThundersValueError(msg)
        else:
            msg = f"The line type of the line {type_name!r} is unknown. It should never happen."
            logger.error(msg)
            raise ThundersValueError(msg)

        # Electrical parameters
        sec = [sec * 10**-6, sec * 10**-6, sec * 10**-6, sec_n * 10**-6]  # surfaces (m2)
        radius = np.zeros(4, dtype=np.float_)  # radius (m)
        gmr = np.zeros(4, dtype=np.float_)  # geometric mean radius (m)
        d = np.zeros((4, 4), dtype=np.float_)  # distance between projections of two wires (m)
        distance = np.zeros((4, 4), dtype=np.float_)  # distance between two wires (m)
        distance_prim = np.zeros((4, 4), dtype=np.float_)  # distance between a wire and the image of another wire (m)
        r = np.zeros((4, 4), dtype=np.float_)  # resistance (ohm/km)
        inductance = np.zeros((4, 4), dtype=np.float_)  # inductance (H/km)
        lambdas = np.zeros((4, 4), dtype=np.float_)  # potential coefficient (m/F)
        for i in range(4):
            radius[i] = np.sqrt(sec[i] / PI)
            gmr[i] = radius[i] * np.exp(-0.25)
            r[i, i] = RHO[conductor_type] / sec[i] * 10**3
            for j in range(4):
                d[i, j] = abs(coord[i][0] - coord[j][0])
                distance[i, j] = np.sqrt((coord[i][0] - coord[j][0]) ** 2 + (coord[i][1] - coord[j][1]) ** 2)
                distance_prim[i, j] = np.sqrt((coord[i][0] - coord[j][2]) ** 2 + (coord[i][1] - coord[j][3]) ** 2)
                if j != i:
                    inductance[i, j] = MU_0 / (2 * PI) * np.log(1 / distance[i, j]) * 10**3
                    inductance[j, i] = inductance[i, j]
                    lambdas[i, j] = 1 / (2 * PI * epsilon) * np.log(distance_prim[i, j] / distance[i, j])
                    lambdas[j, i] = lambdas[i, j]
            inductance[i, i] = MU_0 / (2 * PI) * np.log(1 / gmr[i]) * 10**3
            lambdas[i, i] = 1 / (2 * PI * epsilon) * np.log(distance_prim[i, i] / radius[i])
        lambda_inv = nplin.inv(lambdas) * 10**3  # capacities (F/km)
        c = np.zeros((4, 4), dtype=np.float_)  # capacities (F/km)
        g = np.zeros((4, 4), dtype=np.float_)  # conductance (S/km)
        for i in range(4):
            c[i, i] = lambda_inv[i, i]
            for j in range(4):
                if j != i:
                    c[i, i] -= lambda_inv[i, j]
                    c[i, j] = -lambda_inv[i, j]
            g[i, i] = TAN_D[isolation_type] * c[i, i] * OMEGA

        z_line = r + inductance * OMEGA * 1j
        y = g + c * OMEGA * 1j

        y_shunt = np.zeros((4, 4), dtype=complex)
        for i in range(4):
            for k in range(4):
                y_shunt[i, i] += y[i, k]
            for j in range(4):
                if i != j:
                    y_shunt[i, j] = -y[i, j]

        return z_line, y_shunt, copy.copy(line_data["model"])

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
            return cls.from_lv_exact(type_name=type_name, line_data=data)
        elif model in (LineModel.SYM_NEUTRAL, LineModel.SYM):
            return cls.from_sym(type_name=type_name, line_data=data)
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
            raise ThundersValueError(msg)

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
        for matrix, matrix_name in [(self.y_shunt, "y_shunt"), (self.z_line, "z_line")]:
            if matrix_name == "y_shunt" and self.y_shunt is None:
                continue
            if matrix.shape[0] != matrix.shape[1]:
                msg = f"Incorrect {matrix_name} dimensions for line characteristics {self.type_name!r}: {matrix.shape}"
                logger.error(msg)
                raise ThundersValueError(msg)

        # Check of the coefficients value
        for matrix, matrix_name in [(self.z_line, "line impedance"), (self.y_shunt, "shunt admittance")]:
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
                raise ThundersValueError(msg)
            # Check that the real coefficients are positive
            if (matrix.real < 0.0).any():
                msg = f"Some real part coefficients of the {matrix_name} matrix of {self.type_name!r} are negative..."
                logger.error(msg)
                raise ThundersValueError(msg)
