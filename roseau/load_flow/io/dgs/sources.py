import logging

import numpy as np
import pandas as pd

from roseau.load_flow.models import Bus, VoltageSource
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def generate_sources(
    elm_xnet: pd.DataFrame,
    sources: dict[Id, VoltageSource],
    buses: dict[Id, Bus],
    sta_cubic: pd.DataFrame,
    elm_term: pd.DataFrame,
) -> None:
    """Generate the sources of the network from External Network data.

    Args:
        elm_xnet:
            The "ElmXnet" dataframe containing the external network data.

        sources:
            The dictionary to store the sources into.

        buses:
            The dictionary of the all buses.

        sta_cubic:
            The "StaCubic" dataframe of cubicles.

        elm_term:
            The "ElmTerm" dataframe containing the bus data.
    """
    for source_id in elm_xnet.index:
        id_sta_cubic_source = elm_xnet.at[source_id, "bus1"]  # id of the cubicle connecting the source and its bus
        bus_id = sta_cubic.at[id_sta_cubic_source, "cterm"]  # id of the bus to which the source is connected
        un = elm_term.at[bus_id, "uknom"] / np.sqrt(3) * 1e3  # phase-to-neutral voltage (V)
        tap = elm_xnet.at[source_id, "usetp"]  # tap voltage (p.u.)
        voltage = un * tap
        source_bus = buses[bus_id]

        # TODO remove hard coded phases (requires adapting voltages for delta sources)
        sources[source_id] = VoltageSource(id=source_id, bus=source_bus, phases="abcn", voltages=voltage)
