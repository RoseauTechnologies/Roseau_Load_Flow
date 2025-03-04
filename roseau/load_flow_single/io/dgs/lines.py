import logging
import math
import warnings
from collections.abc import Iterable, Iterator

import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import (
    INSULATORS,
    INSULATORS_REVERSE,
    LINE_TYPES,
    LINE_TYPES_REVERSE,
    MATERIALS,
    MATERIALS_REVERSE,
)
from roseau.load_flow.io.dgs.utils import (
    DGSData,
    clean_id,
    get_id_to_fid_map,
    gps_coords_to_linestring,
    linestring_to_gps_coords,
)
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_single.io.dgs.pwf import STA_CUBIC_FID_INDEX, STA_CUBIC_OBJ_ID_INDEX
from roseau.load_flow_single.models import Bus, Line, LineParameters

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
    for fid in typ_lne.index:
        name = clean_id(typ_lne.at[fid, "loc_name"])
        type_id = name if use_name_as_id else fid
        this_typ_lne: pd.Series = typ_lne.loc[fid]
        if (n := this_typ_lne["nlnph"]) != 3:
            msg = f"Only 3 phase line are supported. Line type with FID={fid!r} and loc_name={name!r} has {n} phases."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)

        # Only the positive sequence impedance and admittance are used
        z_line = complex(this_typ_lne["rline"], this_typ_lne["xline"])
        y_shunt = complex(this_typ_lne["gline"], this_typ_lne["bline"]) * 1e-6

        # Optional fields
        sline = this_typ_lne.get("sline")
        ampacity = sline * 1e3 if sline is not None else None
        line_type = LINE_TYPES.get(this_typ_lne["cohl_"]) if "cohl_" in this_typ_lne else None
        material = MATERIALS.get(this_typ_lne["mlei"]) if "mlei" in this_typ_lne else None
        insulator = INSULATORS.get(this_typ_lne["imiso"]) if "imiso" in this_typ_lne else None
        section = this_typ_lne.get("qurs") or None  # Sometimes it is zero!! replace by None in this case

        lp = LineParameters(
            id=type_id,
            z_line=z_line,
            y_shunt=y_shunt,
            ampacity=ampacity,
            line_type=line_type,
            material=material,
            insulator=insulator,
            section=section,
        )
        line_params[fid] = lp


def typ_lne_from_elm_lne_to_lp(
    elm_lne: pd.DataFrame, lne_idx: Id, line_params: dict[str, LineParameters]
) -> LineParameters:
    """Generate line parameters for a certain line.

    Args:
        elm_lne:
            The "ElmLne" dataframe containing line parameters data.

        lne_idx:
            The ID of the line in the dataframe.

        line_params:
            The dictionary to store the line parameters into.

    Returns:
        The generated line parameters.
    """
    lne_series = elm_lne.loc[lne_idx]
    assert isinstance(lne_series, pd.Series)

    # Get a unique ID for the line parameters (contains the ID of the line)
    typ_id = f"line {lne_idx!r}"
    i = 1
    while typ_id in line_params:
        typ_id = f"line {lne_idx!r} ({i})"
        i += 1

    # Get the type of the line (overhead, underground)
    line_type = LINE_TYPES.get(lne_series["inAir"]) if "inAir" in lne_series else None

    # Get the cross-sectional area (mm²)
    section = lne_series.get("crosssec") or None  # Sometimes it is zero!! replace by None in this case

    # Get the impedance and admittance matrices
    required_fields = ("X1", "R1", "G1", "B1")
    missing_fields = tuple(f for f in required_fields if pd.isna(lne_series.get(f)))
    if missing_fields:
        msg = f"Lines with no 'typ_id' must define {required_fields}. Line {lne_idx!r} is missing {missing_fields}."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)
    length = lne_series["dline"]  # km
    # Only the positive sequence impedance and admittance are used
    z_line = (lne_series["R1"] + 1j * lne_series["X1"]) / length  # Ω/km
    y_shunt = (lne_series["G1"] + 1j * lne_series["B1"]) / length * 1e-6  # µS/km -> S/km

    lp = LineParameters(id=typ_id, z_line=z_line, y_shunt=y_shunt, line_type=line_type, section=section)

    return lp


