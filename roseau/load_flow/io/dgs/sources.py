import logging

import numpy as np
import pandas as pd

from roseau.load_flow.models import AbstractLoad, Bus, Ground, PotentialRef, VoltageSource
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def generate_sources(
    elm_xnet: pd.DataFrame,
    sources: dict[Id, AbstractLoad],
    buses: dict[Id, Bus],
    potential_refs: dict[Id, PotentialRef],
    sta_cubic: pd.DataFrame,
    elm_term: pd.DataFrame,
    ground: Ground,
    has_transfomers: bool,
) -> None:
    """Generate the sources of the network from External Network data.

    Args:
        elm_xnet:
            The "ElmXnet" dataframe containing the external network data.

        sources:
            The dictionary to store the sources into.

        buses:
            The dictionary of the all buses.

        potential_refs:
            The dictionary of the all potential references.

        sta_cubic:
            The "StaCubic" dataframe of cubicles.

        elm_term:
            The "ElmTerm" dataframe containing the bus data.

        ground:
            The ground element to connect to the neutral of the source bus if any.

        has_transfomers:
            Does the network have any transformer?
    """
    for source_id in elm_xnet.index:
        id_sta_cubic_source = elm_xnet.at[source_id, "bus1"]  # id of the cubicle connecting the source and its bus
        bus_id = sta_cubic.at[id_sta_cubic_source, "cterm"]  # id of the bus to which the source is connected
        un = elm_term.at[bus_id, "uknom"] / np.sqrt(3) * 1e3  # phase-to-neutral voltage (V)
        tap = elm_xnet.at[source_id, "usetp"]  # tap voltage (p.u.)
        voltages = un * tap * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3)])
        source_bus = buses[bus_id]

        sources[source_id] = VoltageSource(id=source_id, bus=source_bus, phases="abcn", voltages=voltages)
        if "n" in source_bus.phases:
            ground.connect(source_bus)
        elif has_transfomers:
            source_pref = PotentialRef(f"pref (source {source_id!r})", element=source_bus)  # Delta potential ref
            potential_refs[source_pref.id] = source_pref
