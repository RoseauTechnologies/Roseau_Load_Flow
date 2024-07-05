import logging
from collections.abc import Callable
from typing import Literal

import numpy as np
import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.constants import (
    GEN_STAT_PHASES,
    GENERAL_LOAD_INPUT_MODE,
    GENERAL_LOAD_PHASES,
    LOAD_I_SYM_FIELD_NAMES,
    LV_LOAD_PHASES,
    MV_LOAD_PHASES,
    PV_SYS_PHASES,
    PwFLoadType,
)
from roseau.load_flow.models import AbstractLoad, Bus, PowerLoad
from roseau.load_flow.typing import Id

logger = logging.getLogger(__name__)


def compute_mv_load_power(elm_lod: pd.DataFrame, load_id: str, suffix: str) -> complex:
    """Compute the complex power of an MV Load.

    An MV load has load power (slini) and generation power (sgini). The powers are defined using
    `p*ini`, `s*ini` and `pf*_recap`.

    Args:
        elm_lod:
            The "ElmLodmv" dataframe.

        load_id:
            The ID of the load in the dataframe.

        suffix:
            The phase suffix. An empty string for balanced loads or one of "rst" for phases "abc" respectively.

    Returns:
        The total complex power of the MV load (load power - generation power) at the requested phase.
    """
    # Load power
    pl = elm_lod.at[load_id, "plini" + suffix]
    sl = elm_lod.at[load_id, "slini" + suffix]
    pf_recap = elm_lod.at[load_id, "pf_recap" + suffix]
    ql = np.sqrt(sl**2 - pl**2)
    ql *= np.sign(pl) * (-1 if pf_recap else 1)
    scale_l = elm_lod.at[load_id, "scale0"]
    power_l = (pl + 1j * ql) * scale_l
    # Generation power
    pg = elm_lod.at[load_id, "pgini" + suffix]
    sg = elm_lod.at[load_id, "sgini" + suffix]
    pfg_recap = elm_lod.at[load_id, "pfg_recap" + suffix]
    qg = np.sqrt(sg**2 - pg**2)
    qg *= np.sign(pg) * (-1 if pfg_recap else 1)
    scale_g = elm_lod.at[load_id, "gscale"]
    power_g = (pg + 1j * qg) * scale_g
    return power_l - power_g


def compute_lv_load_power(elm_lod: pd.DataFrame, load_id: str, suffix: str) -> complex:
    """Compute the complex power of an LV Load.

    An LV load has load power (slini) only. The power is defined using `plini`, `slini` and `pf_recap`.

    Args:
        elm_lod:
            The "ElmLodLV" dataframe.

        load_id:
            The ID of the load in the dataframe.

        suffix:
            The phase suffix. An empty string for balanced loads or one of "rst" for phases "abc" respectively.

    Returns:
        The complex power of the LV load at the requested phase.
    """
    p = elm_lod.at[load_id, "plini" + suffix]
    s = elm_lod.at[load_id, "slini" + suffix]
    pf_recap = elm_lod.at[load_id, "pf_recap" + suffix]
    scale = elm_lod.at[load_id, "scale0"]
    q = np.sqrt(s**2 - p**2)
    q *= np.sign(p) * (-1 if pf_recap else 1)
    return (p + 1j * q) * scale


