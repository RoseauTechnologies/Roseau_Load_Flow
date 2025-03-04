import cmath
import logging
from collections.abc import Iterable, Iterator

import pandas as pd

from roseau.load_flow.io.dgs.utils import DGSData, clean_id
from roseau.load_flow.typing import Id
from roseau.load_flow_single.io.dgs.pwf import STA_CUBIC_FID_INDEX, STA_CUBIC_OBJ_ID_INDEX
from roseau.load_flow_single.models import Bus, VoltageSource

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
    has_phi_ini = "phiini" in elm_xnet.columns
    for idx in elm_xnet.index:
        src_id = clean_id(idx)
        bus = buses[sta_cubic.at[elm_xnet.at[idx, "bus1"], "cterm"]]
        setpoint = elm_xnet.at[idx, "usetp"]  # voltage setpoint (p.u.)
        un = bus.nominal_voltage
        phi = (elm_xnet.at[idx, "phiini"] * cmath.pi / 180) if has_phi_ini else 0.0  # angle (deg)
        assert un is not None, f"Bus {bus.id!r} of the source {src_id!r} has no nominal voltage"
        voltage = un.m * cmath.rect(setpoint, phi)  # phase-to-phase voltage (V)
        sources[src_id] = VoltageSource(id=src_id, bus=bus, voltage=voltage)


#
# RLF -> DGS
#
def sources_to_elm_xnet(
    sources: Iterable[VoltageSource], fid_counter: Iterator[str], sta_cubic: dict[Id, list], fold_id: str
) -> DGSData:
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "bus1",  # Terminal in StaCubic
        # "bus1n",  # Neutral Conductor: Neutral in StaCubic
        "cgnd",  # Internal Grounding Impedance: Star Point:Connected:Not connected
        "iintgnd",  # Neutral Conductor: N-Connection:None:At terminal (ABC-N):Separate terminal
        "mode_inp",  # Operation Point: Input Mode
        "pgini",  # Operation Point: Active Power in MW
        "qgini",  # Operation Point: Reactive Power in Mvar
        "bustp",  # Bus Type:PQ:PV:SL
        "usetp",  # Operation Point: Voltage Setpoint in p.u.
        "phiini",  # Operation Point: Angle in deg
    ]
    values: list[list[str | float | None]] = []
    for source in sources:
        fid = next(fid_counter)
        cubic = sta_cubic[source.id]
        cubic[STA_CUBIC_OBJ_ID_INDEX] = fid
        u, phi = cmath.polar(source.voltage.m)
        usetp = u / source.bus.nominal_voltage.m if source.bus.nominal_voltage is not None else 1.0
        phiini = phi * 180 / cmath.pi
        # bus1n is not specified because we don't connect the source's neutral to another bus
        values.append(
            [
                fid,  # FID
                "C",  # OP
                source.id,  # loc_name
                fold_id,  # fold_id
                cubic[STA_CUBIC_FID_INDEX],  # bus1
                # None,  # bus1n
                0,  # cgnd
                0,  # iintgnd
                "DEF",  # mode_inp
                0,  # pgini
                0,  # qgini
                "SL",  # bustp
                usetp,  # usetp
                phiini,  # phiini
            ]
        )
    return {"Attributes": attributes, "Values": values}
