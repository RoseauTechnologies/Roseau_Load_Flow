"""
This module is not for public use.

Use the `ElectricalNetwork.from_dgs` method to read a network from a dgs file.
"""
import json
import logging

import numpy as np
import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.typing import Id, StrPath
from roseau.load_flow.units import Q_

logger = logging.getLogger(__name__)


def network_from_dgs(  # noqa: C901
    filename: StrPath,
) -> tuple[
    dict[Id, Bus],
    dict[Id, AbstractBranch],
    dict[Id, AbstractLoad],
    dict[Id, VoltageSource],
    dict[Id, Ground],
    dict[Id, PotentialRef],
]:
    """Create the electrical elements from a JSON file in DGS format.

    Args:
        filename: name of the JSON file

    Returns:
        The elements of the network: buses, branches, loads, sources, grounds and potential refs.
    """
    # Read files
    (
        elm_xnet,
        elm_term,
        sta_cubic,
        elm_tr,
        typ_tr,
        elm_coup,
        elm_lne,
        typ_lne,
        elm_lod_lv,
        elm_lod_mv,
        elm_gen_stat,
        elm_pv_sys,
    ) = _read_dgs_json_file(filename=filename)

    # Ground and potential reference
    ground = Ground("ground")
    p_ref = PotentialRef("pref", element=ground)

    grounds = {ground.id: ground}
    potential_refs = {p_ref.id: p_ref}

    # Buses
    buses: dict[Id, Bus] = {}
    for bus_id in elm_term.index:
        ph_tech = elm_term.at[bus_id, "phtech"]
        if ph_tech == 0:
            phases = "abc"
        elif ph_tech == 1:
            phases = "abcn"
        else:
            msg = f"The Ph tech {ph_tech!r} for bus {bus_id!r} cannot be handled."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY)
        buses[bus_id] = Bus(id=bus_id, phases=phases)

    # Sources
    sources: dict[Id, VoltageSource] = {}
    for source_id in elm_xnet.index:
        id_sta_cubic_source = elm_xnet.at[source_id, "bus1"]  # id of the cubicle connecting the source and its bus
        bus_id = sta_cubic.at[id_sta_cubic_source, "cterm"]  # id of the bus to which the source is connected
        un = elm_term.at[bus_id, "uknom"] / np.sqrt(3) * 1e3  # phase-to-neutral voltage (V)
        tap = elm_xnet.at[source_id, "usetp"]  # tap voltage (p.u.)
        voltages = [un * tap, un * np.exp(-np.pi * 2 / 3 * 1j) * tap, un * np.exp(np.pi * 2 / 3 * 1j) * tap]
        source_bus = buses[bus_id]

        sources[source_id] = VoltageSource(id=source_id, phases="abcn", bus=source_bus, voltages=voltages)
        source_bus._connect(ground)

    # LV loads
    loads: dict[Id, AbstractLoad] = {}
    if elm_lod_lv is not None:
        _generate_loads(elm_lod_lv, loads, buses, sta_cubic, 1e3, production=False)

    # LV Production loads
    if elm_pv_sys is not None:
        _generate_loads(elm_pv_sys, loads, buses, sta_cubic, 1e3, production=True)
    if elm_gen_stat is not None:
        _generate_loads(elm_gen_stat, loads, buses, sta_cubic, 1e3, production=True)

    # MV loads
    if elm_lod_mv is not None:
        _generate_loads(elm_lod_mv, loads, buses, sta_cubic, 1e6, production=False)

    # Lines
    branches: dict[Id, AbstractBranch] = {}
    if elm_lne is not None:
        lines_params_dict: dict[Id, LineParameters] = {}
        for type_id in typ_lne.index:
            # TODO: use the detailed phase information instead of n
            n = typ_lne.at[type_id, "nlnph"] + typ_lne.at[type_id, "nneutral"]
            if n not in (3, 4):
                msg = f"The number of phases ({n}) of line type {type_id!r} cannot be handled, it should be 3 or 4."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)

            lp = LineParameters.from_sym(
                type_id,
                z0=complex(typ_lne.at[type_id, "rline0"], typ_lne.at[type_id, "xline0"]),
                z1=complex(typ_lne.at[type_id, "rline"], typ_lne.at[type_id, "xline"]),
                y0=Q_(complex(typ_lne.at[type_id, "gline0"], typ_lne.at[type_id, "bline0"]), "uS/km"),
                y1=Q_(complex(typ_lne.at[type_id, "gline"], typ_lne.at[type_id, "bline"]), "uS/km"),
                zn=complex(typ_lne.at[type_id, "rnline"], typ_lne.at[type_id, "xnline"]),
                xpn=typ_lne.at[type_id, "xpnline"],
                bn=Q_(typ_lne.at[type_id, "bnline"], "uS/km"),
                bpn=Q_(typ_lne.at[type_id, "bpnline"], "uS/km"),
            )

            actual_shape = lp.z_line.shape[0]
            if actual_shape > n:  # 4x4 matrix while a 3x3 matrix was expected
                # Extract the 3x3 underlying matrix
                lp = LineParameters(
                    id=lp.id,
                    z_line=lp.z_line[:actual_shape, :actual_shape],
                    y_shunt=lp.y_shunt[:actual_shape, :actual_shape] if lp.with_shunt else None,
                )
            elif actual_shape == n:
                # Everything ok
                pass
            else:
                # Something unexpected happened
                msg = (
                    f"A {n}x{n} impedance matrix was expected for the line type {type_id!r} but a "
                    f"{actual_shape}x{actual_shape} matrix was generated."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)
            lines_params_dict[type_id] = lp

        for line_id in elm_lne.index:
            type_id = elm_lne.at[line_id, "typ_id"]  # id of the line type
            lp = lines_params_dict[type_id]
            branches[line_id] = Line(
                id=line_id,
                bus1=buses[sta_cubic.at[elm_lne.at[line_id, "bus1"], "cterm"]],
                bus2=buses[sta_cubic.at[elm_lne.at[line_id, "bus2"], "cterm"]],
                length=elm_lne.at[line_id, "dline"],
                parameters=lp,
                ground=ground if lp.with_shunt else None,
            )

    # Transformers
    if elm_tr is not None:
        # Transformers type
        transformers_params_dict: dict[Id, TransformerParameters] = {}
        transformers_tap: dict[Id, int] = {}
        for idx in typ_tr.index:
            # Extract data
            name = typ_tr.at[idx, "loc_name"]
            sn = Q_(typ_tr.at[idx, "strn"], "MVA")  # The nominal voltages of the transformer (MVA)
            uhv = Q_(typ_tr.at[idx, "utrn_h"], "kV")  # Phase-to-phase nominal voltages of the high voltages side (kV)
            ulv = Q_(typ_tr.at[idx, "utrn_l"], "kV")  # Phase-to-phase nominal voltages of the low voltages side (kV)
            i0 = Q_(typ_tr.at[idx, "curmg"] / 3, "percent")  # Current during off-load test (%)
            p0 = Q_(typ_tr.at[idx, "pfe"] / 3, "kW")  # Losses during off-load test (kW)
            psc = Q_(typ_tr.at[idx, "pcutr"], "kW")  # Losses during short-circuit test (kW)
            vsc = Q_(typ_tr.at[idx, "uktr"], "percent")  # Voltages on LV side during short-circuit test (%)
            # Windings of the transformer
            windings = f"{typ_tr.at[idx, 'tr2cn_h']}{typ_tr.at[idx, 'tr2cn_l']}{typ_tr.at[idx, 'nt2ag']}"

            # Generate transformer parameters
            transformers_params_dict[idx] = TransformerParameters(
                id=name, type=windings, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc
            )
            transformers_tap[idx] = typ_tr.at[idx, "dutap"]

        # Create transformers
        for idx in elm_tr.index:
            type_id = elm_tr.at[idx, "typ_id"]  # id of the line type
            tap = 1.0 + elm_tr.at[idx, "nntap"] * transformers_tap[type_id] / 100
            branches[idx] = Transformer(
                id=idx,
                bus1=buses[sta_cubic.at[elm_tr.at[idx, "bushv"], "cterm"]],
                bus2=buses[sta_cubic.at[elm_tr.at[idx, "buslv"], "cterm"]],
                parameters=transformers_params_dict[type_id],
                tap=tap,
            )
            ground.connect(bus=buses[sta_cubic.at[elm_tr.at[idx, "buslv"], "cterm"]])

    # Create switches
    if elm_coup is not None:
        for switch_id in elm_coup.index:
            # TODO: use the detailed phase information instead of n
            n = elm_coup.at[switch_id, "nphase"] + elm_coup.at[switch_id, "nneutral"]
            branches[switch_id] = Switch(
                id=switch_id,
                phases="abc" if n == 3 else "abcn",
                bus1=buses[sta_cubic.at[elm_coup.at[switch_id, "bus1"], "cterm"]],
                bus2=buses[sta_cubic.at[elm_coup.at[switch_id, "bus2"], "cterm"]],
            )

    return buses, branches, loads, sources, grounds, potential_refs


