import logging
import warnings
from collections.abc import Iterable, Iterator

import pandas as pd
import shapely

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import BUS_PHASES
from roseau.load_flow.io.dgs.utils import DEFAULT_GPS_COORDS, DEFAULT_TERM_VMAX, DEFAULT_TERM_VMIN, DGSData, clean_id
from roseau.load_flow.typing import Id
from roseau.load_flow.units import Q_
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_single.models import Bus

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
    has_vmax = "vmax" in elm_term.columns
    has_vmin = "vmin" in elm_term.columns
    for fid in elm_term.index:
        name = clean_id(elm_term.at[fid, "loc_name"])
        bus_id = name if use_name_as_id else fid
        ph_tech = elm_term.at[fid, "phtech"]
        u_nom = Q_(elm_term.at[fid, "uknom"], "kV")
        u_max = elm_term.at[fid, "vmax"] if has_vmax else None
        u_min = elm_term.at[fid, "vmin"] if has_vmin else None
        phases = BUS_PHASES.get(ph_tech)
        if phases not in {"abc", "abcn"}:
            msg = f"Only three-phase buses are supported, bus with FID={fid!r} and loc_name={name!r} has Ph tech {ph_tech!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY)
        geometry = shapely.Point(elm_term.at[fid, "GPSlon"], elm_term.at[fid, "GPSlat"]) if has_geometry else None
        buses[fid] = Bus(
            id=bus_id,
            geometry=geometry,
            nominal_voltage=u_nom,
            min_voltage_level=u_min,
            max_voltage_level=u_max,
        )


#
# RLF -> DGS
#
def buses_to_elm_term(buses: Iterable[Bus], fid_counter: Iterator[str], fold_id: str) -> DGSData:
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "typ_id",  # Type in TypBar
        "iUsage",  # Usage:Busbar:Junction Node:Internal Node
        "phtech",  # Phase Technology:ABC:ABC-N:BI:BI-N:2PH:2PH-N:1PH:1PH-N:N
        "uknom",  # Nominal Voltage: Line-Line in kV
        "vmax",  # Maximum Voltage in pu
        "vmin",  # Minimum Voltage in pu
        "outserv",  # Out of Service
        "iEarth",  # Earthed
        "GPSlat",  # Geographical Position: Latitude / Northing in deg
        "GPSlon",  # Geographical Position: Longitude / Easting in deg
    ]
    values: list[list[str | float | None]] = []
    buses_missing_un: list[Id] = []
    for bus in buses:
        if bus._nominal_voltage is None:
            buses_missing_un.append(bus.id)
            uknom = None
        else:
            uknom = bus._nominal_voltage / 1e3
        vmax = bus._max_voltage_level if bus._max_voltage_level is not None else DEFAULT_TERM_VMAX
        vmin = bus._min_voltage_level if bus._min_voltage_level is not None else DEFAULT_TERM_VMIN
        geom = bus.geometry.centroid if bus.geometry is not None else DEFAULT_GPS_COORDS
        gpslon, gpslat = geom.x, geom.y
        values.append(
            [
                next(fid_counter),  # FID
                "C",  # OP
                bus.id,  # loc_name
                fold_id,  # fold_id
                None,  # typ_id
                0,  # iUsage
                0,  # phtech
                uknom,  # uknom
                vmax,  # vmax
                vmin,  # vmin
                0,  # outserv
                0,  # iEarth
                gpslat,  # GPSlat
                gpslon,  # GPSlon
            ]
        )
    if buses_missing_un:
        warnings.warn(
            (
                f"Power factory requires all buses to define their nominal voltage. Missing nominal "
                f"voltage might cause problems on import. The following buses do not define their "
                f"nominal voltage: {buses_missing_un}"
            ),
            stacklevel=find_stack_level(),
        )
    return {"Attributes": attributes, "Values": values}
