import logging

import pandas as pd
import shapely

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import BUS_PHASES
from roseau.load_flow.models import Bus
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def generate_buses(elm_term: pd.DataFrame, buses: dict[Id, Bus]) -> None:
    """Generate the buses of the network.

    Args:
        elm_term:
            The "ElmTerm" dataframe containing the bus data.

        buses:
            The dictionary to store the buses into.
    """
    has_geometry = "GPSlon" in elm_term.columns and "GPSlat" in elm_term.columns
    for bus_id in elm_term.index:
        ph_tech = elm_term.at[bus_id, "phtech"]
        phases = BUS_PHASES.get(ph_tech)
        if phases is None:
            msg = f"The Ph tech {ph_tech!r} for bus {bus_id!r} is not supported."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY)
        geometry = shapely.Point(elm_term.at[bus_id, "GPSlon"], elm_term.at[bus_id, "GPSlat"]) if has_geometry else None
        buses[bus_id] = Bus(id=bus_id, phases=phases, geometry=geometry)