def _read_dgs_json_file(filename: StrPath):
    """Read a JSON file in DGS format.

    Args:
        filename: name of the JSON file

    Returns:
        elm_xnet: dataframe of external sources
        elm_term: dataframe of terminals (i.e. buses)
        sta_cubic: dataframe of cubicles
        elm_tr: dataframe of transformers
        typ_tr: dataframe of types of transformer
        elm_coup: dataframe of switches
        elm_lne: dataframe of electrical line
        typ_lne: dataframe of types of line
        elm_lod_lv: dataframe of LV loads
        elm_lod_mv: dataframe of MV loads
        elm_gen_stat: dataframe of generators
    """
    # Create dataframe from JSON file
    with open(filename, encoding="ISO-8859-10") as f:
        data = json.load(f)

    # External sources
    elm_xnet = pd.DataFrame(columns=data["ElmXnet"]["Attributes"], data=data["ElmXnet"]["Values"]).set_index("FID")

    # Terminals (buses)
    elm_term = pd.DataFrame(columns=data["ElmTerm"]["Attributes"], data=data["ElmTerm"]["Values"]).set_index("FID")

    # Cubicles
    sta_cubic = pd.DataFrame(columns=data["StaCubic"]["Attributes"], data=data["StaCubic"]["Values"]).set_index("FID")

    # Transformers
    if "ElmTr2" in data:
        elm_tr = pd.DataFrame(columns=data["ElmTr2"]["Attributes"], data=data["ElmTr2"]["Values"]).set_index("FID")
    else:
        elm_tr = None

    # Transformer types
    if "TypTr2" in data:
        typ_tr = pd.DataFrame(columns=data["TypTr2"]["Attributes"], data=data["TypTr2"]["Values"]).set_index("FID")
    else:
        typ_tr = None

    # Switch
    if "ElmCoup" in data:
        elm_coup = pd.DataFrame(columns=data["ElmCoup"]["Attributes"], data=data["ElmCoup"]["Values"]).set_index("FID")
    else:
        elm_coup = None

    # Lines
    if "ElmLne" in data:
        elm_lne = pd.DataFrame(columns=data["ElmLne"]["Attributes"], data=data["ElmLne"]["Values"]).set_index("FID")
    else:
        elm_lne = None

    # Line types
    if "TypLne" in data:
        typ_lne = pd.DataFrame(columns=data["TypLne"]["Attributes"], data=data["TypLne"]["Values"]).set_index("FID")
    else:
        typ_lne = None

    # LV loads
    if "ElmLodLV" in data:
        elm_lod_lv = pd.DataFrame(columns=data["ElmLodLV"]["Attributes"], data=data["ElmLodLV"]["Values"]).set_index(
            "FID"
        )
    else:
        elm_lod_lv = None

    # MV loads
    if "ElmLodmv" in data:
        elm_lod_mv = pd.DataFrame(columns=data["ElmLodmv"]["Attributes"], data=data["ElmLodmv"]["Values"]).set_index(
            "FID"
        )
    else:
        elm_lod_mv = None

    # Generators
    if "ElmGenStat" in data:
        elm_gen_stat = pd.DataFrame(
            columns=data["ElmGenStat"]["Attributes"], data=data["ElmGenStat"]["Values"]
        ).set_index("FID")
    else:
        elm_gen_stat = None

    # LV generators
    # Generators
    if "ElmPvsys" in data:
        elm_pv_sys = pd.DataFrame(columns=data["ElmPvsys"]["Attributes"], data=data["ElmPvsys"]["Values"]).set_index(
            "FID"
        )
    else:
        elm_pv_sys = None

    return (
        elm_xnet,
        elm_term,
        sta_cubic,
        elm_tr,
        typ_tr,
        elm_coup,
        elm_lne,
        typ_lne,
        elm_lod_lv,
        elm_lod_mv,
        elm_gen_stat,
        elm_pv_sys,
    )