def compute_general_load_power(elm_lod: pd.DataFrame, load_id: str, suffix: str) -> complex:
    """Compute the complex power of a General Load.

    A general load has load power (slini) only. The power is defined using one of (`plini`, `qlini`),
    (`plini`, `slini`, `pf_recap`), or (`qlini`, `slini`, `pf_recap`)

    Args:
        elm_lod:
            The "ElmLod" dataframe.

        load_id:
            The ID of the load in the dataframe.

        suffix:
            The phase suffix. An empty string for balanced loads or one of "rst" for phases "abc" respectively.

    Returns:
        The complex power of the general load at the requested phase.
    """
    input_mode = elm_lod.at[load_id, "mode_inp"]
    values = [elm_lod.at[load_id, field + suffix] for field in GENERAL_LOAD_INPUT_MODE[input_mode]]
    if input_mode == "DEF":  # noqa: SIM114
        p, q = values
    elif input_mode == "PQ":
        p, q = values
    elif input_mode == "PC":
        p, pf, pf_recap = values
        q = 0 if pf == 0 else (p * np.tan(np.arccos(pf)))
        q *= -1 if pf_recap else 1
    elif input_mode == "IC":
        # i, pf, pf_recap = values
        raise NotImplementedError(f"Input mode {input_mode!r} is not implemented yet.")
    elif input_mode == "SC":
        s, pf, pf_recap = values
        p = s * pf
        q = np.sqrt(s**2 - p**2)
        q *= np.sign(p) * (-1 if pf_recap else 1)
    elif input_mode == "QC":
        q, pf, pf_recap = values
        p = 0 if (pf == 1 or pf == -1) else (q / np.tan(np.arccos(pf)))
        p *= -1 if pf_recap else 1
    elif input_mode == "IP":
        # i, p = values
        raise NotImplementedError(f"Input mode {input_mode!r} is not implemented yet.")
    elif input_mode == "SP":
        s, p, pf_recap = values
        q = np.sqrt(s**2 - p**2)
        q *= -1 if pf_recap else 1
    elif input_mode == "SQ":
        s, q, p_direc = values
        p = (-1 if p_direc else 1) * np.sqrt(s**2 - q**2)
    else:
        raise AssertionError  # should never reach here
    scale = elm_lod.at[load_id, "scale0"]
    return (p + 1j * q) * scale


def compute_pv_sys_power(elm_lod: pd.DataFrame, load_id: str, suffix: str) -> complex:
    """Compute the complex power of a PV Sys.

    Args:
        elm_lod:
            The "ElmPvsys" dataframe.

        load_id:
            The ID of the load in the dataframe.

        suffix:
            The phase suffix. An empty string for balanced loads or one of "rst" for phases "abc" respectively.

    Returns:
        The complex power of the generator.
    """
    p = elm_lod.at[load_id, "pgini" + suffix]
    q = elm_lod.at[load_id, "qgini" + suffix]
    scale = elm_lod.at[load_id, "scale0"]
    # I (Ali) commented the following two lines as "qgini" already includes the sign of q
    # pf_recap = elm_lod.at[load_id, "pf_recap" + suffix]
    # q *= np.sign(p) * (-1 if pf_recap else 1)
    return -(p + 1j * q) * scale


def compute_gen_stat_power(elm_lod: pd.DataFrame, load_id: str, suffix: str) -> complex:
    """Compute the complex power of a Static Generator.

    Args:
        elm_lod:
            The "ElmGenStat" dataframe.

        load_id:
            The ID of the load in the dataframe.

        suffix:
            The phase suffix. An empty string for balanced loads or one of "rst" for phases "abc" respectively.

    Returns:
        The complex power of the generator.
    """
    p = elm_lod.at[load_id, "pgini" + suffix]
    q = elm_lod.at[load_id, "qgini" + suffix]
    scale = elm_lod.at[load_id, "scale0"]
    # I (Ali) commented the following two lines as "qgini" already includes the sign of q
    # pf_recap = elm_lod.at[load_id, "pf_recap" + suffix]
    # q *= np.sign(p) * (-1 if pf_recap else 1)
    return -(p + 1j * q) * scale


_LOAD_POWER_FUNCTIONS: dict[PwFLoadType, Callable[[pd.DataFrame, str, str], complex]] = {
    "MV": compute_mv_load_power,
    "LV": compute_lv_load_power,
    "General": compute_general_load_power,
    "PV": compute_pv_sys_power,
    "GenStat": compute_gen_stat_power,
}


