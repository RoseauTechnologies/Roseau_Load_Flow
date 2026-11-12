import logging
from collections.abc import Iterable, Iterator

import pandas as pd

import roseau.load_flow as rlf
from roseau.load_flow.constants import SQRT3
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.regulators import _get, check_elm_voltreg, regulator_geometry, typ_voltreg_to_rp
from roseau.load_flow.io.dgs.utils import DEFAULT_GPS_COORDS, DGSData, generate_extra_rlf_data, get_id_to_fid_map
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import warn_external
from roseau.load_flow_single.io.dgs.pwf import STA_CUBIC_FID_INDEX, STA_CUBIC_OBJ_ID_INDEX
from roseau.load_flow_single.models import Bus, RegulatorParameters, VoltageRegulator

logger = logging.getLogger(__name__)


#
# DGS -> RLFS
#
def voltreg_to_regulators(
    typ_voltreg: pd.DataFrame | None,
    elm_voltreg: pd.DataFrame | None,
    regulators: dict[Id, VoltageRegulator],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    use_name_as_id: bool,
) -> None:
    """Generate the regulator parameters and the voltage regulators of the network.

    The regulator types (``TypVoltreg``) are read as for multi-phase networks (see
    :meth:`roseau.load_flow.RegulatorParameters.from_power_factory`), restricted to the star
    configurations: a single-phase network has no closed-delta regulator. Every regulator
    (``ElmVoltreg``) regulates the voltage of its load side at the setpoint ``usetp`` (p.u.).

    Args:
        typ_voltreg:
            The "TypVoltreg" dataframe containing the regulator types data, if any.

        elm_voltreg:
            The "ElmVoltreg" dataframe containing the step-voltage regulators data, if any.

        regulators:
            The dictionary to store the regulators into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.

        use_name_as_id:
            Whether the dataframes are indexed by the ``loc_name`` of the elements or their FID.
    """
    if elm_voltreg is None:
        return
    regulator_params_m: dict[str, rlf.RegulatorParameters] = {}  # key is the FID
    if typ_voltreg is not None:
        if use_name_as_id:
            # Reindex the types by their FID, used by the regulators
            typ_voltreg = typ_voltreg.reset_index(drop=False).set_index("FID")
        typ_voltreg_to_rp(
            typ_voltreg=typ_voltreg,
            regulator_params=regulator_params_m,
            use_name_as_id=use_name_as_id,
            multi_phase=False,
        )
    regulator_params = {
        fid: RegulatorParameters(
            id=rp.id, sn=rp._sn, un=rp._un, z2=rp._z2, ym=rp._ym, u_range=rp._u_range, alpha=rp._alpha
        )
        for fid, rp in regulator_params_m.items()
    }

    for idx in elm_voltreg.index:
        check_elm_voltreg(elm_voltreg, idx)
        type_id = elm_voltreg.at[idx, "typ_id"]  # FID of the regulator type
        if type_id not in regulator_params:
            msg = f"The step-voltage regulator {idx!r} has an unknown type {type_id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_TYPE_ID)
        bus1 = buses[sta_cubic.at[elm_voltreg.at[idx, "buss"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_voltreg.at[idx, "busl"], "cterm"]]
        u_ref = _get(elm_voltreg, idx, "usetp")
        maxload = _get(elm_voltreg, idx, "maxload")
        regulators[idx] = VoltageRegulator(
            id=idx,
            bus1=bus1,
            bus2=bus2,
            parameters=regulator_params[type_id],
            u_ref=1.0 if u_ref is None else float(u_ref),  # type: ignore[arg-type]
            max_loading=1.0 if maxload is None else float(maxload) / 100,  # type: ignore[arg-type]
            geometry=regulator_geometry(elm_voltreg, idx, bus1=bus1, bus2=bus2),
        )


#
# RLFS -> DGS
#
TAP_STEPS = 16
"""The number of tap steps on each side of the neutral position of the exported regulator types
(the ANSI/IEEE C57.15 standard ±16 steps): only the total range matters to the continuous model."""


def rp_to_typ_voltreg(regulator_params: Iterable[RegulatorParameters], fid_counter: Iterator[str]) -> DGSData:
    """Generate the "TypVoltreg" data of the regulator parameters.

    The parameters are written as "Star, 3-phase" Type A regulator types, whose circuit base power
    ``Sb = √3·Un·In`` is the rated power ``sn`` of the parameters. The magnetising admittance and
    the steepness ``alpha``, which PowerFactory does not model, are stored in the description of the
    type (``desc:0``).
    """
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "type",  # Type:Type A:Type B
        "config",  # Configuration:Star, 3-phase:Star, 3x1-phase:Closed delta:Open delta
        "cldeltacn",  # Closed delta connection (unused by the star configuration)
        "opdeltacn",  # Open delta connection (unused by the star configuration)
        "frnom",  # Nominal frequency in Hz
        "Un",  # Rated voltage in kV
        "In",  # Rated current in A
        "Sn",  # Rated power in kVA
        "Sb",  # Circuit base power in kVA
        "pcReg",  # Voltage regulation range (+/-) in %
        "dutap",  # Additional voltage per tap in %
        "nntap0",  # Neutral position
        "ntapmin",  # Minimum position
        "ntapmax",  # Maximum position
        "itapzdep",  # Tap dependent impedance
        "uk",  # Short-circuit voltage uk in %
        "pcu",  # Copper losses in W
        "ukr",  # SHC-voltage (Re(uk)) ukr in %
        "xtor",  # Ratio X/R
        "x1pu",  # Reactance x in p.u.
        "r1pu",  # Resistance r in p.u.
        "desc:0",  # Description (used to store extra RLF data)
    ]
    values: list[list[str | float | None]] = []
    for rp in regulator_params:
        if rp._ym != 0:
            warn_external(
                f"The regulator parameters {rp.id!r} have a magnetising admittance {rp._ym} S, which "
                f"PowerFactory's step-voltage regulator does not model: it is only kept for the DGS "
                f"import of roseau-load-flow."
            )
        sb = rp._sn  # VA
        z_pu = rp._z2 / (rp._un**2 / sb)
        pc_reg = rp._u_range * 100.0
        desc0 = generate_extra_rlf_data({"ym": [rp._ym.real, rp._ym.imag], "alpha": rp._alpha})
        values.append(
            [
                next(fid_counter),  # FID
                "C",  # OP
                rp.id,  # loc_name
                None,  # fold_id
                0,  # type: Type A
                1,  # config: Star, 3-phase
                0,  # cldeltacn
                0,  # opdeltacn
                50,  # frnom
                rp._un / 1e3,  # Un
                sb / (SQRT3 * rp._un),  # In
                sb * rp._u_range / 1e3,  # Sn
                sb / 1e3,  # Sb
                pc_reg,  # pcReg
                pc_reg / TAP_STEPS,  # dutap
                0,  # nntap0
                -TAP_STEPS,  # ntapmin
                TAP_STEPS,  # ntapmax
                0,  # itapzdep
                abs(z_pu) * 100.0,  # uk
                z_pu.real * sb,  # pcu
                z_pu.real * 100.0,  # ukr
                z_pu.imag / z_pu.real if z_pu.real != 0 else None,  # xtor
                z_pu.imag,  # x1pu
                z_pu.real,  # r1pu
                desc0,  # desc:0
            ]
        )
    return {"Attributes": attributes, "Values": values}


