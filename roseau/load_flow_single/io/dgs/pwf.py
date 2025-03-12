"""PowerFactory specific elements for the DGS export."""

from collections.abc import Iterator
from typing import Any, Final, Literal

from roseau.load_flow.io.dgs.utils import DGSData

STA_CUBIC_ATTRIBUTES: Final = [
    "FID",  # Unique identifier for DGS file
    "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
    "loc_name",  # Name
    "fold_id",  # In Folder
    "cterm",  # Terminal
    "obj_bus",  # Bus Index:Terminal i:Terminal j OR Terminal:Neutral
    "obj_id",  # Connected with in Elm*,RelFuse,StaSua*
    "nphase",  # No of Phases:
    "cPhInfo",  # Phases:
    "it2p1",  # Phase 1
    "it2p2",  # Phase 2
    "it2p3",  # Phase 3
    # "iStopFeed",  # Terminate feeder at this point
    # "position",  # Position
    # "pIntObjs:SIZEROW",  # Number of rows for attribute 'pIntObjs'
]
STA_CUBIC_FID_INDEX: Final = STA_CUBIC_ATTRIBUTES.index("FID")
STA_CUBIC_OBJ_ID_INDEX: Final = STA_CUBIC_ATTRIBUTES.index("obj_id")


def add_sta_cubic_value(
    cterm: str, obj_bus: Literal[0, 1], phases: str, fid_counter: Iterator[str], sta_cubic: DGSData
) -> list[Any]:
    """Add a new value to the StaCubic DGS data.

    Args:
        cterm:
            The FID of the ElmTerm (bus) object.

        obj_bus:
            The bus index. For a load or source this is always zero. For a branch this is either 0
            or 1 to indicate the side.

        phases:
            The phases of the cubicle.

        fid_counter:
            The unique identifier counter.

        sta_cubic:
            The StaCubic DGS data
    """
    fid = next(fid_counter)
    it2p = [(phases.index(p) if p in phases else None) for p in "abc"]
    value = [
        fid,  # FID
        "C",  # OP
        fid,  # loc_name
        cterm,  # fold_id
        cterm,  # cterm
        obj_bus,  # obj_bus
        None,  # obj_id
        len(phases),  # nphase
        phases,  # cPhInfo
        it2p[0],  # it2p1
        it2p[1],  # it2p2
        it2p[2],  # it2p3
        # None,  # iStopFeed
        # None,  # position
        # "0",  # pIntObjs:SIZEROW
    ]
    sta_cubic["Values"].append(value)
    return value


def create_study_case(fid_counter: Iterator[str]) -> DGSData:
    """Create the "IntCase" object for the study case."""
    return {
        "Attributes": [
            "FID",  # Unique identifier for DGS file
            "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
            "loc_name",  # Name
            "cpowexp",
            "campexp",
            "cpexpshc",
        ],
        "Values": [
            [
                next(fid_counter),  # FID
                "C",  # OP
                "RLF Study Case",  # loc_name
                "M",  # cpowexp
                "k",  # campexp
                "M",  # cpexpshc
            ],
        ],
    }


def create_graphic_net(fid_counter: Iterator[str]) -> DGSData:
    """Create the "IntGrfnet" object for the graphic network."""
    return {
        "Attributes": [
            "FID",  # Unique identifier for DGS file
            "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
            "loc_name",  # Name
            "fold_id",  # In Folder
            "sBordSym:SIZEROW",
            "snap_on",  # Snap to grid: 0=off, 1=on
            "ortho_on",  # Line routing: 0=non-orthogonal, 1=orthogonal, 2=semi-orthogonal
            "sSubstTyp:SIZEROW",
            "sSymbol:SIZEROW",
        ],
        "Values": [
            [
                next(fid_counter),  # FID
                "C",  # OP
                "RLF Graphic",  # loc_name
                None,  # fold_id
                "0",  # sBordSym:SIZEROW
                1,  # snap_on
                1,  # ortho_on
                "0",  # sSubstTyp:SIZEROW
                "0",  # sSymbol:SIZEROW
            ],
        ],
    }


def create_grid(fid_counter: Iterator[str], grf_net_fid: str) -> DGSData:
    """Create the "ElmNet" object for the grid.

    Args:
        fid_counter:
            The unique identifier counter.

        grf_net_fid:
            The FID of the graphic network.

    Returns:
        The DGS data for the "ElmNet" object.
    """
    return {
        "Attributes": [
            "FID",  # Unique identifier for DGS file
            "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
            "loc_name",  # Name
            "fold_id",  # In Folder
            "frnom",  # Nominal Frequency in Hz
            "pDiagram",  # Diagrams/Graphic
        ],
        "Values": [
            [
                next(fid_counter),  # FID
                "C",  # OP
                "RLF Grid",  # loc_name
                None,  # fold_id
                50,  # frnom
                grf_net_fid,  # pDiagram
            ],
        ],
    }
