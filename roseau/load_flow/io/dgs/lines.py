import logging
import warnings

import numpy as np
import pandas as pd
import shapely

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import CONDUCTOR_TYPES, INSULATOR_TYPES, LINE_TYPES
from roseau.load_flow.models import AbstractBranch, Bus, Ground, Line, LineParameters
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import ConductorType

logger = logging.getLogger(__name__)


def generate_typ_lne(typ_lne: pd.DataFrame, lines_params: dict[Id, LineParameters]) -> None:
    """Generate line parameters from the "TypLne" dataframe.

    Args:
        typ_lne:
            The "TypLne" dataframe containing line parameters data.

        lines_params:
            The dictionary to store the line parameters into.
    """
    for type_id in typ_lne.index:
        this_typ_lne: pd.Series = typ_lne.loc[type_id]
        # TODO: use the detailed phase information instead of n
        nneutral = this_typ_lne["nneutral"]
        n = this_typ_lne["nlnph"] + nneutral
        if n not in (3, 4):
            msg = f"The number of phases ({n}) of line type {type_id!r} cannot be handled, it should be 3 or 4."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)

        z_line, y_shunt = LineParameters._sym_to_zy(
            type_id,
            z0=complex(this_typ_lne["rline0"], this_typ_lne["xline0"]),
            z1=complex(this_typ_lne["rline"], this_typ_lne["xline"]),
            y0=complex(this_typ_lne["gline0"], this_typ_lne["bline0"]) * 1e-6,
            y1=complex(this_typ_lne["gline"], this_typ_lne["bline"]) * 1e-6,
            zn=complex(this_typ_lne["rnline"], this_typ_lne["xnline"]) if nneutral else None,
            xpn=this_typ_lne["xpnline"] if nneutral else None,
            bn=(this_typ_lne["bnline"] * 1e-6) if nneutral else None,
            bpn=(this_typ_lne["bpnline"] * 1e-6) if nneutral else None,
        )

        actual_shape = z_line.shape[0]
        if actual_shape > n:  # 4x4 matrix while a 3x3 matrix was expected
            # Extract the 3x3 underlying matrix
            z_line = z_line[:n, :n]
            y_shunt = y_shunt[:n, :n]
        elif actual_shape == n:
            # Everything ok
            pass
        else:
            # Something unexpected happened
            msg = (
                f"A {n}x{n} impedance matrix was expected for the line type {type_id!r} but a "
                f"{actual_shape}x{actual_shape} matrix was generated."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)

        # Optional fields
        sline = this_typ_lne.get("sline")
        max_current = sline * 1e3 if sline is not None else None
        line_type = LINE_TYPES.get(this_typ_lne.get("cohl_"))
        mlei = this_typ_lne.get("mlei")  # int | str | None
        conductor_type = ConductorType(mlei) if isinstance(mlei, str) else CONDUCTOR_TYPES.get(mlei)
        insulator_type = INSULATOR_TYPES.get(this_typ_lne.get("imiso"))
        section = this_typ_lne.get("qurs") or None  # Sometimes it is zero!! replace by None in this case

        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", message=r".* off-diagonal elements ", category=UserWarning)
            lp = LineParameters(
                type_id,
                z_line=z_line,
                y_shunt=y_shunt,
                max_current=max_current,
                line_type=line_type,
                conductor_type=conductor_type,
                insulator_type=insulator_type,
                section=section,
            )
        lines_params[type_id] = lp


