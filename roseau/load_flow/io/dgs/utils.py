import json
import logging
from collections.abc import Iterator, Mapping
from typing import Any, Final, Self, TypedDict

import numpy as np
import pandas as pd
import shapely
from typing_extensions import TypeIs

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import warn_external

logger = logging.getLogger(__name__)

RLF_MARKER: Final = "--roseau-load-flow-data--"

# PowerFactory default values
DEFAULT_TERM_VMAX: Final = 1.05
"""Default maximum voltage level for a terminal in PowerFactory."""
DEFAULT_TERM_VMIN: Final = 0.0
"""Default minimum voltage level for a terminal in PowerFactory."""
DEFAULT_GPS_COORDS: Final = shapely.Point(0.0, 0.0)
"""Default GPS coordinates for a terminal or a switch in PowerFactory."""


class FIDCounter:
    """Simple counter to generate unique FIDs for DGS elements.

    Similar to itertools.count but generates strings instead of integers.
    """

    def __init__(self, start: int = 1) -> None:
        self._counter = start

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> str:
        fid = f"{self._counter}"
        self._counter += 1
        return fid


class DGSData(TypedDict):
    """Type definition for a DGS data dictionary."""

    Attributes: list[str]
    Values: list[list[str | float | None]]


def dgs_dict_to_df(data: Mapping[str, Any], name: str, index_col: str) -> pd.DataFrame:
    """Transform a DGS dictionary of elements into a dataframe indexed by the element ID."""
    df = pd.DataFrame(columns=data[name]["Attributes"], data=data[name]["Values"]).set_index(index_col)
    if not df.index.is_unique:
        msg = f"{name} has non-unique loc_name values, cannot use them as IDs."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_NON_UNIQUE_NAME)
    return df


def parse_dgs_version(data: Mapping[str, Any]) -> tuple[int, ...]:
    """Parse the version of the DGS export, warn on old versions."""
    general_data = dict(zip(data["General"]["Attributes"], zip(*data["General"]["Values"], strict=True), strict=True))
    dgs_version = general_data["Val"][general_data["Descr"].index("Version")]
    dgs_version_tuple = tuple(map(int, dgs_version.split(".")))
    if dgs_version_tuple < (6, 0):
        msg = (
            f"The DGS version {dgs_version} is too old, this may cause conversion errors. Try "
            f"updating the version before exporting."
        )
        warn_external(msg)
    return dgs_version_tuple


def parse_extra_rlf_data(desc: str) -> dict[str, str]:
    """Parse the extra data from the RLF marker in the description of an element."""
    if desc.startswith(RLF_MARKER):
        return json.loads(desc[len(RLF_MARKER) :])
    else:
        return {}


def generate_extra_rlf_data(data: JsonDict) -> str:
    """Generate extra data to store in the description of an element."""
    return f"{RLF_MARKER}{json.dumps(data)}"


def has_typ_lne(typ_lne: pd.DataFrame | None) -> TypeIs[pd.DataFrame]:
    """Check if the network contains line types and warn if not."""
    if typ_lne is None:
        msg = (
            "The network contains lines but it is missing line types (TypLne). Please copy all line "
            "types from the library to the project before exporting otherwise a LineParameter object "
            "will be created for each line."
        )
        warn_external(msg)
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


def iter_dgs_values(dgs_data: DGSData, field: str) -> Iterator[Any]:
    """Iterate over the values of a certain field in a DGS data dictionary."""
    idx = dgs_data["Attributes"].index(field)
    yield from (v[idx] for v in dgs_data["Values"])


def get_id_to_fid_map(dgs_data: DGSData) -> dict[Any, str]:
    """Create a mapping from the ID to the FID for a DGS data dictionary."""
    fid_idx = dgs_data["Attributes"].index("FID")
    id_idx = dgs_data["Attributes"].index("loc_name")
    return {v[id_idx]: v[fid_idx] for v in dgs_data["Values"]}  # type: ignore


def gps_coords_to_linestring(elm_lne: pd.DataFrame, lne_idx: str) -> shapely.LineString | None:
    """Convert GPS coordinates from the ElmLne dataframe to a LineString geometry."""
    geometry = None
    try:
        nb_points = int(elm_lne.at[lne_idx, "GPScoords:SIZEROW"])
        nb_cols = int(elm_lne.at[lne_idx, "GPScoords:SIZECOL"])
        # We need at least 2 points with 2 columns (latitude and longitude)
        if nb_points == 0 or nb_cols == 0:
            pass  # nb_points is 0 -> no GPS points; nb_cols is 0 -> badly initialized GPS data by PwF
        elif nb_points == 1:
            warn_external(f"Failed to read geometry data for line {lne_idx!r}: it has a single GPS point.")
        else:
            assert nb_cols == 2, f"Expected 2 GPS columns (Latitude/Longitude), got {nb_cols}."
            lat_cols = [f"GPScoords:{i}:0" for i in range(nb_points)]
            lon_cols = [f"GPScoords:{i}:1" for i in range(nb_points)]
            geometry = shapely.LineString(
                shapely.points(
                    elm_lne.loc[lne_idx, lon_cols].to_numpy(dtype=float),
                    elm_lne.loc[lne_idx, lat_cols].to_numpy(dtype=float),
                )  # type: ignore
            )
    except Exception as e:
        warn_external(f"Failed to read geometry data for line {lne_idx!r}: {type(e).__name__}: {e}")
    return geometry


def clean_id(fid_or_name: Any, /) -> Id:
    if isinstance(fid_or_name, np.integer):
        return int(fid_or_name)
    elif isinstance(fid_or_name, np.str_):
        return str(fid_or_name)
    else:
        return fid_or_name