def _generate_loads(
    elm_lod: pd.DataFrame,
    loads: dict[Id, AbstractLoad],
    buses: dict[Id, Bus],
    sta_cubic: pd.DataFrame,
    factor: float,
    production: bool,
) -> None:
    """Generate the loads of a given dataframe.

    Args:
        elm_lod:
            The dataframe of loads.

        loads:
            The dictionary the loads will be added to.

        buses:
            The dataframe of buses.

        sta_cubic:
            The dataframe of cubicles.

        factor:
            The factor to multiply the load power (ex: 1e3 for kVA -> VA)

        production:
             True for production loads, False otherwise.
    """
    for load_id in elm_lod.index:
        sta_cubic_id = elm_lod.at[load_id, "bus1"]  # id of the cubicle connecting the load and its bus
        bus_id = sta_cubic.at[sta_cubic_id, "cterm"]  # id of the bus to which the load is connected

        if production:
            s_phase = _compute_production_load_power(elm_lod, load_id, "") * factor
            sa = sb = sc = 0
        else:
            s_phase = _compute_load_power(elm_lod, load_id, "") * factor
            sa = _compute_load_power(elm_lod, load_id, "r") * factor
            sb = _compute_load_power(elm_lod, load_id, "s") * factor
            sc = _compute_load_power(elm_lod, load_id, "t") * factor

        # Balanced or Unbalanced
        s = [s_phase / 3, s_phase / 3, s_phase / 3] if sa == 0 and sb == 0 and sc == 0 else [sa, sb, sc]
        loads[load_id] = PowerLoad(id=load_id, phases="abcn", bus=buses[bus_id], powers=s)


