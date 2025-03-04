import logging
import warnings
from collections.abc import Iterable, Iterator

import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import (
    GEN_STAT_PHASES,
    GENERAL_LOAD_PHASES,
    LOAD_I_SYM_FIELD_NAMES,
    LV_LOAD_PHASES,
    MV_LOAD_PHASES,
    PV_SYS_PHASES,
    PwFLoadType,
)
from roseau.load_flow.io.dgs.loads import LOAD_POWER_FUNCTIONS
from roseau.load_flow.io.dgs.utils import DGSData, clean_id
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_single.io.dgs.pwf import STA_CUBIC_FID_INDEX, STA_CUBIC_OBJ_ID_INDEX
from roseau.load_flow_single.models import AbstractLoad, Bus, PowerLoad

logger = logging.getLogger(__name__)


#
# DGS -> RLF
#
def elm_lod_all_to_loads(
    elm_lod: pd.DataFrame,
    loads: dict[Id, AbstractLoad],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    factor: float,
    load_type: PwFLoadType,
) -> None:
    """Create RLF loads from PwF loads.

    Args:
        elm_lod:
            The dataframe containing the load data.

        loads:
            The dictionary to store the loads into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.

        factor:
            The factor to multiply the load power (ex: 1e3 for kVA -> VA)

        load_type:
            The type of the PwF Load: "MV" (ElmLodmv), "LV" (ElmLodLV), "General" (ElmLod),
            "PV" (ElmPVSys), "GenStat" (ElmGenStat).
    """
    i_sym_field = LOAD_I_SYM_FIELD_NAMES[load_type]
    has_i_sym = i_sym_field is not None and i_sym_field in elm_lod.columns
    for idx in elm_lod.index:
        load_id = clean_id(idx)
        sta_cubic_id = elm_lod.at[idx, "bus1"]  # id of the cubicle connecting the load and its bus
        bus_id = sta_cubic.at[sta_cubic_id, "cterm"]  # id of the bus to which the load is connected
        bus = buses[bus_id]
        phtech = elm_lod.at[idx, "phtech"]  # could be str (MV/General), int (LV), or None (missing)
        i_sym = elm_lod.at[idx, i_sym_field] if has_i_sym else None  # 0: Balanced, 1: Unbalanced
        if i_sym == 1:
            msg = (
                f"Unbalanced loads are not supported, {load_type} load {load_id!r} is unbalanced. "
                f"It will be processed as balanced."
            )
            warnings.warn(msg, stacklevel=find_stack_level())

        if load_type == "MV":
            # Seems like MV Loads in PF just inherit the phase of the bus sometimes
            phases = MV_LOAD_PHASES.get(phtech)
        elif load_type == "LV":
            phases = LV_LOAD_PHASES.get(phtech)
        elif load_type == "General":
            # Seems like General Loads in PF just inherit the phase of the bus sometimes
            phases = GENERAL_LOAD_PHASES.get(phtech)
        elif load_type == "PV":
            phases = PV_SYS_PHASES.get(phtech)
            # TODO: Add control information (FlexibleParameters)
        elif load_type == "GenStat":
            phases = GEN_STAT_PHASES.get(phtech)
            # TODO: Add control information (FlexibleParameters)
        else:
            raise AssertionError(load_type)  # should never reach here

        if phases not in {"abc", "abcn", None}:
            msg = f"Only three-phase balanced loads are supported, {load_type} load {load_id!r} has Ph tech {phtech!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY)

        compute_power = LOAD_POWER_FUNCTIONS[load_type]
        # We only want the balanced power
        s = compute_power(elm_lod, load_id, suffix="") * factor

        loads[load_id] = PowerLoad(id=load_id, bus=bus, power=s)


#
# RLF -> DGS
#
def loads_to_elm_lod(loads: Iterable[AbstractLoad], fid_counter: Iterator[str], sta_cubic: dict[Id, list]) -> DGSData:
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "typ_id",
        "bus1",  # Terminal in StaCubic
        "phtech",  # Phase Technology
        "mode_inp",  # Operation Point: Input Mode
        "i_sym",
        # "u0",
        "scale0",
        "plini",  # Operation Point: Active Power in MW
        "qlini",  # Operation Point: Reactive Power in Mvar
        "slini",  # Operation Point: Apparent Power in MVA
        # "ilini",
        "coslini",
        "pf_recap",  # Operation Point: Power Factor:ind.:cap.
        "p_direc",  # Operation Point: Power Direction:P>=0:P<0
    ]
    values: list[list[str | float | None]] = []
    for load in loads:
        assert isinstance(load, PowerLoad), (
            f"Only PowerLoads are supported in DGS conversion, got {type(load).__name__}"
        )
        fid = next(fid_counter)
        cubic = sta_cubic[load.id]
        cubic[STA_CUBIC_OBJ_ID_INDEX] = fid
        power = load._power / 1e6  # MVA
        slini = abs(power)
        plini = power.real
        qlini = power.imag
        coslini = plini / slini
        pf_recap = int(power.real * power.imag < 0)
        p_direc = int(power.real < 0)
        values.append(
            [
                fid,  # FID
                "C",  # OP
                load.id,  # loc_name
                None,  # fold_id
                None,  # typ_id
                cubic[STA_CUBIC_FID_INDEX],  # bus1
                "3PH-'D'",  # phtech
                "DEF",  # mode_inp
                0,  # i_sym
                # 0,  # u0
                1,  # scale0
                plini,  # plini
                qlini,  # qlini
                slini,  # slini
                # None,  # ilini
                coslini,  # coslini
                pf_recap,  # pf_recap
                p_direc,  # p_direc
            ]
        )
    return {"Attributes": attributes, "Values": values}
