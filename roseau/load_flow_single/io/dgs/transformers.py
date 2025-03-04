import logging
import math
import warnings
from collections.abc import Iterable, Iterator

import pandas as pd
import shapely

from roseau.load_flow.io.dgs.utils import (
    DGSData,
    clean_id,
    generate_extra_rlf_data,
    get_id_to_fid_map,
    parse_extra_rlf_data,
)
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_single.io.dgs.pwf import STA_CUBIC_FID_INDEX, STA_CUBIC_OBJ_ID_INDEX
from roseau.load_flow_single.models import Bus, Transformer, TransformerParameters

logger = logging.getLogger(__name__)


#
# DGS -> RLF
#
def typ_tr2_to_tp(
    typ_tr: pd.DataFrame,
    tr_params: dict[str, TransformerParameters],
    tr_taps: dict[str, float],
    use_name_as_id: bool,
) -> None:
    """Generate transformer parameters from the "TypTr2" dataframe.

    Args:
        typ_tr:
            The "TypTr2" dataframe containing transformer parameters data.

        tr_params:
            The dictionary to store the parameters into indexed by the type's FID.

        tr_taps:
            The dictionary to store the tap positions into indexed by the type's FID.

        use_name_as_id:
            Whether to use the type's ``loc_name`` as its ID or the FID.
    """
    has_manuf = "manuf" in typ_tr.columns
    has_desc0 = "desc:0" in typ_tr.columns
    for fid in typ_tr.index:
        name = clean_id(typ_tr.at[fid, "loc_name"])
        type_id = name if use_name_as_id else fid
        sn = Q_(typ_tr.at[fid, "strn"], "MVA")  # The nominal power of the transformer (MVA)
        uhv = Q_(typ_tr.at[fid, "utrn_h"], "kV")  # Phase-to-phase nominal voltage of the HV side (kV)
        ulv = Q_(typ_tr.at[fid, "utrn_l"], "kV")  # Phase-to-phase nominal voltage of the LV side (kV)
        i0 = Q_(typ_tr.at[fid, "curmg"], "percent")  # Current during off-load test (%)
        p0 = Q_(typ_tr.at[fid, "pfe"], "kW")  # Losses during off-load test (kW)
        psc = Q_(typ_tr.at[fid, "pcutr"], "kW")  # Losses during short-circuit test (kW)
        vsc = Q_(typ_tr.at[fid, "uktr"], "percent")  # Voltages on LV side during short-circuit test (%)
        whv = typ_tr.at[fid, "tr2cn_h"]  # Vector Group: HV-Side
        wlv = typ_tr.at[fid, "tr2cn_l"]  # Vector Group: LV-Side
        clock = typ_tr.at[fid, "nt2ag"]  # Vector Group: Phase Shift
        vg = f"{whv}{wlv.lower()}{clock}"
        manufacturer = typ_tr.at[fid, "manuf"] if has_manuf else None
        extra_data = parse_extra_rlf_data(typ_tr.at[fid, "desc:0"]) if has_desc0 else {}

        # Generate transformer parameters
        tr_params[fid] = TransformerParameters.from_open_and_short_circuit_tests(
            id=type_id,
            vg=vg,
            uhv=uhv,
            ulv=ulv,
            sn=sn,
            p0=p0,
            i0=i0,
            psc=psc,
            vsc=vsc,
            manufacturer=manufacturer,
            **extra_data,
        )
        tr_taps[fid] = typ_tr.at[fid, "dutap"]


def elm_tr2_to_transformers(
    elm_tr: pd.DataFrame,
    transformers: dict[Id, Transformer],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    tr_taps: dict[str, float],
    tr_params: dict[str, TransformerParameters],
) -> None:
    """Generate the transformers of the network.

    Args:
        elm_tr:
            The "ElmTr2" dataframe containing the transformer data.

        transformers:
            The dictionary to store the transformers into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.

        tr_taps:
            The dictionary of all transformers tap positions indexed by the type's FID.

        tr_params:
            The dictionary of all transformers parameters indexed by their FID.
    """
    has_maxload = "maxload" in elm_tr.columns
    for idx in elm_tr.index:
        tr_id = clean_id(idx)
        typ_id = elm_tr.at[idx, "typ_id"]  # FID of the transformer type
        tap = 1.0 - elm_tr.at[idx, "nntap"] * tr_taps[typ_id] / 100
        bus_hv = buses[sta_cubic.at[elm_tr.at[idx, "bushv"], "cterm"]]
        bus_lv = buses[sta_cubic.at[elm_tr.at[idx, "buslv"], "cterm"]]
        maxload = Q_(elm_tr.at[idx, "maxload"] if has_maxload else 100, "percent")
        # petersen = elm_tr.at[idx, "cpeter_l"]  # Petersen coil
        # z_gnd = elm_tr.at[idx, "re0tr_l"] + 1j * elm_tr.at[idx, "xe0tr_l"]  # Grounding impedance
        # Transformers do not have geometries, use the buses
        geometry = (
            shapely.LineString([bus_hv.geometry, bus_lv.geometry]).centroid  # type: ignore
            if bus_hv.geometry is not None and bus_lv.geometry is not None
            else None
        )
        transformers[tr_id] = Transformer(
            id=tr_id,
            bus_hv=bus_hv,
            bus_lv=bus_lv,
            parameters=tr_params[typ_id],
            tap=tap,
            max_loading=maxload,
            geometry=geometry,
        )


#
# RLF -> DGS
#
DU_TAP = 0.5  # Additional voltage per tap in %