def compute_3phase_load_powers(
    elm_lod: pd.DataFrame, load_id: str, i_sym: Literal[0, 1], factor: float, load_type: PwFLoadType
) -> tuple[complex, complex, complex]:
    """Compute the three-phase complex power of a load.

    The load can be balanced or unbalanced. The load can represent an "MV Load", an "LV Load", or a
    "General Load".

    Args:
        elm_lod:
            The dataframe containing load data.

        load_id:
            The ID of the load in the dataframe.

        i_sym:
            0 for balanced load, 1 for unbalanced load.

        factor:
            A factor to convert the power values from load type dependent PwF units to SI units.

        load_type:
            The type of the load: "MV", "LV", or "General".

    Returns:
        A 3-tuple of complex powers for each phase.
    """
    power_comp = _LOAD_POWER_FUNCTIONS[load_type]
    if i_sym == 0:  # Balanced
        s_balanced = power_comp(elm_lod, load_id, "")
        sa = s_balanced / 3
        sb = s_balanced / 3
        sc = s_balanced / 3
    elif i_sym == 1:  # Unbalanced
        sa = power_comp(elm_lod, load_id, "r")
        sb = power_comp(elm_lod, load_id, "s")
        sc = power_comp(elm_lod, load_id, "t")
    else:
        raise NotImplementedError(i_sym)  # should never reach here
    return sa * factor, sb * factor, sc * factor


def generate_loads(
    elm_lod: pd.DataFrame,
    loads: dict[Id, AbstractLoad],
    buses: dict[Id, Bus],
    sta_cubic: pd.DataFrame,
    factor: float,
    load_type: PwFLoadType,
) -> None:
    """Generate the loads of a given load type.

    Args:
        elm_lod:
            The dataframe containing the load data.

        loads:
            The dictionary to store the loads into.

        buses:
            The dictionary of the all buses.

        sta_cubic:
            The "StaCubic" dataframe of cubicles.

        factor:
            The factor to multiply the load power (ex: 1e3 for kVA -> VA)

        load_type:
            The type of the PwF Load: "MV" (ElmLodmv), "LV" (ElmLodLV), "General" (ElmLod),
            "PV" (ElmPVSys), "GenStat" (ElmGenStat).
    """
    i_sym_field = LOAD_I_SYM_FIELD_NAMES[load_type]
    has_i_sym = i_sym_field is not None and i_sym_field in elm_lod.columns
    for load_id in elm_lod.index:
        sta_cubic_id = elm_lod.at[load_id, "bus1"]  # id of the cubicle connecting the load and its bus
        bus_id = sta_cubic.at[sta_cubic_id, "cterm"]  # id of the bus to which the load is connected
        bus = buses[bus_id]
        phtech = elm_lod.at[load_id, "phtech"]  # could be str (MV/General), int (LV), or None (missing)
        i_sym = elm_lod.at[load_id, i_sym_field] if has_i_sym else None  # 0: Balanced, 1: Unbalanced

        if load_type == "MV":
            # Seems like MV Loads in PF just inherit the phase of the bus sometimes
            phases = MV_LOAD_PHASES.get(phtech) if pd.notna(phtech) else bus.phases
        elif load_type == "LV":
            phases = LV_LOAD_PHASES.get(phtech)
        elif load_type == "General":
            # Seems like General Loads in PF just inherit the phase of the bus sometimes
            phases = GENERAL_LOAD_PHASES.get(phtech) if pd.notna(phtech) else bus.phases
        elif load_type == "PV":
            phases = PV_SYS_PHASES.get(phtech)
            i_sym = 0  # Always balanced
            # TODO: Add control information (FlexibleParameters)
        elif load_type == "GenStat":
            phases = GEN_STAT_PHASES.get(phtech)
            i_sym = 0  # Always balanced
            # TODO: Add control information (FlexibleParameters)
        else:
            raise AssertionError(load_type)  # should never reach here

        if phases is None:
            msg = f"Ph tech {phtech!r} for {load_type} load {load_id!r} is not supported."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY)

        if i_sym == 0 or i_sym == 1:
            sa, sb, sc = compute_3phase_load_powers(
                elm_lod=elm_lod, load_id=load_id, i_sym=i_sym, factor=factor, load_type=load_type
            )
        else:
            # We don't know, try unbalanced first
            sa, sb, sc = compute_3phase_load_powers(
                elm_lod=elm_lod, load_id=load_id, i_sym=1, factor=factor, load_type=load_type
            )
            if sa == 0 and sb == 0 and sc == 0:
                # try balanced next
                sa, sb, sc = compute_3phase_load_powers(
                    elm_lod=elm_lod, load_id=load_id, i_sym=0, factor=factor, load_type=load_type
                )

        # Balanced or Unbalanced
        loads[load_id] = PowerLoad(id=load_id, phases=phases, bus=buses[bus_id], powers=[sa, sb, sc])
