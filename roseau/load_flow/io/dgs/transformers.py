import logging

import pandas as pd
import shapely

from roseau.load_flow.models import Bus, Transformer, TransformerParameters
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_

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
    for fid in typ_tr.index:
        name = typ_tr.at[fid, "loc_name"]
        type_id = name if use_name_as_id else fid
        sn = Q_(typ_tr.at[fid, "strn"], "MVA")  # The nominal power of the transformer (MVA)
        uhv = Q_(typ_tr.at[fid, "utrn_h"], "kV")  # Phase-to-phase nominal voltage of the HV side (kV)
        ulv = Q_(typ_tr.at[fid, "utrn_l"], "kV")  # Phase-to-phase nominal voltage of the LV side (kV)
        i0 = Q_(typ_tr.at[fid, "curmg"], "percent")  # Current during off-load test (%)
        p0 = Q_(typ_tr.at[fid, "pfe"], "kW")  # Losses during off-load test (kW)
        psc = Q_(typ_tr.at[fid, "pcutr"], "kW")  # Losses during short-circuit test (kW)
        vsc = Q_(typ_tr.at[fid, "uktr"], "percent")  # Voltages on LV side during short-circuit test (%)
        fn = Q_(typ_tr.at[fid, "frnom"], "Hz")  # Nominal frequency (Hz)
        whv = typ_tr.at[fid, "tr2cn_h"]  # Vector Group: HV-Side
        wlv = typ_tr.at[fid, "tr2cn_l"]  # Vector Group: LV-Side
        clock = typ_tr.at[fid, "nt2ag"]  # Vector Group: Phase Shift
        vg = f"{whv}{wlv}{clock}"

        # Generate transformer parameters
        tr_params[fid] = TransformerParameters.from_open_and_short_circuit_tests(
            id=type_id, vg=vg, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc, fn=fn
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
        type_id = elm_tr.at[idx, "typ_id"]  # FID of the transformer type
        tap = 1.0 + elm_tr.at[idx, "nntap"] * tr_taps[type_id] / 100
        bus_hv = buses[sta_cubic.at[elm_tr.at[idx, "bushv"], "cterm"]]
        bus_lv = buses[sta_cubic.at[elm_tr.at[idx, "buslv"], "cterm"]]
        maxload = (elm_tr.at[idx, "maxload"] / 100) if has_maxload else 1.0
        # petersen = elm_tr.at[idx, "cpeter_l"]  # Petersen coil
        # z_gnd = elm_tr.at[idx, "re0tr_l"] + 1j * elm_tr.at[idx, "xe0tr_l"]  # Grounding impedance
        # Transformers do not have geometries, use the buses
        geometry = (
            shapely.LineString([bus_hv.geometry, bus_lv.geometry]).centroid  # type: ignore
            if bus_hv.geometry is not None and bus_lv.geometry is not None
            else None
        )
        transformers[idx] = Transformer(
            id=idx,
            bus_hv=bus_hv,
            bus_lv=bus_lv,
            parameters=tr_params[type_id],
            tap=tap,
            max_loading=maxload,
            geometry=geometry,
        )
