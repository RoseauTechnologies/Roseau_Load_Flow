import logging
from collections.abc import Iterable, Iterator

import pandas as pd
import shapely

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.utils import DEFAULT_GPS_COORDS, DGSData, clean_id
from roseau.load_flow.typing import Id
from roseau.load_flow_single.io.dgs.pwf import STA_CUBIC_FID_INDEX, STA_CUBIC_OBJ_ID_INDEX
from roseau.load_flow_single.models import Bus, Switch

logger = logging.getLogger(__name__)


#
# DGS -> RLF
#
def elm_coup_to_switches(
    elm_coup: pd.DataFrame, switches: dict[Id, Switch], buses: dict[str, Bus], sta_cubic: pd.DataFrame
) -> None:
    """Generate the switches of the network.

    Args:
        elm_coup:
            The "ElmCoup" dataframe containing the switch data.

        switches:
            The dictionary to store the switches into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.
    """
    has_geometry = "GPSlon" in elm_coup.columns and "GPSlat" in elm_coup.columns
    for idx in elm_coup.index:
        sw_id = clean_id(idx)
        nphase = elm_coup.at[idx, "nphase"]
        if nphase != 3:
            msg = f"Only 3-phase switches are supported. Switch {sw_id!r} has nphase={nphase!s}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)
        bus1 = buses[sta_cubic.at[elm_coup.at[idx, "bus1"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_coup.at[idx, "bus2"], "cterm"]]
        geometry = shapely.Point(elm_coup.at[idx, "GPSlon"], elm_coup.at[idx, "GPSlat"]) if has_geometry else None
        closed = bool(elm_coup.at[idx, "on_off"])
        switches[sw_id] = Switch(id=sw_id, bus1=bus1, bus2=bus2, closed=closed, geometry=geometry)


#
# RLF -> DGS
#
def switches_to_elm_coup(
    switches: Iterable[Switch], fid_counter: Iterator[str], sta_cubic: dict[Id, tuple[list, list]]
) -> DGSData:
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "typ_id",  # Type in TypSwitch
        "bus1",  # Terminal i in StaCubic
        "bus2",  # Terminal j in StaCubic
        "nphase",  # No. of Phases:1:2:3
        "nneutral",  # No. of Neutrals:0:1
        "aUsage",  # Switch Type
        "on_off",  # Closed
        "iNeutInter",  # Switch interrupts neutral wire
        "GPSlat",  # Geographical Position: Latitude / Northing in deg
        "GPSlon",  # Geographical Position: Longitude / Easting in deg
    ]
    values: list[list[str | float | None]] = []
    for switch in switches:
        fid = next(fid_counter)
        cubic1, cubic2 = sta_cubic[switch.id]
        cubic1[STA_CUBIC_OBJ_ID_INDEX] = fid
        cubic2[STA_CUBIC_OBJ_ID_INDEX] = fid
        geom = switch.geometry.centroid if switch.geometry is not None else DEFAULT_GPS_COORDS
        gpslon, gpslat = geom.x, geom.y
        on_off = 1 if switch.closed else 0
        values.append(
            [
                fid,  # FID
                "C",  # OP
                switch.id,  # loc_name
                None,  # fold_id
                None,  # typ_id
                cubic1[STA_CUBIC_FID_INDEX],  # bus1
                cubic2[STA_CUBIC_FID_INDEX],  # bus2
                3,  # nphase
                0,  # nneutral
                None,  # aUsage
                on_off,  # on_off
                0,  # iNeutInter
                gpslat,  # GPSlat
                gpslon,  # GPSlon
            ]
        )
    return {"Attributes": attributes, "Values": values}
