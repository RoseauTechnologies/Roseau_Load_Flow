import logging
from typing import TYPE_CHECKING, Final

import numpy as np
import pandas as pd
import shapely

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dgs.utils import parse_extra_rlf_data
from roseau.load_flow.models import Bus, Ground, GroundConnection, RegulatorParameters, VoltageRegulator
from roseau.load_flow.models.regulator_parameters import (
    PowerFactoryClosedDeltaConnection,
    PowerFactoryRegulatorConfiguration,
    PowerFactoryRegulatorType,
)
from roseau.load_flow.typing import Id
from roseau.load_flow.utils import warn_external

if TYPE_CHECKING:
    import roseau.load_flow_single as rlfs

logger = logging.getLogger(__name__)

REGULATOR_CONFIGURATIONS: Final[dict[int, PowerFactoryRegulatorConfiguration]] = {
    1: "Star, 3-phase",
    2: "Star, 3 x 1-phase",
    3: "Closed delta, 3 x 1-phase",
    4: "Open delta, 2 x 1-phase",
}
"""The configurations of the PowerFactory step-voltage regulator types (``TypVoltreg.config``)."""
REGULATOR_TYPES: Final[dict[int, PowerFactoryRegulatorType]] = {0: "Type A", 1: "Type B"}
"""The types of the PowerFactory step-voltage regulators (``TypVoltreg.type``)."""
CLOSED_DELTA_CONNECTIONS: Final[dict[int, PowerFactoryClosedDeltaConnection]] = {0: "Lagging", 1: "Leading"}
"""The connections of the PowerFactory closed-delta step-voltage regulators (``TypVoltreg.cldeltacn``)."""


def _get(df: pd.DataFrame, idx: str, column: str) -> object | None:
    """Get the value of a column of a dataframe row, or None if the column or value is missing."""
    if column not in df.columns:
        return None
    value = df.at[idx, column]
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return value


#
# DGS -> RLF
#
def typ_voltreg_to_rp(
    typ_voltreg: pd.DataFrame,
    regulator_params: dict[str, RegulatorParameters],
    use_name_as_id: bool,
    multi_phase: bool = True,
) -> None:
    """Generate the regulator parameters from the "TypVoltreg" dataframe.

    PowerFactory's step-voltage regulator type is read with
    :meth:`RegulatorParameters.from_power_factory`. The magnetising admittance and the tap
    smoothing ``alpha`` have no PowerFactory equivalent: they are read from the description of the
    type (``desc:0``) when it holds roseau-load-flow data.

    Args:
        typ_voltreg:
            The "TypVoltreg" dataframe containing the regulator types data.

        regulator_params:
            The dictionary to store the parameters into indexed by the type's FID.

        use_name_as_id:
            Whether to use the type's ``loc_name`` as its ID or the FID.

        multi_phase:
            Whether the parameters are read for a multi-phase network. A single-phase network only
            has star regulators: the closed-delta configuration is then rejected.
    """
    supported = (1, 2, 3) if multi_phase else (1, 2)
    for fid in typ_voltreg.index:
        type_id = typ_voltreg.at[fid, "loc_name"] if use_name_as_id else fid

        # Configuration (1: "Star, 3-phase" by default)
        config = int(_get(typ_voltreg, fid, "config") or 1)  # type: ignore[arg-type]
        configuration = REGULATOR_CONFIGURATIONS.get(config)
        if configuration is None or config not in supported:
            what = "star and closed-delta configurations (1, 2, 3)" if multi_phase else "star configurations (1, 2)"
            msg = (
                f"The step-voltage regulator type {type_id!r} has the configuration {config}: only "
                f"the {what} are supported."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED)
        closed_delta_connection = None
        if configuration == "Closed delta, 3 x 1-phase" and (code := _get(typ_voltreg, fid, "cldeltacn")) is not None:
            closed_delta_connection = CLOSED_DELTA_CONNECTIONS.get(int(code))  # type: ignore[arg-type]
            if closed_delta_connection is None:
                msg = (
                    f"The step-voltage regulator type {type_id!r} has an unknown closed delta "
                    f"connection {code}: only the lagging (0) and leading (1) connections exist."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED)
        if multi_phase and configuration == "Star, 3-phase":
            warn_external(
                f"The step-voltage regulator type {type_id!r} is a 'Star, 3-phase' one, whose single "
                f"tap controller is read as three independent units."
            )

        # Type A or B
        kind_code = int(_get(typ_voltreg, fid, "type") or 0)  # type: ignore[arg-type]
        kind = REGULATOR_TYPES.get(kind_code)
        if kind is None:
            warn_external(
                f"The step-voltage regulator type {type_id!r} has an unknown type {kind_code}, read "
                f"as a Type A regulator."
            )
            kind = "Type A"
        if _get(typ_voltreg, fid, "itapzdep"):
            warn_external(
                f"The step-voltage regulator type {type_id!r} has a tap-dependent impedance, which "
                f"is not supported: its impedance at the neutral tap is used."
            )

        # Rated voltage (kV) and current (A). `In` first: PowerFactory's exports round the derived `Sb`
        un = float(typ_voltreg.at[fid, "Un"])
        sb_factor = np.sqrt(3) if configuration == "Star, 3-phase" else 1.0
        if (in_ := _get(typ_voltreg, fid, "In")) is not None:
            in_ = float(in_)  # type: ignore[arg-type]
        elif (sb := _get(typ_voltreg, fid, "Sb")) is not None:
            in_ = float(sb) / (sb_factor * un)  # type: ignore[arg-type]  # kVA / kV = A
        else:
            msg = f"The step-voltage regulator type {type_id!r} has neither 'In' nor 'Sb'."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)

        # Regulation range (%)
        pc_reg = _get(typ_voltreg, fid, "pcReg")
        if pc_reg is None:
            dutap, ntapmax = _get(typ_voltreg, fid, "dutap"), _get(typ_voltreg, fid, "ntapmax")
            if dutap is None or ntapmax is None:
                msg = f"The step-voltage regulator type {type_id!r} has neither 'pcReg' nor 'dutap' and 'ntapmax'."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)
            pc_reg = float(dutap) * float(ntapmax)  # type: ignore[arg-type]

        # Series impedance. `uk`/`pcu` first: PowerFactory's exports round the derived `r1pu`/`x1pu`
        uk, pcu = _get(typ_voltreg, fid, "uk"), _get(typ_voltreg, fid, "pcu")
        if uk is None or pcu is None:
            r1pu, x1pu = _get(typ_voltreg, fid, "r1pu"), _get(typ_voltreg, fid, "x1pu")
            if r1pu is None or x1pu is None:
                msg = f"The step-voltage regulator type {type_id!r} has neither 'uk' and 'pcu' nor 'r1pu' and 'x1pu'."
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_MISSING_REQUIRED_DATA)
            sb = sb_factor * un * 1e3 * in_  # VA
            uk = abs(complex(float(r1pu), float(x1pu))) * 100.0  # type: ignore[arg-type]
            pcu = float(r1pu) * sb  # type: ignore[arg-type]

        rp = RegulatorParameters.from_power_factory(
            type_id,
            un=un,
            in_=in_,
            pc_reg=float(pc_reg),  # type: ignore[arg-type]
            uk=float(uk),  # type: ignore[arg-type]
            pcu=float(pcu),  # type: ignore[arg-type]
            kind=kind,
            configuration=configuration,
            closed_delta_connection=closed_delta_connection,
        )

        # Extra data of roseau-load-flow (magnetising admittance and alpha)
        desc = _get(typ_voltreg, fid, "desc:0")
        extra = parse_extra_rlf_data(desc) if isinstance(desc, str) else {}
        if extra and ("ym" in extra or "alpha" in extra):
            ym = complex(*extra["ym"]) if "ym" in extra else 0j
            rp = RegulatorParameters(
                type_id,
                sn=rp._sn,
                un=rp._un,
                z2=rp._z2,
                ym=ym,
                u_range=rp._u_range,
                connection=rp._connection,
                alpha=float(extra.get("alpha", rp._alpha)),
            )
        regulator_params[fid] = rp


