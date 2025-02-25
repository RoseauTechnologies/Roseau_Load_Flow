import logging
import warnings
from collections.abc import Iterator
from typing import Any, TypedDict

import pandas as pd
import shapely
from typing_extensions import TypeIs

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils import find_stack_level

logger = logging.getLogger(__name__)


class DGSData(TypedDict):
    """Type definition for a DGS data dictionary."""

    Attributes: list[str]
    Values: list[list[str | float | None]]


def dgs_dict_to_df(data: dict[str, Any], name: str, index_col: str) -> pd.DataFrame:
    """Transform a DGS dictionary of elements into a dataframe indexed by the element ID."""
    df = pd.DataFrame(columns=data[name]["Attributes"], data=data[name]["Values"]).set_index(index_col)
    if not df.index.is_unique:
        msg = f"{name} has non-unique loc_name values, cannot use them as IDs."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_NON_UNIQUE_NAME)
    return df


def parse_dgs_version(data: dict[str, Any]) -> tuple[int, ...]:
    """Parse the version of the DGS export, warn on old versions."""
    general_data = dict(zip(data["General"]["Attributes"], zip(*data["General"]["Values"], strict=True), strict=True))
    dgs_version = general_data["Val"][general_data["Descr"].index("Version")]
    dgs_version_tuple = tuple(map(int, dgs_version.split(".")))
    if dgs_version_tuple < (6, 0):
        msg = (
            f"The DGS version {dgs_version} is too old, this may cause conversion errors. Try "
            f"updating the version before exporting."
        )
        warnings.warn(msg, stacklevel=find_stack_level())
    return dgs_version_tuple


def has_typ_lne(typ_lne: pd.DataFrame | None) -> TypeIs[pd.DataFrame]:
    """Check if the network contains line types and warn if not."""
    if typ_lne is None:
        msg = (
            "The network contains lines but it is missing line types (TypLne). Please copy all line "
            "types from the library to the project before exporting otherwise a LineParameter object "
            "will be created for each line."
        )
        warnings.warn(msg, stacklevel=find_stack_level())
        return False
    else:
        return True


def has_typ_tr2(typ_tr2: pd.DataFrame | None) -> TypeIs[pd.DataFrame]:
    """Check if the network contains transformer types and raise an exception if not."""
    if typ_tr2 is None:
        msg = (
            "The network contains transformers but it is missing transformer types (TypTr2). Please "
            "copy all transformer types from the library to the project before exporting and try "
            "again."
        )
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)
    else:
        return True


def generate_sta_cubic(bus_id: str, phases: str, fid_counter: Iterator[int], sta_cubic: DGSData) -> str:
    fid = f"{next(fid_counter)}"
    it2p = [(phases.index(p) if p in phases else None) for p in "abc"]
    sta_cubic["Values"].append(
        [
            fid,  # FID
            "C",  # OP
            fid,  # loc_name
            None,  # fold_id
            bus_id,  # cterm
            bus_id,  # obj_bus
            None,  # obj_id
            len(phases),  # nphase
            phases,  # cPhInfo
            it2p[0],  # it2p1
            it2p[1],  # it2p2
            it2p[2],  # it2p3
            None,  # iStopFeed
            "0",  # cMajorNodes:SIZEROW
            None,  # cMajorNodes
            None,  # cBusBar
            None,  # cpCB
            None,  # cpCts
            None,  # position
            "0",  # pIntObjs:SIZEROW
            None,  # cpRelays
        ]
    )
    return fid


def linestring_to_gps_coords(geom: shapely.Geometry | None) -> dict[str, str]:
    """Convert a LineString geometry to GPS coordinates.

    The GPS coordinates are stored in the following format:
        * ``GPScoords:SIZEROW``: Number of rows for attribute 'GPScoords'
        * ``GPScoords:SIZECOL``: Number of columns for attribute 'GPScoords'
        * ``GPScoords``: Geographical Position in deg
    """
    if geom is None:
        gps_data = {"GPScoords:SIZEROW": "0", "GPScoords:SIZECOL": "0"}
    elif isinstance(geom, shapely.LineString):
        gps_coords = geom.coords
        gps_data = {
            "GPScoords:SIZEROW": str(len(gps_coords)),
            "GPScoords:SIZECOL": "2",
        }
        for i, (lon, lat) in enumerate(gps_coords):
            gps_data[f"GPScoords:{i}:0"] = str(lat)
            gps_data[f"GPScoords:{i}:1"] = str(lon)
    else:
        raise AssertionError(f"Expected a linestring, got {type(geom).__name__}")
    return gps_data


def get_id_to_fid_map(dgs_data: DGSData) -> dict[Any, str]:
    """Create a mapping from the ID to the FID for a DGS data dictionary."""
    fid_idx = dgs_data["Attributes"].index("FID")
    id_idx = dgs_data["Attributes"].index("loc_name")
    return {v[id_idx]: v[fid_idx] for v in dgs_data["Values"]}  # type: ignore


def gps_coords_to_linestring(elm_lne: pd.DataFrame, line_id: str) -> shapely.LineString | None:
    """Convert GPS coordinates from the ElmLne dataframe to a LineString geometry."""
    geometry = None
    try:
        nb_points = int(elm_lne.at[line_id, "GPScoords:SIZEROW"])
        nb_cols = int(elm_lne.at[line_id, "GPScoords:SIZECOL"])
        # We need at least 2 points with 2 columns (latitude and longitude)
        if nb_points == 0 or nb_cols == 0:
            pass  # nb_points is 0 -> no GPS points; nb_cols is 0 -> badly initialized GPS data by PwF
        elif nb_points == 1:
            warnings.warn(
                f"Failed to read geometry data for line {line_id!r}: it has a single GPS point.",
                stacklevel=find_stack_level(),
            )
        else:
            assert nb_cols == 2, f"Expected 2 GPS columns (Latitude/Longitude), got {nb_cols}."
            lat_cols = [f"GPScoords:{i}:0" for i in range(nb_points)]
            lon_cols = [f"GPScoords:{i}:1" for i in range(nb_points)]
            geometry = shapely.LineString(
                shapely.points(
                    elm_lne.loc[line_id, lon_cols].to_numpy(dtype=float),
                    elm_lne.loc[line_id, lat_cols].to_numpy(dtype=float),
                )  # type: ignore
            )
    except Exception as e:
        warnings.warn(
            f"Failed to read geometry data for line {line_id!r}: {type(e).__name__}: {e}",
            stacklevel=find_stack_level(),
        )
    return geometry
