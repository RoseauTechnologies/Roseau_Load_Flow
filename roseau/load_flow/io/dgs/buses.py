import logging

import pandas as pd
import shapely

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import BUS_PHASES
from roseau.load_flow.models import Bus

logger = logging.getLogger(__name__)


#
# DGS -> RLF
#
def elm_term_to_buses(elm_term: pd.DataFrame, buses: dict[str, Bus], use_name_as_id: bool) -> None:
    """Generate the buses of the network.

    Args:
        elm_term:
            The "ElmTerm" dataframe containing the bus data.

        buses:
            The dictionary to store the buses into.

        use_name_as_id:
            Whether to use the bus's ``loc_name`` as its ID or the FID.
    """
    has_geometry = "GPSlon" in elm_term.columns and "GPSlat" in elm_term.columns
    for fid in elm_term.index:
        name = elm_term.at[fid, "loc_name"]
        bus_id = name if use_name_as_id else fid
        ph_tech = elm_term.at[fid, "phtech"]
        u_nom = elm_term.at[fid, "uknom"] * 1e3  # phase-to-phase voltage (V)
        phases = BUS_PHASES.get(ph_tech)
        if phases is None:
            msg = f"The Ph tech {ph_tech!r} for bus with FID={fid!r} and loc_name={name!r} is not supported."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY)
        geometry = shapely.Point(elm_term.at[fid, "GPSlon"], elm_term.at[fid, "GPSlat"]) if has_geometry else None
        buses[fid] = Bus(id=bus_id, phases=phases, geometry=geometry, nominal_voltage=u_nom)