def check_elm_voltreg(elm_voltreg: pd.DataFrame, idx: Id) -> None:
    """Check the control settings of a step-voltage regulator, warning about those that the
    continuous controller with independent units does not model.

    Raises:
        RoseauLoadFlowException: If the automatic tap changing is off (a fixed-tap regulator is
        not modelled).
    """
    if _get(elm_voltreg, idx, "ntrcn") == 0:
        msg = f"The step-voltage regulator {idx!r} has no automatic tap changing, which is not supported."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_NOT_SUPPORTED)
    if _get(elm_voltreg, idx, "i_cont") == 0:
        warn_external(f"The step-voltage regulator {idx!r} has a discrete tap changer, modelled as a continuous one.")
    if _get(elm_voltreg, idx, "ildc"):
        warn_external(
            f"The step-voltage regulator {idx!r} has a line drop compensation, which is not supported: it is ignored."
        )
    if _get(elm_voltreg, idx, "iRevPQ"):
        warn_external(
            f"The step-voltage regulator {idx!r} has a reverse power operation mode, which is "
            f"not supported: it is ignored."
        )


def regulator_geometry(
    elm_voltreg: pd.DataFrame, idx: Id, bus1: "Bus | rlfs.Bus", bus2: "Bus | rlfs.Bus"
) -> shapely.Point | None:
    """The geometry of a step-voltage regulator: its GPS coordinates if any, else the middle of its
    buses (as for the transformers)."""
    lon, lat = _get(elm_voltreg, idx, "GPSlon"), _get(elm_voltreg, idx, "GPSlat")
    if lon is not None and lat is not None and (lon, lat) != (0, 0):
        return shapely.Point(lon, lat)
    elif bus1.geometry is not None and bus2.geometry is not None:
        return shapely.LineString([bus1.geometry, bus2.geometry]).centroid  # type: ignore
    else:
        return None


