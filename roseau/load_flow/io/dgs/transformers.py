import logging

import pandas as pd
import shapely

from roseau.load_flow.models import Bus, Transformer, TransformerParameters
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_

logger = logging.getLogger(__name__)


def generate_typ_tr(
    typ_tr: pd.DataFrame, transformers_params: dict[Id, TransformerParameters], transformers_tap: dict[Id, float]
) -> None:
    """Generate transformer parameters from the "TypTr2" dataframe.

    Args:
        typ_tr:
            The "TypTr2" dataframe containing transformer parameters data.

        transformers_params:
            The dictionary to store the transformer parameters into.

        transformers_tap:
            The dictionary to store the tap positions of the transformers into.
    """
    for idx in typ_tr.index:
        # Extract data
        name = typ_tr.at[idx, "loc_name"]
        sn = Q_(typ_tr.at[idx, "strn"], "MVA")  # The nominal voltages of the transformer (MVA)
        uhv = Q_(typ_tr.at[idx, "utrn_h"], "kV")  # Phase-to-phase nominal voltages of the high voltages side (kV)
        ulv = Q_(typ_tr.at[idx, "utrn_l"], "kV")  # Phase-to-phase nominal voltages of the low voltages side (kV)
        i0 = Q_(typ_tr.at[idx, "curmg"] / 3, "percent")  # Current during off-load test (%)
        p0 = Q_(typ_tr.at[idx, "pfe"] / 3, "kW")  # Losses during off-load test (kW)
        psc = Q_(typ_tr.at[idx, "pcutr"], "kW")  # Losses during short-circuit test (kW)
        vsc = Q_(typ_tr.at[idx, "uktr"], "percent")  # Voltages on LV side during short-circuit test (%)
        # Windings of the transformer
        windings = f"{typ_tr.at[idx, 'tr2cn_h']}{typ_tr.at[idx, 'tr2cn_l']}{typ_tr.at[idx, 'nt2ag']}"

        # Generate transformer parameters
        transformers_params[idx] = TransformerParameters.from_open_and_short_circuit_tests(
            id=name, type=windings, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc
        )
        transformers_tap[idx] = typ_tr.at[idx, "dutap"]


def generate_transformers(
    elm_tr: pd.DataFrame,
    transformers: dict[Id, Transformer],
    buses: dict[Id, Bus],
    sta_cubic: pd.DataFrame,
    transformers_tap: dict[Id, float],
    transformers_params: dict[Id, TransformerParameters],
) -> None:
    """Generate the transformers of the network.

    Args:
        elm_tr:
            The "ElmTr2" dataframe containing the transformer data.

        transformers:
            The dictionary to store the transformers into.

        buses:
            The dictionary of the all buses.

        sta_cubic:
            The "StaCubic" dataframe of cubicles.

        transformers_tap:
            The dictionary of all transformers tap positions.

        transformers_params:
            The dictionary of all transformers parameters.
    """
    for idx in elm_tr.index:
        type_id = elm_tr.at[idx, "typ_id"]  # id of the transformer type
        tap = 1.0 + elm_tr.at[idx, "nntap"] * transformers_tap[type_id] / 100
        bus1 = buses[sta_cubic.at[elm_tr.at[idx, "bushv"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_tr.at[idx, "buslv"], "cterm"]]
        # petersen = elm_tr.at[idx, "cpeter_l"]  # Petersen coil
        # z_gnd = elm_tr.at[idx, "re0tr_l"] + 1j * elm_tr.at[idx, "xe0tr_l"]  # Grounding impedance
        # Transformers do not have geometries, use the buses
        geometry = (
            shapely.LineString([bus1.geometry, bus2.geometry]).centroid  # type: ignore
            if bus1.geometry is not None and bus2.geometry is not None
            else None
        )
        transformers[idx] = Transformer(
            id=idx, bus1=bus1, bus2=bus2, parameters=transformers_params[type_id], tap=tap, geometry=geometry
        )