def _compute_load_power(elm_lod: pd.DataFrame, load_id: str, suffix: str) -> complex:
    """Compute a load power in PWF format.

    Args:
        elm_lod:
            The dataframe of loads.

        load_id:
            The load id.

        suffix:
            The phase of the load (empty for balanced loads, or r, s, t for phases a, b, c)

    Returns:
        The apparent power.
    """
    p = elm_lod.at[load_id, "plini" + suffix]
    q = np.sqrt(elm_lod.at[load_id, "slini" + suffix] ** 2 - elm_lod.at[load_id, "plini" + suffix] ** 2)
    q *= np.sign(p) * (-1 if elm_lod.at[load_id, "pf_recap" + suffix] else 1)
    return p + 1j * q


def _compute_production_load_power(elm_lod: pd.DataFrame, load_id: str, suffix: str) -> complex:
    """Compute a production load power in PWF format.

    Args:
        elm_lod:
            The dataframe of loads.

        load_id:
            The load id.

        suffix:
            The phase of the load (empty for balanced loads, or r, s, t for phases a, b, c)

    Returns:
        The apparent power.
    """
    p = elm_lod.at[load_id, "pgini" + suffix]
    q = elm_lod.at[load_id, "qgini" + suffix]
    q *= np.sign(p) * (-1 if elm_lod.at[load_id, "pf_recap" + suffix] else 1)
    return -(p + 1j * q)