def generate_typ_lne_from_elm_lne(
    elm_lne: pd.DataFrame, line_id: Id, phases: str, lines_params: dict[Id, LineParameters]
) -> None:
    """Generate line parameters for a certain line.

    Args:
        elm_lne:
            The "ElmLne" dataframe containing line parameters data.

        line_id:
            The ID of the line in the dataframe.

        lines_params:
            The dictionary to store the line parameters into.
    """

    lne_series = elm_lne.loc[line_id]

    # Get a unique ID for the line parameters (contains the ID of the line)
    typ_id = f"line {line_id!r}"
    i = 1
    while typ_id in lines_params:
        typ_id = f"line {line_id!r} ({i})"
        i += 1

    # Get the type of the line (overhead, underground)
    line_type = LINE_TYPES.get(lne_series.get("inAir"))

    # Get the cross-sectional area
    section = lne_series.get("inAir")  # mm²

    # Get the impedance and admittance matrices
    required_fields = ("R0", "X0", "X1", "R1", "G0", "B0", "G1", "B1")
    missing_fields = tuple(f for f in required_fields if pd.isna(lne_series.get(f)))
    if missing_fields:
        msg = f"Lines with no 'typ_id' must define {required_fields}. Line {line_id!r} is missing {missing_fields}."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)
    length = lne_series["dline"]  # km
    z0 = (lne_series["R0"] + 1j * lne_series["X0"]) / length  # Ω/km
    z1 = (lne_series["R1"] + 1j * lne_series["X1"]) / length  # Ω/km
    y0 = (lne_series["G0"] + 1j * lne_series["B0"]) / length * 1e-6  # µS/km -> S/km
    y1 = (lne_series["G1"] + 1j * lne_series["B1"]) / length * 1e-6  # µS/km -> S/km
    z3x3, y3x3 = LineParameters._sym_to_zy(id=typ_id, z0=z0, z1=z1, y0=y0, y1=y1)
    zs, zm = z3x3[0, :2]
    ys, ym = y3x3[0, :2]
    n_phases = len(phases)
    z_line = np.full((n_phases, n_phases), fill_value=zm, dtype=np.complex128)
    y_shunt = np.full((n_phases, n_phases), fill_value=ym, dtype=np.complex128)
    np.fill_diagonal(z_line, zs)
    np.fill_diagonal(y_shunt, ys)

    with warnings.catch_warnings():
        warnings.filterwarnings(action="ignore", message=r".* off-diagonal elements ", category=UserWarning)
        lp = LineParameters(id=typ_id, z_line=z_line, y_shunt=y_shunt, line_type=line_type, section=section)

    return lp


def generate_lines(
    elm_lne: pd.DataFrame,
    branches: dict[Id, AbstractBranch],
    buses: dict[Id, Bus],
    sta_cubic: pd.DataFrame,
    lines_params: dict[Id, LineParameters],
    ground: Ground,
) -> None:
    """Generate the lines of the network.

    Args:
        elm_lne:
            The "ElmLne" dataframe containing the line data.

        branches:
            The dictionary to store the lines into.

        buses:
            The dictionary of the all buses.

        sta_cubic:
            The "StaCubic" dataframe of cubicles.

        lines_params:
            The dictionary of all lines parameters. If the line does not define a type Id, a line
            parameters object will be created and stored in this dictionary.

        ground:
            The ground object to connect to lines that have shunt components.
    """
    has_geometry = "GPScoords:SIZEROW" in elm_lne.columns
    for line_id in elm_lne.index:
        type_id = elm_lne.at[line_id, "typ_id"]  # id of the line type
        bus1 = buses[sta_cubic.at[elm_lne.at[line_id, "bus1"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_lne.at[line_id, "bus2"], "cterm"]]
        length = elm_lne.at[line_id, "dline"]
        phases = "abcn" if (bus1.phases == "abcn" and bus2.phases == "abcn") else "abc"

        if type_id in lines_params:
            lp = lines_params[type_id]
            if phases == "abcn" and lp._z_line.shape[0] == 3:
                phases = "abc"
        elif pd.isna(type_id):  # Missing line type, generate a new one
            lp = generate_typ_lne_from_elm_lne(
                elm_lne=elm_lne, line_id=line_id, phases=phases, lines_params=lines_params
            )
        else:
            msg = f"typ_id {type_id!r} of line {line_id} was not found in the 'type_lne' table"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_TYPE_ID)

        geometry = None
        if has_geometry:
            try:
                nb_points = int(elm_lne.at[line_id, "GPScoords:SIZEROW"])
                latitude_columns = [f"GPScoords:{i}:0" for i in range(nb_points)]
                longitude_columns = [f"GPScoords:{i}:1" for i in range(nb_points)]
                geometry = shapely.LineString(
                    shapely.points(
                        elm_lne.loc[line_id, longitude_columns].values.astype(float),
                        elm_lne.loc[line_id, latitude_columns].values.astype(float),
                    )
                )
            except Exception as e:
                warnings.warn(
                    f"Failed to read geometry data for line {line_id!r}: {type(e).__name__}: {e}", stacklevel=4
                )
        branches[line_id] = Line(
            id=line_id,
            bus1=bus1,
            bus2=bus2,
            length=length,
            parameters=lp,
            ground=ground if lp.with_shunt else None,
            phases=phases,
            geometry=geometry,
        )
