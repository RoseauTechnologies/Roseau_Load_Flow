import logging

import pandas as pd

import roseau.load_flow as rlf
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.regulators import _get, check_elm_voltreg, regulator_geometry, typ_voltreg_to_rp
from roseau.load_flow.typing import Id
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
