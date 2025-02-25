import logging

import pandas as pd

from roseau.load_flow.constants import SQRT3
from roseau.load_flow.models import Bus, VoltageSource
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


#
# DGS -> RLF
#
def elm_xnet_to_sources(
    elm_xnet: pd.DataFrame,
    sources: dict[Id, VoltageSource],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
) -> None:
    """Generate the sources of the network from External Network data.

    Args:
        elm_xnet:
            The "ElmXnet" dataframe containing the external network data.

        sources:
            The dictionary to store the sources into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.
    """
    for source_id in elm_xnet.index:
        bus = buses[sta_cubic.at[elm_xnet.at[source_id, "bus1"], "cterm"]]
        tap = elm_xnet.at[source_id, "usetp"]  # tap voltage (p.u.)
        voltage = bus.nominal_voltage.m / SQRT3 * tap  # phase-to-neutral voltage (V)

        # TODO remove hard coded phases (requires adapting voltages for delta sources)
        sources[source_id] = VoltageSource(id=source_id, bus=bus, phases="abcn", voltages=voltage)