def regulators_to_elm_voltreg(
    regulators: Iterable[VoltageRegulator],
    typ_voltreg: DGSData,
    fid_counter: Iterator[str],
    sta_cubic: dict[Id, tuple[list, list]],
    fold_id: str,
) -> DGSData:
    """Generate the "ElmVoltreg" data of the voltage regulators.

    The regulators are written with a continuous automatic tap changer controlling the
    positive-sequence voltage of their load side at their target voltage ``u_ref``.
    """
    attributes: list[str] = [
        "FID",  # Unique identifier for DGS file
        "OP",  # Operation (C=create, U=update, D=delete, M=merge, I=ignore)
        "loc_name",  # Name
        "fold_id",  # In Folder
        "typ_id",  # Type in TypVoltreg
        "buss",  # S-Side in StaCubic
        "busl",  # L-Side in StaCubic
        "outserv",  # Out of Service
        "GPSlat",  # Geographical Position: Latitude / Northing in deg
        "GPSlon",  # Geographical Position: Longitude / Easting in deg
        "cneutcon",  # N-Connection
        "cgnd",  # Star point
        "ntrcn",  # Automatic tap changing
        "i_cont",  # Tap changer:discrete:continuous
        "usetp",  # Voltage setpoint in p.u.
        "usp_low",  # Lower voltage bound in p.u.
        "usp_up",  # Upper voltage bound in p.u.
        "ilcph",  # Controlled phase:a:b:c:a-b:b-c:c-a:Pos.Seq.
        "nntap1",  # Tap 1 position
        "igang",  # Gang operated taps
        "i_pcReglim",  # Limited voltage control range
        "maxload",  # Max. loading in %
        "ildc",  # Line drop compensation (LDC)
        "ildc_lm",  # Voltage limit
        "iRevPQ",  # Reverse power operation
    ]
    values: list[list[str | float | None]] = []
    typ_fid_by_id = get_id_to_fid_map(typ_voltreg)
    for regulator in regulators:
        fid = next(fid_counter)
        cubic_s, cubic_l = sta_cubic[regulator.id]
        cubic_s[STA_CUBIC_OBJ_ID_INDEX] = fid
        cubic_l[STA_CUBIC_OBJ_ID_INDEX] = fid
        geom = regulator.geometry.centroid if regulator.geometry is not None else DEFAULT_GPS_COORDS
        u_ref = regulator._u_ref
        values.append(
            [
                fid,  # FID
                "C",  # OP
                regulator.id,  # loc_name
                fold_id,  # fold_id
                typ_fid_by_id[regulator.parameters.id],  # typ_id
                cubic_s[STA_CUBIC_FID_INDEX],  # buss
                cubic_l[STA_CUBIC_FID_INDEX],  # busl
                0,  # outserv
                geom.y,  # GPSlat
                geom.x,  # GPSlon
                0,  # cneutcon
                0,  # cgnd: earthed star point
                1,  # ntrcn: automatic tap changing
                1,  # i_cont: continuous
                u_ref,  # usetp
                u_ref - 0.01,  # usp_low
                u_ref + 0.01,  # usp_up
                6,  # ilcph: positive sequence
                0,  # nntap1
                0,  # igang
                0,  # i_pcReglim
                regulator._max_loading * 100.0,  # maxload
                0,  # ildc
                0,  # ildc_lm
                0,  # iRevPQ
            ]
        )
    return {"Attributes": attributes, "Values": values}