def tp_to_typ_tr2(transformer_params: Iterable[TransformerParameters], fid_counter: Iterator[str]) -> DGSData:
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "frnom",  # Nominal Frequency in Hz
        "strn",  # Rated Power in MVA
        "nt2ph",  # Technology
        "tr2cn_h",  # Vector Group: HV-Side:Y :YN:Z :ZN:D
        "tr2cn_l",  # Vector Group: LV-Side:Y :YN:Z :ZN:D
        "nt2ag",  # Vector Group: Phase Shift in *30deg
        "utrn_h",  # Rated Voltage: HV-Side in kV
        "utrn_l",  # Rated Voltage: LV-Side in kV
        "uktr",  # Positive Sequence Impedance: Short-Circuit Voltage uk in %
        "pcutr",  # Positive Sequence Impedance: Copper Losses in kW
        "uk0tr",  # Zero Sequence Impedance: Short-Circuit Voltage uk0 in %
        "ur0tr",  # Zero Sequence Impedance: SHC-Voltage (Re(uk0)) uk0r in %
        "pfe",  # Magnetising Impedance: No Load Losses in kW
        "curmg",  # Magnetising Impedance: No Load Current in %
        "zx0hl_n",  # Zero Sequence Magnetising Impedance: Mag. Impedance/uk0
        "rtox0_n",  # Zero Sequence Magnetising Impedance: Mag. R/X
        "tapchtype",  # Tap Changer 1: Type:Ratio/Asym. Phase Shifter:Ideal Phase Shifter:Sym. Phase Shifter
        "tap_side",  # Tap Changer 1: at Side:HV:LV
        "dutap",  # Tap Changer 1: Additional Voltage per Tap in %
        "phitr",  # Tap Changer 1: Phase of du in deg
        "nntap0",  # Tap Changer 1: Neutral Position
        "ntpmn",  # Tap Changer 1: Minimum Position
        "ntpmx",  # Tap Changer 1: Maximum Position
        "manuf",  # Manufacturer
        "desc:0",  # Description (used to store extra RLF data)
    ]
    values: list[list[str | float | None]] = []
    for tp in transformer_params:
        values.append(
            [
                next(fid_counter),  # FID
                "C",  # OP
                tp.id,  # loc_name
                None,  # fold_id
                50,  # frnom
                tp.sn.m_as("MVA"),  # strn
                3,  # nt2ph
                tp.whv,  # tr2cn_h
                tp.wlv.upper(),  # tr2cn_l
                tp.clock,  # nt2ag
                tp.uhv.m_as("kV"),  # utrn_h
                tp.ulv.m_as("kV"),  # utrn_l
                tp.vsc.m_as("percent"),  # uktr
                tp.psc.m_as("kW"),  # pcutr
                0,  # uk0tr TODO
                0,  # ur0tr TODO
                tp.p0.m_as("kW"),  # pfe
                tp.i0.m_as("percent"),  # curmg
                100,  # zx0hl_n
                0,  # rtox0_n
                0,  # tapchtype
                0,  # tap_side
                DU_TAP,  # dutap
                0,  # phitr
                0,  # nntap0
                -20,  # ntpmn
                20,  # ntpmx
                tp.manufacturer,  # manuf
                generate_extra_rlf_data({"range": tp.range, "efficiency": tp.efficiency}),  # desc:0
            ]
        )
    return {"Attributes": attributes, "Values": values}


def transformers_to_elm_tr2(
    transformers: Iterable[Transformer],
    typ_tr2: DGSData,
    fid_counter: Iterator[str],
    sta_cubic: dict[Id, tuple[list, list]],
    fold_id: str,
) -> DGSData:
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "typ_id",  # Type in TypTr2
        "bushv",  # HV-Side in StaCubic
        "buslv",  # LV-Side in StaCubic
        "nntap",  # Tap Changer 1: Tap Position
        "maxload",  # Thermal Loading Limit: Max. loading in %
        "cneutcon",  # Neutral Conductor: N-Connection
        "cgnd_l",  # Internal Grounding Impedance, LV Side: Star Point:Connected:Not connected
        "cpeter_l",  # Internal Grounding Impedance, LV Side: Petersen Coil
        "re0tr_l",  # Internal Grounding Impedance, LV Side: Resistance, Re in Ohm
        "xe0tr_l",  # Internal Grounding Impedance, LV Side: Reactance, Xe in Ohm
    ]
    values: list[list[str | float | None]] = []
    typ_fid_by_id = get_id_to_fid_map(typ_tr2)
    for tr in transformers:
        fid = next(fid_counter)
        cubic_hv, cubic_lv = sta_cubic[tr.id]
        cubic_hv[STA_CUBIC_OBJ_ID_INDEX] = fid
        cubic_lv[STA_CUBIC_OBJ_ID_INDEX] = fid
        nntap_float = 100 * (1.0 - tr.tap) / DU_TAP
        nntap = round(nntap_float)
        if not math.isclose(nntap_float, nntap, abs_tol=0.1):
            warnings.warn(
                (
                    f"Transformer {tr.id!r} has tap value {tr.tap} which is equivalent to position "
                    f"{nntap_float} of {DU_TAP}% additional voltage per tap. Setting the tap position "
                    f"to {nntap} instead."
                ),
                stacklevel=find_stack_level(),
            )
        values.append(
            [
                fid,  # FID
                "C",  # OP
                tr.id,  # loc_name
                fold_id,  # fold_id
                typ_fid_by_id[tr.parameters.id],  # typ_id
                cubic_hv[STA_CUBIC_FID_INDEX],  # bushv
                cubic_lv[STA_CUBIC_FID_INDEX],  # buslv
                nntap,  # nntap
                tr.max_loading.m_as("percent"),  # maxload
                0,  # cneutcon
                0,  # cgnd_l
                0,  # cpeter_l
                0,  # re0tr_l
                0,  # xe0tr_l
            ]
        )
    return {"Attributes": attributes, "Values": values}
