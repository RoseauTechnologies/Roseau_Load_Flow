import logging

import numpy as np
import pandas as pd

from roseau.load_flow.constants import SQRT3
from roseau.load_flow.models import Bus, Ground, GroundConnection, VoltageSource
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def _get_int(df: pd.DataFrame, idx: Id, column: str) -> int | None:
    """Get an integer value of a dataframe row, or None if the column or the value is missing."""
    if column not in df.columns:
        return None
    value = df.at[idx, column]
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return int(value)


#
# DGS -> RLF
#
def elm_xnet_to_sources(
    elm_xnet: pd.DataFrame,
    sources: dict[Id, VoltageSource],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    ground: Ground,
    ground_connections: dict[Id, GroundConnection],
) -> set[Id]:
    """Generate the sources of the network from External Network data.

    The star point of an external grid is earthed (``cgnd = 0``, the default) or not
    (``cgnd = 1``), and connected to the neutral of its terminal (``iintgnd = 1``, the default) or
    not (``iintgnd = 0``). When the terminal has a neutral:

    - a star point connected to the neutral of the terminal earths this neutral, unless it is not
      earthed;
    - a star point not connected to the neutral of the terminal gives the source a floating
      neutral, itself earthed unless the star point is not earthed: the neutral of the terminal is
      then only earthed elsewhere, if at all.

    Args:
        elm_xnet:
            The "ElmXnet" dataframe containing the external network data.

        sources:
            The dictionary to store the sources into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.

        ground:
            The ground of the network.

        ground_connections:
            The dictionary to store the ground connections of the earthed star points into.

    Returns:
        The IDs of the sources whose star point is not connected to the neutral of their bus: their
        buses must not be preferred as potential references.
    """
    separate_star_points: set[Id] = set()
    for source_id in elm_xnet.index:
        bus = buses[sta_cubic.at[elm_xnet.at[source_id, "bus1"], "cterm"]]
        tap = elm_xnet.at[source_id, "usetp"]  # tap voltage (p.u.)
        un = bus.nominal_voltage
        assert un is not None, f"Bus {bus.id} of the source {source_id!r} has no nominal voltage"
        voltage = un.m / SQRT3 * tap  # phase-to-neutral voltage (V)
        earthed = _get_int(elm_xnet, source_id, "cgnd") != 1
        star_point_connected = _get_int(elm_xnet, source_id, "iintgnd") != 0

        # TODO remove hard coded phases (requires adapting voltages for delta sources)
        if "n" in bus.phases and not star_point_connected:
            # The star point is not connected to the neutral of the bus: the source has its own
            # neutral, earthed directly if the star point is earthed
            source = VoltageSource(id=source_id, bus=bus, phases="abcn", voltages=voltage, connect_neutral=False)
            if earthed:
                gc = GroundConnection(id=f"gc (source {source_id!r})", element=source, ground=ground)
                ground_connections[gc.id] = gc
            separate_star_points.add(source_id)
        else:
            source = VoltageSource(id=source_id, bus=bus, phases="abcn", voltages=voltage)
            if "n" in bus.phases and earthed:
                # The earthed star point is connected to the neutral of the bus
                gc = GroundConnection(id=f"gc (source {source_id!r})", element=bus, ground=ground)
                ground_connections[gc.id] = gc
        sources[source_id] = source
    return separate_star_points
