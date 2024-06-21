import logging

import pandas as pd
import shapely

from roseau.load_flow.models import AbstractBranch, Bus, Switch
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def generate_switches(
    elm_coup: pd.DataFrame, branches: dict[Id, AbstractBranch], buses: dict[Id, Bus], sta_cubic: pd.DataFrame
) -> None:
    """Generate the switches of the network.

    Args:
        elm_coup:
            The "ElmCoup" dataframe containing the switch data.

        branches:
            The dictionary to store the switches into.

        buses:
            The dictionary of the all buses.

        sta_cubic:
            The "StaCubic" dataframe of cubicles.
    """
    has_geometry = "GPSlon" in elm_coup.columns and "GPSlat" in elm_coup.columns
    for switch_id in elm_coup.index:
        # TODO: use the detailed phase information instead of n
        n = elm_coup.at[switch_id, "nphase"] + elm_coup.at[switch_id, "nneutral"]
        phases = "abc" if n == 3 else "abcn"
        bus1 = buses[sta_cubic.at[elm_coup.at[switch_id, "bus1"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_coup.at[switch_id, "bus2"], "cterm"]]
        geometry = (
            shapely.Point(elm_coup.at[switch_id, "GPSlon"], elm_coup.at[switch_id, "GPSlat"]) if has_geometry else None
        )
        branches[switch_id] = Switch(id=switch_id, phases=phases, bus1=bus1, bus2=bus2, geometry=geometry)