def elm_voltreg_to_regulators(
    elm_voltreg: pd.DataFrame,
    regulators: dict[Id, VoltageRegulator],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    regulator_params: dict[str, RegulatorParameters],
) -> list[VoltageRegulator]:
    """Generate the voltage regulators of the network.

    The configuration of the regulator type gives the shape of the regulator: the star
    configurations give a ``"wye"`` regulator with the phases ``"abcn"`` (the neutral carried
    through), which needs a neutral on both of its buses; the closed-delta configuration gives a
    closed-delta regulator with the phases ``"abc"``. Every unit regulates its own voltage at the
    setpoint ``usetp`` (p.u.).

    Args:
        elm_voltreg:
            The "ElmVoltreg" dataframe containing the step-voltage regulators data.

        regulators:
            The dictionary to store the regulators into.

        buses:
            The dictionary of the all buses indexed by their FID.

        sta_cubic:
            The "StaCubic" dataframe of cubicles indexed by their FID.

        regulator_params:
            The dictionary of all regulator parameters indexed by their FID.

    Returns:
        The star regulators whose star point is earthed (``cgnd = 0``, the default): their
        source-side neutral must be connected to the ground.
    """
    earthed_star_points: list[VoltageRegulator] = []
    for idx in elm_voltreg.index:
        check_elm_voltreg(elm_voltreg, idx)
        if _get(elm_voltreg, idx, "igang"):
            warn_external(
                f"The step-voltage regulator {idx!r} has ganged taps, which are not supported: its "
                f"units are controlled independently."
            )

        type_id = elm_voltreg.at[idx, "typ_id"]  # FID of the regulator type
        if type_id not in regulator_params:
            msg = f"The step-voltage regulator {idx!r} has an unknown type {type_id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_TYPE_ID)
        parameters = regulator_params[type_id]
        bus1 = buses[sta_cubic.at[elm_voltreg.at[idx, "buss"], "cterm"]]
        bus2 = buses[sta_cubic.at[elm_voltreg.at[idx, "busl"], "cterm"]]
        if parameters.is_delta:
            phases = "abc"
        else:
            if "n" not in bus1.phases or "n" not in bus2.phases:
                msg = (
                    f"The star step-voltage regulator {idx!r} is connected to a terminal without "
                    f"neutral, which is not supported: a star regulator needs a neutral (ABC-N "
                    f"terminals) on both sides."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DGS_BAD_PHASE_TECHNOLOGY)
            phases = "abcn"
        u_ref = _get(elm_voltreg, idx, "usetp")
        maxload = _get(elm_voltreg, idx, "maxload")
        geometry = regulator_geometry(elm_voltreg, idx, bus1=bus1, bus2=bus2)
        regulator = VoltageRegulator(
            id=idx,
            bus1=bus1,
            bus2=bus2,
            parameters=parameters,
            u_ref=1.0 if u_ref is None else float(u_ref),  # type: ignore[arg-type]
            phases=phases,
            max_loading=1.0 if maxload is None else float(maxload) / 100,  # type: ignore[arg-type]
            geometry=geometry,
        )
        regulators[idx] = regulator
        if not parameters.is_delta and _get(elm_voltreg, idx, "cgnd") != 1:
            earthed_star_points.append(regulator)
    return earthed_star_points


def voltreg_to_regulators(
    typ_voltreg: pd.DataFrame | None,
    elm_voltreg: pd.DataFrame | None,
    regulators: dict[Id, VoltageRegulator],
    buses: dict[str, Bus],
    sta_cubic: pd.DataFrame,
    use_name_as_id: bool,
) -> list[VoltageRegulator]:
    """Generate the regulator parameters and the voltage regulators of the network.

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

    Returns:
        The star regulators whose star point is earthed (see :func:`earth_star_points`).
    """
    if elm_voltreg is None:
        return []
    regulator_params: dict[str, RegulatorParameters] = {}  # key is the FID
    if typ_voltreg is not None:
        if use_name_as_id:
            # Reindex the types by their FID, used by the regulators
            typ_voltreg = typ_voltreg.reset_index(drop=False).set_index("FID")
        typ_voltreg_to_rp(typ_voltreg=typ_voltreg, regulator_params=regulator_params, use_name_as_id=use_name_as_id)
    return elm_voltreg_to_regulators(
        elm_voltreg=elm_voltreg,
        regulators=regulators,
        buses=buses,
        sta_cubic=sta_cubic,
        regulator_params=regulator_params,
    )


def earth_star_points(
    regulators: list[VoltageRegulator], ground: Ground, ground_connections: dict[Id, GroundConnection]
) -> None:
    """Earth the source-side neutral of the star regulators whose star point is earthed, unless it
    already is.

    This must be done once the potential references of the network are added: as in PowerFactory,
    the star point is earthed in addition to the other earthings of the network.
    """
    for regulator in regulators:
        bus = regulator.bus1
        if not any(
            isinstance(e, GroundConnection) and e.element is bus and e.phase == "n" for e in bus._connected_elements
        ):
            gc = GroundConnection(id=f"gc (regulator {regulator.id!r})", element=bus, ground=ground)
            ground_connections[gc.id] = gc
