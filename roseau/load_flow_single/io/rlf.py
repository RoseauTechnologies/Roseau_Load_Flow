import cmath
import logging
from typing import Literal

import numpy as np

import roseau.load_flow as rlf
from roseau.load_flow.typing import ComplexArray, Id, JsonDict
from roseau.load_flow.utils import warn_external
from roseau.load_flow_single.io.common import NetworkElements
from roseau.load_flow_single.models import (
    AbstractLoad,
    Bus,
    CurrentLoad,
    FlexibleParameter,
    ImpedanceLoad,
    Line,
    LineParameters,
    PowerLoad,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)

logger = logging.getLogger(__name__)

type OnIncompatibleType = Literal["ignore", "warn", "raise-critical", "raise"]


def _handle_incompatibility(msg: str, on_incompatible: OnIncompatibleType, critical: bool = True) -> None:
    if on_incompatible == "ignore":
        pass
    elif on_incompatible == "warn":
        warn_external(msg, UserWarning)
    elif on_incompatible == "raise-critical":
        if critical:
            raise rlf.RoseauLoadFlowException(msg, code=rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE)
        else:
            warn_external(msg, UserWarning)
    elif on_incompatible == "raise":
        raise rlf.RoseauLoadFlowException(msg, code=rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE)
    else:
        raise ValueError(
            f"Invalid value for `on_incompatible`: {on_incompatible!r}. Expected one of 'ignore', "
            f"'warn', 'raise-critical', or 'raise'."
        )


def _handle_floating_neutral(element_m: rlf.AbstractConnectable, on_incompatible: OnIncompatibleType) -> None:
    if element_m.has_floating_neutral:
        _handle_incompatibility(
            f"{element_m.element_type!r} {element_m.id!r} {element_m._side_desc}has a floating neutral, which is not supported.",
            on_incompatible=on_incompatible,
            critical=False,
        )


def _balance_voltages(
    ph: str, voltages: ComplexArray, msg: str, on_incompatible: OnIncompatibleType, critical: bool = True
) -> complex:
    """Calculate and return √3*Van to be used in the single-phase equivalent network."""
    if ph in ("abc", "abcn"):  # "abc" or "abcn" (most common case)
        v0, v1, v2 = rlf.sym.phasor_to_sym(voltages).tolist()
        if not ph.endswith("n"):
            v1 /= 1 - rlf.ALPHA2
        voltage = v1 * rlf.SQRT3
        if not np.allclose([v0, v2], 0):
            _handle_incompatibility(msg, on_incompatible=on_incompatible, critical=critical)
    elif ph in ("abn", "bcn", "can"):  # abn, bcn, can
        v1n, v2n = voltages.tolist()
        if ph == "abn":
            voltage = v1n * rlf.SQRT3
        elif ph == "bcn":
            voltage = -(v1n + v2n) * rlf.SQRT3
        elif ph == "can":
            voltage = v2n * rlf.SQRT3
        if not cmath.isclose(v2n, v1n * rlf.ALPHA2):
            _handle_incompatibility(msg, on_incompatible=on_incompatible, critical=critical)
    elif ph == "ab":
        voltage = voltages.item(0) / cmath.rect(1, cmath.pi / 6)
    elif ph == "bc":
        voltage = voltages.item(0) / cmath.rect(1, -cmath.pi / 2)
    elif ph == "ca":
        voltage = voltages.item(0) / cmath.rect(1, 5 * cmath.pi / 6)
    elif ph == "an":
        van = voltages.item(0)
        voltage = van * rlf.SQRT3
    elif ph == "bn":
        vbn = voltages.item(0)
        van = vbn / rlf.ALPHA2
        voltage = van * rlf.SQRT3
    elif ph == "cn":
        vcn = voltages.item(0)
        van = vcn / rlf.ALPHA
        voltage = van * rlf.SQRT3
    else:
        raise AssertionError(ph)
    return voltage


