import json
import logging

import numpy as np
import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    Element,
    Ground,
    Line,
    LineCharacteristics,
    PotentialRef,
    PowerLoad,
    Switch,
    Transformer,
    TransformerCharacteristics,
    VoltageSource,
)
from roseau.load_flow.typing import StrPath
from roseau.load_flow.utils import LineModel, Q_

logger = logging.getLogger(__name__)


def network_from_dgs(  # noqa: C901
    filename: StrPath,
) -> tuple[dict[str, Bus], dict[str, AbstractBranch], dict[str, AbstractLoad], dict[str, VoltageSource], list[Element]]:
    """Create the electrical elements from a JSON file in DGS format to create an electrical network.

    Args:
        filename: name of the JSON file

    Returns:
        The buses, branches, loads, sources and special elements to construct the electrical network.
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

    # Ground and special elements
    ground = Ground("ground")
    p_ref = PotentialRef("pref", element=ground)

    # Buses
    buses: dict[str, Bus] = {}
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
    sources: dict[str, VoltageSource] = {}
    for source_id in elm_xnet.index:
        id_sta_cubic_source = elm_xnet.at[source_id, "bus1"]  # id of the cubicle connecting the source and its bus
        bus_id = sta_cubic.at[id_sta_cubic_source, "cterm"]  # id of the bus to which the source is connected
        un = elm_term.at[bus_id, "uknom"] / np.sqrt(3) * 1e3  # phase-to-neutral voltage (V)
        tap = elm_xnet.at[source_id, "usetp"]  # tap voltage (p.u.)
        voltages = [un * tap, un * np.exp(-np.pi * 2 / 3 * 1j) * tap, un * np.exp(np.pi * 2 / 3 * 1j) * tap]
        source_bus = buses[bus_id]

        sources[source_id] = VoltageSource(id=source_id, phases="abcn", bus=source_bus, voltages=voltages)
        source_bus.connect(ground)

    # LV loads
    loads: dict[str, AbstractLoad] = {}
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
    branches: dict[str, AbstractBranch] = {}
    if elm_lne is not None:

        line_types: dict[str, LineCharacteristics] = {}
        for type_id in typ_lne.index:
            # TODO: use the detailed phase information instead of n
            n = typ_lne.at[type_id, "nlnph"] + typ_lne.at[type_id, "nneutral"]
            if n == 4:
                line_model = LineModel.SYM_NEUTRAL
            elif n == 3:
                line_model = LineModel.SYM
            else:
                msg = f"The number of phases ({n}) of line type {type_id!r} cannot be handled, it should be 3 or 4."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_NUMBER)

            line_types[type_id] = LineCharacteristics.from_sym(
                type_id,
                r0=typ_lne.at[type_id, "rline0"],
                model=line_model,
                r1=typ_lne.at[type_id, "rline"],
                x0=typ_lne.at[type_id, "xline0"],
                x1=typ_lne.at[type_id, "xline"],
                g0=Q_(typ_lne.at[type_id, "gline0"], "uS/km"),
                g1=Q_(typ_lne.at[type_id, "gline"], "uS/km"),
                b0=Q_(typ_lne.at[type_id, "bline0"], "uS/km"),
                b1=Q_(typ_lne.at[type_id, "bline"], "uS/km"),
                rn=typ_lne.at[type_id, "rnline"],
                xn=typ_lne.at[type_id, "xnline"],
                xpn=typ_lne.at[type_id, "xpnline"],
                bn=Q_(typ_lne.at[type_id, "bnline"], "uS/km"),
                bpn=Q_(typ_lne.at[type_id, "bpnline"], "uS/km"),
            )

        for line_id in elm_lne.index:
            type_id = elm_lne.at[line_id, "typ_id"]  # id of the line type

            branches[line_id] = Line.from_dict(
                id=line_id,
                bus1=buses[sta_cubic.at[elm_lne.at[line_id, "bus1"], "cterm"]],
                bus2=buses[sta_cubic.at[elm_lne.at[line_id, "bus2"], "cterm"]],
                length=elm_lne.at[line_id, "dline"],
                line_type=line_types[type_id],
                ground=ground,
            )

    # Transformers
    if elm_tr is not None:
        # Transformers type
        transformers_data: dict[str, TransformerCharacteristics] = {}
        transformers_tap: dict[str, int] = {}
        for idx in typ_tr.index:
            # Extract data
            name = typ_tr.at[idx, "loc_name"]
            sn = typ_tr.at[idx, "strn"] * 1e6  # The nominal voltages of the transformer (MVA -> VA)
            uhv = typ_tr.at[idx, "utrn_h"] * 1e3  # Phase-to-phase nominal voltages of the high voltages side (kV -> V)
            ulv = typ_tr.at[idx, "utrn_l"] * 1e3  # Phase-to-phase nominal voltages of the low voltages side (kV -> V)
            i0 = typ_tr.at[idx, "curmg"] / 3 / 100  # Current during off-load test (%)
            p0 = typ_tr.at[idx, "pfe"] * 1e3 / 3  # Losses during off-load test (kW -> W)
            psc = typ_tr.at[idx, "pcutr"] * 1e3  # Losses during short circuit test (kW -> W)
            vsc = typ_tr.at[idx, "uktr"] / 100  # Voltages on LV side during short circuit test (%)
            # Windings of the transformer
            windings = f"{typ_tr.at[idx, 'tr2cn_h']}{typ_tr.at[idx, 'tr2cn_l']}{typ_tr.at[idx, 'nt2ag']}"

            # Generate transformer parameters
            transformers_data[idx] = TransformerCharacteristics(name, windings, uhv, ulv, sn, p0, i0, psc, vsc)
            transformers_tap[idx] = typ_tr.at[idx, "dutap"]

        # Create transformers
        for idx in elm_tr.index:
            type_id = elm_tr.at[idx, "typ_id"]  # id of the line type
            tap = 1.0 + elm_tr.at[idx, "nntap"] * transformers_tap[type_id] / 100
            branches[idx] = Transformer.from_dict(
                id=idx,
                bus1=buses[sta_cubic.at[elm_tr.at[idx, "bushv"], "cterm"]],
                bus2=buses[sta_cubic.at[elm_tr.at[idx, "buslv"], "cterm"]],
                transformer_type=transformers_data[type_id],
                tap=tap,
            )
            ground.connect_to_bus(bus=buses[sta_cubic.at[elm_tr.at[idx, "buslv"], "cterm"]])

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

    return buses, branches, loads, sources, [p_ref, ground]


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
    if "ElmTr2" in data.keys():
        elm_tr = pd.DataFrame(columns=data["ElmTr2"]["Attributes"], data=data["ElmTr2"]["Values"]).set_index("FID")
    else:
        elm_tr = None

    # Transformer types
    if "TypTr2" in data.keys():
        typ_tr = pd.DataFrame(columns=data["TypTr2"]["Attributes"], data=data["TypTr2"]["Values"]).set_index("FID")
    else:
        typ_tr = None

    # Switch
    if "ElmCoup" in data.keys():
        elm_coup = pd.DataFrame(columns=data["ElmCoup"]["Attributes"], data=data["ElmCoup"]["Values"]).set_index("FID")
    else:
        elm_coup = None

    # Lines
    if "ElmLne" in data.keys():
        elm_lne = pd.DataFrame(columns=data["ElmLne"]["Attributes"], data=data["ElmLne"]["Values"]).set_index("FID")
    else:
        elm_lne = None

    # Line types
    if "TypLne" in data.keys():
        typ_lne = pd.DataFrame(columns=data["TypLne"]["Attributes"], data=data["TypLne"]["Values"]).set_index("FID")
    else:
        typ_lne = None

    # LV loads
    if "ElmLodLV" in data.keys():
        elm_lod_lv = pd.DataFrame(columns=data["ElmLodLV"]["Attributes"], data=data["ElmLodLV"]["Values"]).set_index(
            "FID"
        )
    else:
        elm_lod_lv = None

    # MV loads
    if "ElmLodmv" in data.keys():
        elm_lod_mv = pd.DataFrame(columns=data["ElmLodmv"]["Attributes"], data=data["ElmLodmv"]["Values"]).set_index(
            "FID"
        )
    else:
        elm_lod_mv = None

    # Generators
    if "ElmGenStat" in data.keys():
        elm_gen_stat = pd.DataFrame(
            columns=data["ElmGenStat"]["Attributes"], data=data["ElmGenStat"]["Values"]
        ).set_index("FID")
    else:
        elm_gen_stat = None

    # LV generators
    # Generators
    if "ElmPvsys" in data.keys():
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
    loads: dict[str, AbstractLoad],
    buses: dict[str, Bus],
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

        if sa == 0 and sb == 0 and sc == 0:  # Balanced
            s = [s_phase / 3, s_phase / 3, s_phase / 3]
        else:  # Unbalanced
            s = [sa, sb, sc]
        loads[load_id] = PowerLoad(id=load_id, phases="abcn", bus=buses[bus_id], s=s)


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
