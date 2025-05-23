import logging
import warnings

import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import INSULATORS, LINE_TYPES, MATERIALS
from roseau.load_flow.io.dgs.utils import gps_coords_to_linestring
from roseau.load_flow.models import Bus, Ground, Line, LineParameters
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


#
# DGS -> RLF
#
def typ_lne_to_lp(typ_lne: pd.DataFrame, line_params: dict[str, LineParameters], use_name_as_id: bool) -> None:
    """Generate line parameters from the "TypLne" dataframe.

    Args:
        typ_lne:
            The "TypLne" dataframe containing line parameters data.

        line_params:
            The dictionary to store the line parameters into indexed by the type's FID.

        use_name_as_id:
            Whether to use the type's ``loc_name`` as its ID or the FID.
    """
    # TODO: Maybe add the section of the neutral
    for fid in typ_lne.index:
        name = typ_lne.at[fid, "loc_name"]
        type_id = name if use_name_as_id else fid
        this_typ_lne: pd.Series = typ_lne.loc[fid]
        # TODO: use the detailed phase information instead of n
        nneutral = this_typ_lne["nneutral"]
        n = this_typ_lne["nlnph"] + nneutral
        if n not in (3, 4):
            msg = (
                f"The number of phases ({n}) of line type with FID={fid!r} and loc_name={name!r} "
                f"cannot be handled, it should be 3 or 4."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)

        z_line, y_shunt = LineParameters._sym_to_zy(
            type_id,
            z0=complex(this_typ_lne["rline0"], this_typ_lne["xline0"]),
            z1=complex(this_typ_lne["rline"], this_typ_lne["xline"]),
            y0=complex(this_typ_lne["gline0"], this_typ_lne["bline0"]) * 1e-6,
            y1=complex(this_typ_lne["gline"], this_typ_lne["bline"]) * 1e-6,
            zn=complex(this_typ_lne["rnline"], this_typ_lne["xnline"]) if nneutral else None,
            zpn=complex(this_typ_lne["rpnline"], this_typ_lne["xpnline"]) if nneutral else None,
            bn=(this_typ_lne["bnline"] * 1e-6) if nneutral else None,
            bpn=(this_typ_lne["bpnline"] * 1e-6) if nneutral else None,
        )

        actual_n = z_line.shape[0]
        if actual_n > n:  # 4x4 matrix while a 3x3 matrix was expected
            # Extract the 3x3 underlying matrix
            z_line = z_line[:n, :n]
            y_shunt = y_shunt[:n, :n]
        elif actual_n == n:
            # Everything ok
            pass
        else:
            # Something unexpected happened
            msg = (
                f"A {n}x{n} impedance matrix was expected for the line type with FID={fid!r} and "
                f"loc_name={name!r} but a {actual_n}x{actual_n} matrix was generated."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)

        # Optional fields
        sline = this_typ_lne.get("sline")
        ampacity = sline * 1e3 if sline is not None else None
        line_type = LINE_TYPES.get(this_typ_lne["cohl_"]) if "cohl_" in this_typ_lne else None
        material = MATERIALS.get(this_typ_lne["mlei"]) if "mlei" in this_typ_lne else None
        insulator = INSULATORS.get(this_typ_lne["imiso"]) if "imiso" in this_typ_lne else None
        section = this_typ_lne.get("qurs") or None  # Sometimes it is zero!! replace by None in this case

        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", message=r".* off-diagonal elements ", category=UserWarning)
            lp = LineParameters(
                id=type_id,
                z_line=z_line,
                y_shunt=y_shunt,
                ampacities=ampacity,
                line_type=line_type,
                materials=material,
                insulators=insulator,
                sections=section,
            )
        line_params[fid] = lp


def typ_lne_from_elm_lne_to_lp(
    elm_lne: pd.DataFrame, line_id: Id, phases: str, line_params: dict[str, LineParameters]
) -> LineParameters:
    """Generate line parameters for a certain line.

    Args:
        elm_lne:
            The "ElmLne" dataframe containing line parameters data.

        line_id:
            The ID of the line in the dataframe.

        phases:
            The phases of the line.

        line_params:
            The dictionary to store the line parameters into.

    Returns:
        The generated line parameters.
    """
    lne_series = elm_lne.loc[line_id]
    assert isinstance(lne_series, pd.Series)

    # Get a unique ID for the line parameters (contains the ID of the line)
    typ_id = f"line {line_id!r}"
    i = 1
    while typ_id in line_params:
        typ_id = f"line {line_id!r} ({i})"
        i += 1

    # Get the type of the line (overhead, underground)
    line_type = LINE_TYPES.get(lne_series["inAir"]) if "inAir" in lne_series else None

    # Get the cross-sectional area (mm²)
    section = lne_series.get("crosssec") or None  # Sometimes it is zero!! replace by None in this case
    # TODO The section of the neutral?

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
    z_line, y_shunt = LineParameters._sym_to_zy_simple(n=len(phases), z0=z0, y0=y0, z1=z1, y1=y1)
    LineParameters._check_z_line_matrix(id=typ_id, z_line=z_line)

    with warnings.catch_warnings():
        warnings.filterwarnings(action="ignore", message=r".* off-diagonal elements ", category=UserWarning)
        lp = LineParameters(id=typ_id, z_line=z_line, y_shunt=y_shunt, line_type=line_type, sections=section)

    return lp


def elm_lne_to_lines(
    elm_lne: pd.DataFrame,
    lines: dict[Id, Line],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    line_params: dict[str, LineParameters],
    ground: Ground,
) -> None:
    """Generate the lines of the network.

    Args:
        elm_lne:
            The "ElmLne" dataframe containing the line data.

        lines:
            The dictionary to store the lines into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.

        line_params:
            The dictionary of all lines parameters indexed by their FID. If the line does not define
            a type Id, a line parameters object will be created and stored in this dictionary.

        ground:
            The ground object to connect to lines that have shunt components.
    """
    has_geometry = "GPScoords:SIZEROW" in elm_lne.columns
    for line_id in elm_lne.index:
        type_fid = elm_lne.at[line_id, "typ_id"]  # FID of the line type
        bus1 = buses[sta_cubic.at[elm_lne.at[line_id, "bus1"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_lne.at[line_id, "bus2"], "cterm"]]
        length = elm_lne.at[line_id, "dline"]
        phases = "abcn" if (bus1.phases == "abcn" and bus2.phases == "abcn") else "abc"

        if type_fid in line_params:
            lp = line_params[type_fid]
            if phases == "abcn" and lp._z_line.shape[0] == 3:
                phases = "abc"
        elif pd.isna(type_fid):  # Missing line type, generate a new one
            lp = typ_lne_from_elm_lne_to_lp(elm_lne=elm_lne, line_id=line_id, phases=phases, line_params=line_params)
        else:
            msg = f"typ_id {type_fid!r} of line {line_id!r} was not found in the 'type_lne' table"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_TYPE_ID)
        geometry = gps_coords_to_linestring(elm_lne, line_id) if has_geometry else None
        lines[line_id] = Line(
            id=line_id,
            bus1=bus1,
            bus2=bus2,
            length=length,
            parameters=lp,
            ground=ground if lp.with_shunt else None,
            phases=phases,
            geometry=geometry,
        )
