import logging
import warnings

import pandas as pd
import shapely

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Switch
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def generate_switches(
    elm_coup: pd.DataFrame, switches: dict[Id, Switch], buses: dict[Id, Bus], sta_cubic: pd.DataFrame
) -> None:
    """Generate the switches of the network.

    Args:
        elm_coup:
            The "ElmCoup" dataframe containing the switch data.

        switches:
            The dictionary to store the switches into.

        buses:
            The dictionary of the all buses.

        sta_cubic:
            The "StaCubic" dataframe of cubicles.
    """
    has_geometry = "GPSlon" in elm_coup.columns and "GPSlat" in elm_coup.columns
    for switch_id in elm_coup.index:
        # TODO: use the detailed phase information instead of n
        nphase = elm_coup.at[switch_id, "nphase"]
        nneutral = elm_coup.at[switch_id, "nneutral"]
        if nphase != 3:
            msg = f"nphase={nphase!s} for switch {switch_id!r} is not supported. Only 3-phase switches are currently supported."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)
        phases = "abcn" if nneutral else "abc"
        bus1 = buses[sta_cubic.at[elm_coup.at[switch_id, "bus1"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_coup.at[switch_id, "bus2"], "cterm"]]
        geometry = (
            shapely.Point(elm_coup.at[switch_id, "GPSlon"], elm_coup.at[switch_id, "GPSlat"]) if has_geometry else None
        )
        on_off = elm_coup.at[switch_id, "on_off"]
        if not on_off:
            warnings.warn(
                f"Switch {switch_id!r} is open but switches are always closed in roseau-load-flow.", stacklevel=4
            )
        switches[switch_id] = Switch(id=switch_id, phases=phases, bus1=bus1, bus2=bus2, geometry=geometry)