def network_from_rlf(  # noqa: C901
    en_m: rlf.ElectricalNetwork, /, *, on_incompatible: OnIncompatibleType
) -> tuple[NetworkElements, dict[str, JsonDict]]:
    """Convert a multi-phase electrical network to a single-phase one.

    Args:
        en_m:
            The multi-phase electrical network. Buses and branches must be three-phase.

        on_incompatible:
            Action to take when an incompatibility is found. Options are:
            - "ignore": Ignore incompatible elements.
            - "warn": Issue a warning but continue processing.
            - "raise-critical": Raise on critical incompatibilities, warn on non-critical ones.
            - "raise": Raise an exception for all incompatibilities.

    Returns:
        A tuple containing:
            - `NetworkElements`: The converted network elements
            - `dict[str, JsonDict]`: Tool data for the network
    """
    if not isinstance(en_m, rlf.ElectricalNetwork):
        raise TypeError(f"Expected an instance of `rlf.ElectricalNetwork`, got {type(en_m)}")

    # Check grounds
    if (n_grounds := len(en_m.grounds)) != 1:
        _handle_incompatibility(
            f"Expected 1 ground, found {n_grounds}", on_incompatible=on_incompatible, critical=False
        )

    # Check ground connections
    for gc in en_m.ground_connections.values():
        if gc.phase != "n":
            _handle_incompatibility(
                f"Ground connection {gc.id!r} has incompatible phases {gc.phase!r}, expected 'n'",
                on_incompatible=on_incompatible,
                critical=False,
            )

    # Check potential references
    for pref in en_m.potential_refs.values():
        if pref.phases not in ("abc", "abcn", "n", None):
            _handle_incompatibility(
                f"Potential ref {pref.id!r} has incompatible phases {pref.phases!r}, expected 'abc', 'abcn', or 'n'",
                on_incompatible=on_incompatible,
                critical=False,
            )

    # Convert buses
    buses: dict[Id, Bus] = {}
    for bus_m in en_m.buses.values():
        ph = bus_m.phases
        if "abc" not in ph:
            msg = f"Bus {bus_m.id!r} is not three-phase, phases={ph!r}"
            raise rlf.RoseauLoadFlowException(msg, code=rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE)
        if bus_m._initialized_by_the_user and (init_pot := bus_m._initial_potentials) is not None:
            init_voltages = rlf.converters._calculate_voltages(init_pot, ph)
            v_i = _balance_voltages(
                ph,
                init_voltages,
                f"Bus {bus_m.id!r} has unbalanced initial potentials",
                on_incompatible,
                critical=False,
            )
        else:
            v_i = None

        bus_s = Bus(
            id=bus_m.id,
            nominal_voltage=bus_m._nominal_voltage,
            min_voltage_level=bus_m._min_voltage_level,
            max_voltage_level=bus_m._max_voltage_level,
            initial_voltage=v_i,
            geometry=bus_m.geometry,
        )
        buses[bus_s.id] = bus_s

    # Convert line and transformer parameters
    ln_params_m: set[Id] = set()
    ln_params_s: dict[Id, LineParameters] = {}
    for ln_m in en_m.lines.values():
        lp_m = ln_m.parameters
        if lp_m.id in ln_params_m:
            continue
        ln_params_m.add(lp_m.id)
        try:
            lp_s = LineParameters.from_roseau_load_flow(lp_m, strict=on_incompatible != "ignore")
        except rlf.RoseauLoadFlowException as e:
            if on_incompatible == "raise":
                raise
            else:
                _handle_incompatibility(e.msg, on_incompatible=on_incompatible, critical=False)
            lp_s = LineParameters.from_roseau_load_flow(lp_m, strict=False)
        ln_params_s[lp_s.id] = lp_s

    tr_params_m: set[Id] = set()
    tr_params_s: dict[Id, TransformerParameters] = {}
    for tr_m in en_m.transformers.values():
        tp_m = tr_m.parameters
        if tp_m.id in tr_params_m:
            continue
        tr_params_m.add(tp_m.id)
        tp_s = TransformerParameters.from_roseau_load_flow(tp_m)
        tr_params_s[tp_s.id] = tp_s

    # Convert lines
    lines: dict[Id, Line] = {}
    for ln_m in en_m.lines.values():
        if "abc" not in ln_m.phases:
            msg = f"Line {ln_m.id!r} is not three-phase, phases={ln_m.phases!r}"
            raise rlf.RoseauLoadFlowException(msg, code=rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE)
        ln_s = Line(
            id=ln_m.id,
            bus1=buses[ln_m.side1.bus.id],
            bus2=buses[ln_m.side2.bus.id],
            parameters=ln_params_s[ln_m.parameters.id],
            length=ln_m._length,
            max_loading=ln_m._max_loading,
            geometry=ln_m.geometry,
        )
        lines[ln_s.id] = ln_s

    # Convert transformers
    transformers: dict[Id, Transformer] = {}
    for tr_m in en_m.transformers.values():
        # Three-phase check done in parameters
        tr_s = Transformer(
            id=tr_m.id,
            bus_hv=buses[tr_m.side_hv.bus.id],
            bus_lv=buses[tr_m.side_lv.bus.id],
            parameters=tr_params_s[tr_m.parameters.id],
            tap=tr_m.tap,
            max_loading=tr_m._max_loading,
            geometry=tr_m.geometry,
        )
        _handle_floating_neutral(tr_m.side_hv, on_incompatible=on_incompatible)
        _handle_floating_neutral(tr_m.side_lv, on_incompatible=on_incompatible)
        transformers[tr_s.id] = tr_s

    # Convert switches
    switches: dict[Id, Switch] = {}
    for sw_m in en_m.switches.values():
        if "abc" not in sw_m.phases:
            msg = f"Switch {sw_m.id!r} is not three-phase, phases={sw_m.phases!r}"
            raise rlf.RoseauLoadFlowException(msg, code=rlf.RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE)
        sw_s = Switch(
            id=sw_m.id,
            bus1=buses[sw_m.bus1.id],
            bus2=buses[sw_m.bus2.id],
            closed=sw_m.closed,
            geometry=sw_m.geometry,
        )
        switches[sw_s.id] = sw_s

    # Convert sources
    sources: dict[Id, VoltageSource] = {}
    for src_m in en_m.sources.values():
        ph = src_m.phases
        if "abc" not in ph:
            _handle_incompatibility(
                f"Source {src_m.id!r} is not three-phase, phases={ph!r}", on_incompatible=on_incompatible
            )
        voltage = _balance_voltages(
            ph,
            voltages=src_m._voltages,
            msg=f"Source {src_m.id!r} has unbalanced voltages",
            on_incompatible=on_incompatible,
        )
        _handle_floating_neutral(src_m, on_incompatible=on_incompatible)
        src_s = VoltageSource(id=src_m.id, bus=buses[src_m.bus.id], voltage=voltage)
        sources[src_s.id] = src_s

    # Convert loads
    loads: dict[Id, AbstractLoad] = {}
    for ld_m in en_m.loads.values():
        ph = ld_m.phases
        if "abc" not in ph:
            _handle_incompatibility(
                f"Load {ld_m.id!r} is not three-phase, phases={ph!r}", on_incompatible=on_incompatible
            )
        if isinstance(ld_m, rlf.PowerLoad):
            if np.unique_values(ld_m._powers).size != 1:
                _handle_incompatibility(f"Load {ld_m.id!r} has unbalanced powers", on_incompatible=on_incompatible)
            if ld_m.flexible_params is None:
                fp_s = None
            else:
                if not all(fp == ld_m.flexible_params[0] for fp in ld_m.flexible_params[1:]):
                    _handle_incompatibility(
                        f"Load {ld_m.id!r} has unbalanced flexible parameters", on_incompatible=on_incompatible
                    )
                fp_s = FlexibleParameter.from_roseau_load_flow(ld_m.flexible_params[0], phases=ld_m.voltage_phases[0])
            ld_s = PowerLoad(id=ld_m.id, bus=buses[ld_m.bus.id], power=ld_m._powers.sum(), flexible_param=fp_s)
        elif isinstance(ld_m, rlf.CurrentLoad):
            if np.unique_values(ld_m._currents).size != 1:
                _handle_incompatibility(f"Load {ld_m.id!r} has unbalanced currents", on_incompatible=on_incompatible)
            current = np.mean(ld_m._currents).item()
            if "n" not in ph:
                # Ia = Iab - Ica = (Van-Vbn) / Zab - (Vcn-Van) / Zca, etc. --> Il = Ip * √3
                current *= rlf.SQRT3
            ld_s = CurrentLoad(id=ld_m.id, bus=buses[ld_m.bus.id], current=current)
        elif isinstance(ld_m, rlf.ImpedanceLoad):
            if np.unique_values(ld_m._impedances).size != 1:
                _handle_incompatibility(f"Load {ld_m.id!r} has unbalanced impedances", on_incompatible=on_incompatible)
            impedance = np.mean(ld_m._impedances).item()
            if "n" not in ph:
                # (Δ-Y) transform: Zan = Zab*Zca/(Zab+Zbc+Zca), etc. --> Zpn = Zpp / 3
                impedance /= 3
            ld_s = ImpedanceLoad(id=ld_m.id, bus=buses[ld_m.bus.id], impedance=impedance)
        else:
            raise NotImplementedError(f"Load type {ld_m.type!r} is not implemented.")
        _handle_floating_neutral(ld_m, on_incompatible=on_incompatible)
        loads[ld_s.id] = ld_s

    return (
        {
            "buses": buses,
            "lines": lines,
            "transformers": transformers,
            "switches": switches,
            "loads": loads,
            "sources": sources,
            "crs": en_m.crs,
        },
        en_m.tool_data.to_dict(),
    )