def elm_lne_to_lines(
    elm_lne: pd.DataFrame,
    lines: dict[Id, Line],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    line_params: dict[str, LineParameters],
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
    """
    has_geometry = "GPScoords:SIZEROW" in elm_lne.columns
    has_maxload = "maxload" in elm_lne.columns
    for idx in elm_lne.index:
        line_id = clean_id(idx)
        typ_id = elm_lne.at[idx, "typ_id"]  # FID of the line type
        bus1 = buses[sta_cubic.at[elm_lne.at[idx, "bus1"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_lne.at[idx, "bus2"], "cterm"]]
        length = elm_lne.at[idx, "dline"]
        maxload = Q_(elm_lne.at[idx, "maxload"] if has_maxload else 100, "percent")

        if typ_id in line_params:
            lp = line_params[typ_id]
        elif pd.isna(typ_id):  # Missing line type, generate a new one
            lp = typ_lne_from_elm_lne_to_lp(elm_lne=elm_lne, lne_idx=idx, line_params=line_params)
        else:
            msg = f"typ_id {typ_id!r} of line {line_id!r} was not found in the 'type_lne' table"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_TYPE_ID)
        geometry = gps_coords_to_linestring(elm_lne, idx) if has_geometry else None
        lines[line_id] = Line(
            id=line_id,
            bus1=bus1,
            bus2=bus2,
            length=length,
            parameters=lp,
            max_loading=maxload,
            geometry=geometry,
        )


#
# RLF -> DGS
#
def lp_to_typ_lne(
    line_params: Iterable[LineParameters],
    lp_uns: Iterable[set[float]],
    fid_counter: Iterator[str],
) -> DGSData:
    """Generate the "TypLne" dataframe from line parameters.

    Args:
        line_params:
            An iterable of line parameters and their nominal voltage to convert to the dataframe.

        lp_uns:
            An iterable of sets of nominal voltages of the buses connected to the lines of each line
            parameters in the line_params iterable.

        fid_counter:
            An iterator to generate unique FIDs.

    Returns:
        The "TypLne" dataframe.
    """
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "uline",  # Rated Voltage in kV
        "sline",  # Rated Current in kA
        "InomAir",  # Rated Current (in air) in kA
        "mlei",  # Parameters per Length 1,2-Sequence: Conductor Material
        "cohl_",  # Cable / OHL:Cable:Overhead Line
        "systp",  # System Type:AC:DC
        "nlnph",  # Phases:1:2:3
        "nneutral",  # Number of Neutrals:0:1
        "frnom",  # Nominal Frequency in Hz
        "rline",  # Parameters per Length 1,2-Sequence: AC-Resistance R'(20°C) in Ohm/km
        "xline",  #  Parameters per Length 1,2-Sequence: Reactance X' in Ohm/km
        "lline",  #  Parameters per Length 1,2-Sequence: Inductance L' in mH/km
        "rline0",  #  Parameters per Length Zero Sequence: AC-Resistance R0' in Ohm/km
        "xline0",  #  Parameters per Length Zero Sequence: Reactance X0' in Ohm/km
        "lline0",  #  Parameters per Length Zero Sequence: Inductance L0' in mH/km
        "rnline",  #  Parameters per Length, Neutral: AC-Resistance Rn' in Ohm/km
        "xnline",  #  Parameters per Length, Neutral: Reactance Xn' in Ohm/km
        "lnline",  #  Parameters per Length, Neutral: Inductance Ln' in mH/km
        "rpnline",  #  Parameters per Length, Phase-Neutral Coupling: AC-Resistance Rpn' in Ohm/km
        "xpnline",  #  Parameters per Length, Phase-Neutral Coupling: Reactance Xpn' in Ohm/km
        "lpnline",  #  Parameters per Length, Phase-Neutral Coupling: Inductance Lpn' in mH/km
        "bline",  #  Parameters per Length 1,2-Sequence: Susceptance B' in uS/km
        "cline",  #  Parameters per Length 1,2-Sequence: Capacitance C' in uF/km
        "tline",  #  Parameters per Length 1,2-Sequence: Ins. Factor
        "gline",  #  Parameters per Length 1,2-Sequence: Conductance G' in uS/km
        "bline0",  #  Parameters per Length Zero Sequence: Susceptance B0' in uS/km
        "cline0",  #  Parameters per Length Zero Sequence: Capacitance C0' in uF/km
        "gline0",  #  Parameters per Length Zero Sequence: Conductance G0' in uS/km
        "bnline",  #  Parameters per Length, Neutral: Susceptance Bn' in uS/km
        "cnline",  #  Parameters per Length, Neutral: Capacitance Cn' in uF/km
        "bpnline",  #  Parameters per Length, Phase-Neutral Coupling: Susceptance Bpn' in uS/km
        "cpnline",  #  Parameters per Length, Phase-Neutral Coupling: Capacitance Cpn' in uF/km
        "imiso",  # Cable Design Parameter: Insulation Material:PVC:XLPE:Mineral:Paper:EPR
        "qurs",  # Nominal Cross Section in mm^2
        "shins",  # Cable Design Parameter With Sheath: Sheath Insulation Material
        "shtyp",  # Cable Design Parameter With Sheath: Sheath Type:Non-Metallic:Metallic
        "fr_sheath",  # Cable Design Parameter: With Sheath
    ]
    values: list[list[str | float | None]] = []
    frnom = 50  # Nominal Frequency in Hz
    omega = 2 * math.pi * frnom
    for lp, uns in zip(line_params, lp_uns, strict=True):
        if len(uns) == 0:
            uline = 0.0
            warnings.warn(
                (
                    f"Cannot determine the nominal voltage of line parameters {lp.id!r} because buses "
                    f"connected to its lines do not define a nominal voltage."
                ),
                stacklevel=find_stack_level(),
            )
        elif len(uns) > 1:
            uline = max(uns)
            warnings.warn(
                (
                    f"Line parameters {lp.id!r} has line that are connected to buses with different "
                    f"nominal voltages {sorted(uns)}. This may cause errors in the load flow "
                    f"calculation in PowerFactory. Choosing {uline} V as the nominal voltage."
                ),
                stacklevel=find_stack_level(),
            )
        else:
            uline = next(iter(uns))

        sline = lp._ampacity / 1e3 if lp._ampacity is not None else None
        mlei = MATERIALS_REVERSE.get(lp._material) if lp._material is not None else None
        cohl_ = LINE_TYPES_REVERSE.get(lp._line_type) if lp._line_type is not None else None
        imiso = INSULATORS_REVERSE.get(lp._insulator) if lp._insulator is not None else ""
        rline = lp._z_line.real  # Ohm/km
        xline = lp._z_line.imag  # Ohm/km
        gline = lp._y_shunt.real * 1e6  # µS/km
        bline = lp._y_shunt.imag * 1e6  # µS/km
        lline = xline / omega * 1e3  # mH/km
        cline = bline / omega  # uF/km

        typ_lne = [
            next(fid_counter),  # FID
            "C",  # OP
            lp.id,  # loc_name
            None,  # fold_id
            uline,  # uline
            sline,  # sline
            sline,  # InomAir
            mlei,  # mlei
            cohl_,  # cohl_
            0,  # systp
            3,  # nlnph
            0,  # nneutral
            frnom,  # frnom
            rline,  # rline
            xline,  # xline
            lline,  # lline
            0,  # rline0
            0,  # xline0
            0,  # lline0
            0,  # rnline
            0,  # xnline
            0,  # lnline
            0,  # rpnline
            0,  # xpnline
            0,  # lpnline
            bline,  # bline
            cline,  # cline
            0,  # tline
            gline,  # gline
            0,  # bline0
            0,  # cline0
            0,  # gline0
            0,  # bnline
            0,  # cnline
            0,  # bpnline
            0,  # cpnline
            imiso,  # imiso
            lp._section or 0,  # qurs
            0,  # shins
            0,  # shtyp
            0,  # fr_sheath
        ]
        values.append(typ_lne)
    return {"Attributes": attributes, "Values": values}


def lines_to_elm_lne(
    lines: Iterable[Line],
    typ_lne: DGSData,
    fid_counter: Iterator[str],
    sta_cubic: dict[Id, tuple[list, list]],
    fold_id: str,
) -> DGSData:
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "typ_id",  # Type in TypLne,TypTow,TypGeo,TypCabsys
        "inAir",  # Parameters: Laying:Ground:Air
        # "crosssec",  # Cross Section in mm^2
        "bus1",  # Terminal i in StaCubic
        "bus2",  # Terminal j in StaCubic
        "dline",  # Parameters: Length of Line in km
        "nlnum",  # Number of: parallel Lines
        "maxload",  # Maximum Loading in %
    ]
    gps_attributes: dict[str, None] = {}  # dict keys used as an ordered set
    values: list[list[str | float | None]] = []

    typ_fid_by_id = get_id_to_fid_map(typ_lne)

    for line in lines:
        fid = next(fid_counter)
        typ_id = typ_fid_by_id[line.parameters.id]
        laying = LINE_TYPES_REVERSE.get(line.parameters._line_type) if line.parameters._line_type is not None else None
        # crosssec = line.parameters._section or 0
        cubic1, cubic2 = sta_cubic[line.id]
        cubic1[STA_CUBIC_OBJ_ID_INDEX] = fid
        cubic2[STA_CUBIC_OBJ_ID_INDEX] = fid
        gps_coords = linestring_to_gps_coords(line.geometry)
        gps_attributes.update(dict.fromkeys(gps_coords))

        values.append(
            [
                fid,  # FID
                "C",  # OP
                line.id,  # loc_name
                fold_id,  # fold_id
                typ_id,  # typ_id
                laying,  # inAir
                # crosssec,  # crosssec
                cubic1[STA_CUBIC_FID_INDEX],  # bus1
                cubic2[STA_CUBIC_FID_INDEX],  # bus2
                line._length,  # dline
                1,  # nlnum
                line.max_loading.m_as("percent"),  # maxload
                *gps_coords.values(),
            ]
        )
    attributes.extend(gps_attributes.keys())
    return {"Attributes": attributes, "Values": values}
