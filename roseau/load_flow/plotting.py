"""Plotting functions for `roseau.load_flow`."""

import cmath
import dataclasses
import math
from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING, Any, Literal, Self, TypedDict

import geopandas as gpd
import numpy as np
from pint import PintError

from roseau.load_flow.models import AbstractTerminal, Bus, Line, Switch, Transformer
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.sym import NegativeSequence, PositiveSequence, ZeroSequence, phasor_to_sym
from roseau.load_flow.types import LineType
from roseau.load_flow.typing import ComplexArray, Id, ResultState
from roseau.load_flow.units import Q_

if TYPE_CHECKING:
    import folium
    import plotly.graph_objects as go
    from matplotlib.axes import Axes

    import roseau.load_flow_single as rlfs

    type FeatureMap = dict[str, Any]
    type StyleDict = dict[str, Any]
    type MapElementType = Literal["bus", "line", "transformer"]

    class VoltageProfileNode(TypedDict):
        distance: float
        voltage: float
        voltages: list[float] | None
        min_voltage: float | None
        max_voltage: float | None
        state: ResultState
        is_tr_bus: bool

    class VoltageProfileEdge(TypedDict):
        from_bus: Id
        to_bus: Id
        loading: float | None
        loadings: list[float] | None
        max_loading: float
        state: ResultState


_COLORS = {"a": "#234e83", "b": "#cad40e", "c": "#55b2aa", "n": "#000000"}
_COLORS.update(
    {
        "an": _COLORS["a"],
        "bn": _COLORS["b"],
        "cn": _COLORS["c"],
        "ab": _COLORS["a"],
        "bc": _COLORS["b"],
        "ca": _COLORS["c"],
    }
)

# TODO: consult with the frontend team for a color scheme
_RESULT_COLORS: dict[ResultState, str] = {
    "very-high": "#d7191c",  # reddish
    "high": "#fdae61",  # orangy
    "normal": "#1a9850",  # greenish
    "low": "#abd9e9",  # light bluish
    "very-low": "#2c7bb6",  # bluish
    "unknown": "#666666",  # gray
}


#
# Utility functions
#
def _get_rot(vector: complex) -> float:
    """Get the rotation of a vector in degrees."""
    rot = cmath.phase(vector) * 180 / cmath.pi
    if rot > 90:
        rot -= 180
    elif rot < -90:
        rot += 180
    return rot


def _get_align(rot: float) -> tuple[str, str]:
    """Get the horizontal and vertical alignment corresponding to a rotation angle."""
    if 45 < abs(rot) < 135:
        return "right", "center"
    else:
        return "center", "bottom"


def _configure_axes(ax: "Axes", vector: ComplexArray) -> None:
    """Configure the axes for a plot of complex data."""
    center = vector.mean()
    ax_lim = max(abs(vector - center)) * 1.2
    ax.grid()
    ax.set_axisbelow(True)
    ax.set_aspect("equal")
    ax.set_xlim(-ax_lim + center.real, ax_lim + center.real)
    ax.set_ylim(-ax_lim + center.imag, ax_lim + center.imag)


def _draw_voltage_phasor(
    ax: "Axes", potential1: complex, potential2: complex, color: str, annotate: bool = True
) -> None:
    """Draw a voltage phasor between two potentials."""
    voltage = potential1 - potential2
    midpoint = (potential1 + potential2) / 2
    ax.arrow(potential2.real, potential2.imag, voltage.real, voltage.imag, color=color)
    if annotate:
        rot = _get_rot(voltage)
        ha, va = _get_align(rot)
        ax.annotate(f"{abs(voltage):.0f}V", (midpoint.real, midpoint.imag), ha=ha, va=va, rotation=rot)


def _get_phases_and_potentials(
    element: AbstractTerminal, voltage_type: Literal["pp", "pn", "auto"]
) -> tuple[AbstractTerminal, str, ComplexArray]:
    if not element.is_multi_phase:
        raise TypeError(f"Only multi-phase elements can be plotted. Did you mean to use rlf.{type(element).__name__}?")
    if not isinstance(element, AbstractTerminal):
        raise ValueError(
            "The element must be a terminal (bus, load, source) or a branch side (line, switch, transformer)."
        )
    phases, potentials = element.phases, element.res_potentials.m

    if len(phases) < 2:
        raise ValueError(f"The element {element.id!r} must have at least two phases to plot voltages.")

    if voltage_type == "auto":
        pass
    elif voltage_type == "pn":
        if "n" not in phases:
            raise ValueError("The element must have a neutral to plot phase-to-neutral voltages.")
    elif voltage_type == "pp":
        phases = phases.removesuffix("n")
        n_pp = len(phases)
        if n_pp < 2:
            raise ValueError("The element must have more than one phase to plot phase-to-phase voltages.")
        potentials = potentials[:n_pp]
    else:
        raise ValueError(f"Invalid voltage_type: {voltage_type!r}")
    return element, phases, potentials


def _pu_to_pct[V: (float, list[float])](v: V | None, /) -> V | None:
    """Convert per unit value to percentage."""
    if v is None:
        return None
    elif isinstance(v, list):
        return [val * 100 for val in v]
    else:
        return v * 100


def _pp_num(v: float | list[float] | list[float | None] | None, /, missing: str = "n/a") -> str:
    """Pretty print number(s) or `missing` if `None`."""
    if v is None:
        return missing
    elif isinstance(v, list):
        return "[" + ", ".join(missing if val is None else f"{val:.5g}" for val in v) + "]"
    else:
        return f"{v:.5g}"


def _scalar_if_unique(value: np.ndarray | None):
    # If the value is the same for all phases, return it as a scalar, otherwise, return the array
    if value is None:
        return None
    unique = np.unique(value)
    if unique.size == 1:
        return unique.item()
    return value.tolist()


#
# Phasor plotting functions
#
def plot_voltage_phasors(
    element: AbstractTerminal, *, voltage_type: Literal["pp", "pn", "auto"] = "auto", ax: "Axes | None" = None
) -> "Axes":
    """Plot the voltage phasors of a terminal element or a branch element.

    Args:
        element:
            The bus, load, source, branch side whose voltages to plot.

        voltage_type:
            The type of the voltages to plot.

            - ``"auto"``: Plots the phase-to-neutral voltages if the element has a neutral, otherwise
              the phase-to-phase voltages. This works for all elements and is the default.
            - ``"pp"``: Plots the phase-to-phase voltages. Raises an error if the element has only
              one phase (e.g. "an").
            - ``"pn"``: Plots the phase-to-neutral voltages. Raises an error if the element has no
              neutral.

        ax:
            The axes to plot on. If None, the currently active axes object is used.

    Returns:
        The axes with the plot.
    """
    from roseau.load_flow.utils.optional_deps import pyplot as plt

    if ax is None:
        ax = plt.gca()
    element, phases, potentials = _get_phases_and_potentials(element, voltage_type)
    _configure_axes(ax, potentials)
    ax.set_title(f"{element.id}" if element._side_value is None else f"{element.id} ({element._side_value})")
    potentials = potentials.tolist()
    if "n" in phases:
        origin = potentials[-1]
        for phase, potential in zip(phases[:-1], potentials[:-1], strict=True):
            _draw_voltage_phasor(ax, potential, origin, color=_COLORS[phase])
        for phase, potential in zip(phases, potentials, strict=True):
            ax.scatter(potential.real, potential.imag, color=_COLORS[phase], label=phase)
    elif len(phases) == 2:
        v1, v2 = potentials
        phase = phases
        _draw_voltage_phasor(ax, v1, v2, color=_COLORS[phase])
        for v, ph in ((v1, phase[0]), (v2, phase[1])):
            ax.scatter(v.real, v.imag, color=_COLORS[ph], label=ph)
    else:
        assert phases == "abc"
        va, vb, vc = potentials
        for v1, v2, phase in ((va, vb, "ab"), (vb, vc, "bc"), (vc, va, "ca")):
            _draw_voltage_phasor(ax, v1, v2, color=_COLORS[phase])
        for v, phase in ((va, "a"), (vb, "b"), (vc, "c")):
            ax.scatter(v.real, v.imag, color=_COLORS[phase], label=phase)
    ax.legend()
    return ax


def plot_symmetrical_voltages(
    element: AbstractTerminal, *, axes: Iterable["Axes"] | None = None
) -> "tuple[Axes, Axes, Axes]":
    """Plot the symmetrical voltages of a terminal element or a branch element.

    Args:
        element:
            The bus, load, source, branch side whose voltages to plot. The element must have
            ``'abc'`` or ``'abcn'`` phases.

        axes:
            The three axes to plot on for the symmetrical components in the order zero, positive,
            negative. If None, new axes are created.

    Returns:
        The three axes with the plots of the symmetrical components in the order zero, positive,
        negative.
    """
    from roseau.load_flow.utils.optional_deps import pyplot as plt

    element, phases, potentials = _get_phases_and_potentials(element, "auto")
    if phases not in {"abc", "abcn"}:
        raise ValueError("The element must have 'abc' or 'abcn' phases.")
    if axes is None:
        _, axes = plt.subplots(1, 3)
    ax0, ax1, ax2 = axes  # type: ignore
    sym_components = phasor_to_sym(potentials[:3])
    u0, u1, u2 = sym_components.tolist()
    un = potentials.item(3) if "n" in phases else 0j
    ax_limits = (1.2 * max(abs(sym_components)) * PositiveSequence).ravel()
    title = f"{element.id}" if element._side_value is None else f"{element.id} ({element._side_value})"

    def _draw_balanced_voltages(ax: "Axes", u: "complex", seq: "ComplexArray"):
        seq_potentials = (u * seq).ravel().tolist()
        for phase, v in zip("abc", seq_potentials, strict=False):
            _draw_voltage_phasor(ax, v, 0j, color=_COLORS[phase], annotate=False)
        for phase, v in zip("abc", seq_potentials, strict=False):
            ax.scatter(v.real, v.imag, color=_COLORS[phase], label=phase)

    def _draw_zero_voltages(ax: "Axes", u: "complex", seq: "ComplexArray"):
        _draw_voltage_phasor(ax, u, un, color=_COLORS["a"], annotate=False)
        ax.scatter(u.real, u.imag, color=_COLORS["a"], label="abc")
        if "n" in phases:
            ax.scatter(un.real, un.imag, color=_COLORS["n"], label="n")

    for name, u, ax, seq, draw_func in (
        ("Zero Sequence", u0, ax0, ZeroSequence, _draw_zero_voltages),
        ("Positive Sequence", u1, ax1, PositiveSequence, _draw_balanced_voltages),
        ("Negative Sequence", u2, ax2, NegativeSequence, _draw_balanced_voltages),
    ):
        _configure_axes(ax, ax_limits)
        ax.set_title(f"{title}\n{name}")
        draw_func(ax, u, seq)
        angle = cmath.phase(u)
        ha = "right" if cmath.pi / 2 < abs(angle) < 3 * cmath.pi / 2 else "left"
        va = "bottom" if abs(angle) < cmath.pi else "top"
        xy = u + ax_limits.item(0) / 20 * cmath.exp(1j * angle)  # move it 5% of the axis limits
        ax.annotate(f"{abs(u):.0f}V", (xy.real, xy.imag), ha=ha, va=va)
        ax.legend()

    return ax0, ax1, ax2


#
# Map plotting functions
#
def _check_folium(func_name: str) -> None:
    """Check if the folium library is installed."""
    try:
        import folium  # pyright: ignore # noqa: F401
    except ImportError as e:
        e.add_note(f"The `folium` library is required when using `{func_name}`. Install it with `pip install folium`.")
        raise


def _plot_interactive_map_internal(  # noqa: C901
    network: "ElectricalNetwork | rlfs.ElectricalNetwork",
    dataframes: dict["MapElementType", gpd.GeoDataFrame],
    fields: dict["MapElementType", dict[str, str]],
    style_color_callback: Callable[[str, Id], str],
    highlight_color: str,
    style_function: Callable[["FeatureMap"], "StyleDict | None"] | None,
    highlight_function: Callable[["FeatureMap"], "StyleDict | None"] | None,
    map_kws: Mapping[str, Any] | None,
    add_tooltips: bool,
    add_popups: bool,
    add_search: bool,
    fit_bounds: bool,
) -> "folium.Map":
    import folium
    from folium.plugins import FeatureGroupSubGroup, Search

    def internal_style_function(feature):
        result = style_function(feature) if style_function is not None else None
        if result is not None:
            return result
        # Default style
        e_id, e_type = feature["properties"]["id"], feature["properties"]["element_type"]
        style_color = style_color_callback(e_type, e_id)
        if e_type == "bus":
            vn = nominal_voltages[e_id]
            if e_id in source_buses:
                radius, margin = 15, -1
                border_radius = 0  # Source bus: square
            else:
                if vn < lv:
                    radius, margin = 5, 3  # LV
                elif vn < mv:
                    radius, margin = 10, 1  # MV
                else:
                    radius, margin = 15, -1  # HV
                border_radius = radius / 2
            markup = f"""
            <div style="font-size: 0.8em;">
                <div style="width: {radius}px;
                            height: {radius}px;
                            border-radius: {border_radius}px;
                            background-color: {style_color};
                            margin: {margin}px;
                            ">
                </div>
            </div>
            """
            return {"html": markup}
        elif e_type == "line":
            line = network.lines[e_id]
            line_type = line.parameters._line_type
            vn = nominal_voltages[line.bus1.id]
            if vn < lv:
                weight = 1.5  # LV
            elif vn < mv:
                weight = 3.0  # MV
            else:
                weight = 4.5  # HV
            dash_array = "5, 5" if line_type == LineType.UNDERGROUND else None
            return {"color": style_color, "weight": weight, "dashArray": dash_array}
        elif e_type == "transformer":
            bus_hv_id = feature["properties"]["bus_hv_id"]
            bus_lv_id = feature["properties"]["bus_lv_id"]
            vn = nominal_voltages[bus_hv_id]
            if bus_hv_id in source_buses or bus_lv_id in source_buses:
                radius, margin = 15, -1
            else:
                if vn < lv:
                    radius, margin = 5, 3  # LV
                elif vn < mv:
                    radius, margin = 10, 1  # MV
                else:
                    radius, margin = 15, -1  # HV
            tr_color = style_color
            hv_color = style_color_callback("bus", bus_hv_id)
            lv_color = style_color_callback("bus", bus_lv_id)
            markup = f"""
            <div style="font-size: 0.8em;">
                <div style="width: {radius}px;
                            height: {radius}px;
                            border-top: 2px solid {tr_color};
                            border-bottom: 2px solid {tr_color};
                            background: linear-gradient(to right,
                                                       {hv_color} 0%,
                                                       {hv_color} 40%,
                                                       {tr_color} 41%,
                                                       {tr_color} 59%,
                                                       {lv_color} 60%,
                                                       {lv_color} 100%);
                            margin: {margin}px;
                            ">
                </div>

            </div>
            """
            return {"html": markup}
        else:
            return {"color": style_color, "weight": 2}

    def internal_highlight_function(feature):
        result = highlight_function(feature) if highlight_function is not None else None
        if result is not None:
            return result
        # Default highlight style
        e_type = feature["properties"]["element_type"]
        if e_type == "bus":  # noqa: SIM116
            return {"color": highlight_color, "fillColor": highlight_color}
        elif e_type == "line":
            return {"color": highlight_color}
        elif e_type == "transformer":
            return {"color": highlight_color, "fillColor": highlight_color}
        else:
            return {"color": highlight_color}

    source_buses = {src.bus.id for src in network.sources.values()}
    transformer_buses = {side.bus.id for tr in network.transformers.values() for side in (tr.side_hv, tr.side_lv)}
    nominal_voltages = network._get_nominal_voltages()
    mv, lv = 60e3, 1e3

    # Filter out transformer buses, these are represented by the transformers themselves
    dataframes["bus"] = dataframes["bus"].loc[~dataframes["bus"]["id"].isin(transformer_buses)]

    tooltips: dict[MapElementType, folium.GeoJsonTooltip | None] = {}
    if add_tooltips:
        for e_type, e_fields in fields.items():
            tooltips[e_type] = folium.GeoJsonTooltip(
                fields=list(e_fields.keys()),
                aliases=list(e_fields.values()),
                localize=True,
                sticky=False,
                labels=True,
                max_width=800,
            )
    else:
        tooltips = dict.fromkeys(fields.keys(), None)
    popups: dict[MapElementType, folium.GeoJsonPopup | None] = {}
    if add_popups:
        for e_type, e_fields in fields.items():
            popups[e_type] = folium.GeoJsonPopup(
                fields=list(e_fields.keys()),
                aliases=list(e_fields.values()),
                localize=True,
                labels=True,
            )
    else:
        popups = dict.fromkeys(fields.keys(), None)

    map_kws = dict(map_kws) if map_kws is not None else {}

    # Calculate the center and zoom level of the map if not provided
    if not fit_bounds and ("location" not in map_kws or "zoom_start" not in map_kws):
        geom_union = dataframes["bus"].union_all().union(dataframes["line"].union_all())
        if "location" not in map_kws:
            map_kws["location"] = list(reversed(geom_union.centroid.coords[0]))
        if "zoom_start" not in map_kws:
            # Calculate the zoom level based on the bounding box of the network
            min_x, min_y, max_x, max_y = geom_union.bounds
            # The bounding box could be a point, a vertical line or a horizontal line. In these
            # cases, we set a default zoom level of 16.
            zoom_lon = math.ceil(math.log2(360 * 2.0 / (max_x - min_x))) if max_x > min_x else 16
            zoom_lat = math.ceil(math.log2(360 * 2.0 / (max_y - min_y))) if max_y > min_y else 16
            map_kws["zoom_start"] = min(zoom_lon, zoom_lat) - 1

    if "zoom_control" not in map_kws and add_search:
        map_kws["zoom_control"] = "topright"

    m = folium.Map(**map_kws)
    network_layer = folium.FeatureGroup(name="Electrical Network").add_to(m)
    names = {"bus": "Buses", "line": "Lines", "transformer": "Transformers"}
    for e_type, frame in dataframes.items():
        if frame.empty:
            continue
        marker = folium.Marker(icon=folium.DivIcon()) if e_type != "line" else None
        name = names[e_type]
        folium.GeoJson(
            data=frame,
            name=name,
            marker=marker,
            style_function=internal_style_function,
            highlight_function=internal_highlight_function,
            tooltip=tooltips[e_type],
            popup=popups[e_type],
        ).add_to(FeatureGroupSubGroup(network_layer, name).add_to(m))
    folium.LayerControl(
        collapsed=False,
        draggable=True,
        position="bottomright",
    ).add_to(m)
    if add_search:
        Search(network_layer, search_label="id", placeholder="Search network elements...").add_to(m)
    if fit_bounds:
        folium.FitOverlays(padding=30).add_to(m)
    return m


def plot_interactive_map(
    network: ElectricalNetwork,
    *,
    style_color: str = "#234e83",
    highlight_color: str = "#cad40e",
    style_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    highlight_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    map_kws: Mapping[str, Any] | None = None,
    add_tooltips: bool = True,
    add_popups: bool = True,
    add_search: bool = True,
    fit_bounds: bool = True,
) -> "folium.Map":
    """Plot an electrical network on an interactive map.

    This function uses the `folium` library to create an interactive map of the electrical network.

    Make sure you have defined the geometry of the buses and lines in the network before using this
    function. You can do this by setting the `geometry` attribute of the buses and lines.
    Transformers use the geometry of their HV buses.

    Args:
        network:
            The electrical network to plot. Buses, lines and transformers are plotted. Buses of
            source elements are represented with bigger square markers.

        style_color:
            The color of the default style of an element. Defaults to :roseau-primary:`■ #234e83`.

        highlight_color:
            The color of the default style when an element is highlighted. Defaults to
            :roseau-secondary:`■ #cad40e`.

        style_function:
            Function mapping a GeoJson Feature to a style dict. If not provided or when it returns
            ``None``, the default style is used.

        highlight_function:
            Function mapping a GeoJson Feature to a style dict for mouse events. If not provided or
            when it returns ``None``, the default highlight style is used.

        map_kws:
            Additional keyword arguments to pass to the :class:`folium.Map` constructor. By default,
            if ``fit_bounds`` is false, `location` is set to the centroid of the network geometry
            and `zoom_start` is calculated based on its bounding box.

        add_tooltips:
            If ``True`` (default), tooltips will be added to the map elements. Tooltips appear when
            hovering over an element.

        add_popups:
            If ``True`` (default), popups will be added to the map elements. Popups appear when
            clicking on an element.

        add_search:
            If ``True`` (default), a search bar will be added to the map to search for network
            elements by their ID.

        fit_bounds:
            If ``True`` (default), the map view will be adjusted to fit all network elements. If
            ``False``, the initial view is determined by the `location` and `zoom_start` parameters
            in `map_kws`.

    Returns:
        The :class:`folium.Map` object with the network plot.
    """
    _check_folium(func_name="plot_interactive_map")
    if not network.is_multi_phase:
        raise TypeError(
            "Only multi-phase networks can be plotted. Did you mean to use rlfs.plotting.plot_interactive_map?"
        )

    buses_gdf = network.buses_frame
    buses_gdf.reset_index(inplace=True)
    buses_gdf["element_type"] = "bus"
    buses_gdf["min_voltage_level"] *= 100  # Convert to percentage
    buses_gdf["max_voltage_level"] *= 100  # Convert to percentage

    lines_gdf = network.lines_frame
    lines_gdf.reset_index(inplace=True)
    lines_gdf["element_type"] = "line"
    lines_gdf["max_loading"] *= 100  # Convert to percentage
    lines_gdf[["ampacity", "section", "line_type", "material", "insulator"]] = None
    line_params = {}
    for idx in lines_gdf.index:
        line_id: Id = lines_gdf.at[idx, "id"]  # type: ignore
        lp = network.lines[line_id].parameters
        if lp.id not in line_params:
            line_params[lp.id] = {
                "ampacity": _scalar_if_unique(lp._ampacities),
                "section": _scalar_if_unique(lp._sections),
                "line_type": lp._line_type,
                "material": _scalar_if_unique(lp._materials),
                "insulator": _scalar_if_unique(lp._insulators),
            }
        lines_gdf.at[idx, "ampacity"] = line_params[lp.id]["ampacity"]
        lines_gdf.at[idx, "section"] = line_params[lp.id]["section"]
        lines_gdf.at[idx, "line_type"] = line_params[lp.id]["line_type"]
        lines_gdf.at[idx, "material"] = line_params[lp.id]["material"]
        lines_gdf.at[idx, "insulator"] = line_params[lp.id]["insulator"]

    transformers_gdf = network.transformers_frame
    transformers_gdf.reset_index(inplace=True)
    transformers_gdf["element_type"] = "transformer"
    transformers_gdf["tap"] *= 100  # Convert to percentage
    transformers_gdf[["hv_side", "lv_side"]] = ""
    transformers_gdf[["vg", "sn", "uhv", "ulv"]] = None
    for idx in transformers_gdf.index:
        tr_id: Id = transformers_gdf.at[idx, "id"]  # type: ignore
        # Replace geometry with that of the HV bus
        bus_hv_id: Id = transformers_gdf.at[idx, "bus_hv_id"]  # type: ignore
        transformers_gdf.at[idx, "geometry"] = network.buses[bus_hv_id].geometry  # type: ignore
        lp = network.transformers[tr_id].parameters
        transformers_gdf.at[idx, "vg"] = lp.vg
        transformers_gdf.at[idx, "sn"] = lp._sn / 1e3  # Convert to kVA
        transformers_gdf.at[idx, "uhv"] = lp._uhv
        transformers_gdf.at[idx, "ulv"] = lp._ulv

    m = _plot_interactive_map_internal(
        network=network,
        dataframes={"bus": buses_gdf, "line": lines_gdf, "transformer": transformers_gdf},
        fields={
            "bus": {
                "id": "Id:",
                "phases": "Phases:",
                "nominal_voltage": "Un (V):",
                "min_voltage_level": "Umin (%):",
                "max_voltage_level": "Umax (%):",
            },
            "line": {
                "id": "Id:",
                "phases": "Phases:",
                "bus1_id": "Bus1:",
                "bus2_id": "Bus2:",
                "parameters_id": "Parameters:",
                "length": "Length (km):",
                "line_type": "Line Type:",
                "material": "Material:",
                "insulator": "Insulator:",
                "section": "Section (mm²):",
                "ampacity": "Ampacity (A):",
                "max_loading": "Max loading (%):",
            },
            "transformer": {
                "id": "Id:",
                "vg": "Vector Group:",
                "sn": "Sn (kVA):",
                "tap": "Tap Position (%):",
                "parameters_id": "Parameters:",
                "max_loading": "Max loading (%):",
                "hv_side": "HV Side",
                "bus_hv_id": "» Bus:",
                "phases_hv": "» Phases:",
                "uhv": "» Ur (V):",
                "lv_side": "LV Side",
                "bus_lv_id": "» Bus:",
                "phases_lv": "» Phases:",
                "ulv": "» Ur (V):",
            },
        },
        style_color_callback=lambda et, id: "#000000" if et == "transformer" else style_color,
        highlight_color=highlight_color,
        style_function=style_function,
        highlight_function=highlight_function,
        map_kws=map_kws,
        add_tooltips=add_tooltips,
        add_popups=add_popups,
        add_search=add_search,
        fit_bounds=fit_bounds,
    )
    return m


def plot_results_interactive_map(
    network: ElectricalNetwork,
    *,
    style_color: str = "#234e83",
    highlight_color: str = "#cad40e",
    style_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    highlight_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    map_kws: Mapping[str, Any] | None = None,
    add_tooltips: bool = True,
    add_popups: bool = True,
    add_search: bool = True,
    fit_bounds: bool = True,
) -> "folium.Map":
    """Plot an electrical network on an interactive map with the load flow results.

    This function uses the `folium` library to create an interactive map of the electrical network
    with buses colored according to their voltage levels and lines/transformers colored according to
    their loadings.

    Make sure you have defined the geometry of the buses and lines in the network before using this
    function. You can do this by setting the `geometry` attribute of the buses and lines.
    Transformers use the geometry of their HV buses. Also, ensure that the network has valid results
    by running a load flow calculation before plotting.

    Args:
        network:
            The electrical network to plot. Buses, lines and transformers are plotted. Buses of
            source elements are represented with bigger square markers.

        style_color:
            The color of the default style of an element. Defaults to :roseau-primary:`■ #234e83`.

        highlight_color:
            The color of the default style when an element is highlighted. Defaults to
            :roseau-secondary:`■ #cad40e`.

        style_function:
            Function mapping a GeoJson Feature to a style dict. If not provided or when it returns
            ``None``, the default style is used. The default style colors of buses depend on their
            voltage levels:
            - blue: `U` below `Umin`
            - cyan: `U` close to `Umin`; specifically, `Umin ≤ U < 0.75 * Umin + 0.25`
            - green: `U` within `Umin` and `Umax` and not close to the limits
            - orange: `U` close to `Umax`; specifically, `0.75 * Umax + 0.25 < U ≤ Umax`
            - red: `U` above `Umax`

            The default style colors of lines and transformers depend on their loadings:
            - green: below 75% of the maximum loading
            - orange: between 75% and 100% of the maximum loading
            - red: above 100% of the maximum loading

        highlight_function:
            Function mapping a GeoJson Feature to a style dict for mouse events. If not provided or
            when it returns ``None``, the default highlight style is used.

        map_kws:
            Additional keyword arguments to pass to the :class:`folium.Map` constructor. By default,
            if ``fit_bounds`` is false, `location` is set to the centroid of the network geometry
            and `zoom_start` is calculated based on its bounding box.

        add_tooltips:
            If ``True`` (default), tooltips will be added to the map elements. Tooltips appear when
            hovering over an element.

        add_popups:
            If ``True`` (default), popups will be added to the map elements. Popups appear when
            clicking on an element.

        add_search:
            If ``True`` (default), a search bar will be added to the map to search for network
            elements by their ID.

        fit_bounds:
            If ``True`` (default), the map view will be adjusted to fit all network elements. If
            ``False``, the initial view is determined by the `location` and `zoom_start` parameters
            in `map_kws`.

    Returns:
        The `folium.Map` object with the network plot.
    """
    _check_folium(func_name="plot_results_interactive_map")

    if not network.is_multi_phase:
        raise TypeError(
            "Only multi-phase networks can be plotted. Did you mean to use rlfs.plotting.plot_results_interactive_map?"
        )
    network._check_valid_results()

    buses_data: dict[str, list[Any]] = {
        "id": [],
        "phases": [],
        "element_type": [],
        "nominal_voltage": [],
        "min_voltage_level": [],
        "max_voltage_level": [],
        "geometry": [],
        "res_separator": [],
        "res_voltage": [],
        "res_voltage_level": [],
    }
    buses_ids: list[Id] = []
    for bus in network.buses.values():
        buses_ids.append(bus.id)
        buses_data["id"].append(bus.id)
        buses_data["phases"].append(bus.phases)
        buses_data["element_type"].append("bus")
        buses_data["nominal_voltage"].append(bus._nominal_voltage)
        buses_data["min_voltage_level"].append(_pu_to_pct(bus._min_voltage_level))
        buses_data["max_voltage_level"].append(_pu_to_pct(bus._max_voltage_level))
        buses_data["geometry"].append(bus.geometry)
        buses_data["res_separator"].append("")  # Results separator
        buses_data["res_voltage"].append(_pp_num([abs(v) for v in bus._res_voltages_getter(warning=False).tolist()]))
        buses_data["res_voltage_level"].append(
            _pp_num(
                _pu_to_pct(
                    v_levels.tolist()
                    if (v_levels := bus._res_voltage_levels_getter(warning=False)) is not None
                    else None
                )
            )
        )

    lines_data: dict[str, list[Any]] = {
        "id": [],
        "phases": [],
        "element_type": [],
        "bus1_id": [],
        "bus2_id": [],
        "parameters_id": [],
        "length": [],
        "line_type": [],
        "material": [],
        "insulator": [],
        "section": [],
        "ampacity": [],
        "geometry": [],
        "res_separator": [],  # Results separator
        "max_loading": [],
        "res_loading": [],
    }
    for line in network.lines.values():
        lines_data["id"].append(line.id)
        lines_data["phases"].append(line.phases)
        lines_data["element_type"].append("line")
        lines_data["bus1_id"].append(line.bus1.id)
        lines_data["bus2_id"].append(line.bus2.id)
        lines_data["parameters_id"].append(line._parameters.id)
        lines_data["length"].append(line._length)
        lines_data["line_type"].append(line._parameters._line_type)
        lines_data["material"].append(_scalar_if_unique(line._parameters._materials))
        lines_data["insulator"].append(_scalar_if_unique(line._parameters._insulators))
        lines_data["section"].append(_scalar_if_unique(line._parameters._sections))
        lines_data["ampacity"].append(_scalar_if_unique(line._parameters._ampacities))
        lines_data["geometry"].append(line.geometry)
        lines_data["res_separator"].append("")  # Results separator
        lines_data["max_loading"].append(line._max_loading * 100)
        lines_data["res_loading"].append(
            _pp_num(
                _pu_to_pct(
                    loading.tolist() if (loading := line._res_loading_getter(warning=False)) is not None else None
                )
            )
        )

    def _get_tr_buses_data(tr: Transformer, field: str) -> str:
        return _pp_num([buses_data[field][buses_ids.index(bus_id)] for bus_id in (tr.bus_hv.id, tr.bus_lv.id)])

    transformers_data: dict[str, list[Any]] = {
        "id": [],
        "phases": [],
        "element_type": [],
        "bus_hv_id": [],
        "bus_lv_id": [],
        "parameters_id": [],
        "geometry": [],
        "vg": [],
        "sn": [],
        "tap": [],
        "rated_voltages": [],
        "max_loading": [],
        "nominal_voltages": [],
        "min_voltage_levels": [],
        "max_voltage_levels": [],
        "res_separator": [],
        "res_loading": [],
        "res_voltage_hv": [],
        "res_voltage_lv": [],
        "res_voltage_level_hv": [],
        "res_voltage_level_lv": [],
    }
    for tr in network.transformers.values():
        transformers_data["id"].append(tr.id)
        transformers_data["phases"].append(f"[{tr.phases_hv}, {tr.phases_lv}]")
        transformers_data["element_type"].append("transformer")
        transformers_data["bus_hv_id"].append(tr.bus_hv.id)
        transformers_data["bus_lv_id"].append(tr.bus_lv.id)
        transformers_data["parameters_id"].append(tr._parameters.id)
        transformers_data["geometry"].append(tr.bus_hv.geometry)
        transformers_data["vg"].append(tr._parameters.vg)
        transformers_data["sn"].append(tr._parameters._sn / 1e3)  # Convert to kVA
        transformers_data["tap"].append(tr._tap * 100)  # Convert to percentage
        transformers_data["rated_voltages"].append(_pp_num([tr._parameters._uhv, tr._parameters._ulv]))
        transformers_data["max_loading"].append(tr._max_loading * 100)
        transformers_data["nominal_voltages"].append(_get_tr_buses_data(tr, "nominal_voltage"))
        transformers_data["min_voltage_levels"].append(_get_tr_buses_data(tr, "min_voltage_level"))
        transformers_data["max_voltage_levels"].append(_get_tr_buses_data(tr, "max_voltage_level"))
        transformers_data["res_separator"].append("")  # Results separator
        transformers_data["res_loading"].append(tr._res_loading_getter(warning=False) * 100)
        bus_hv_idx = buses_ids.index(tr.bus_hv.id)
        bus_lv_idx = buses_ids.index(tr.bus_lv.id)
        transformers_data["res_voltage_hv"].append(buses_data["res_voltage"][bus_hv_idx])
        transformers_data["res_voltage_lv"].append(buses_data["res_voltage"][bus_lv_idx])
        transformers_data["res_voltage_level_hv"].append(buses_data["res_voltage_level"][bus_hv_idx])
        transformers_data["res_voltage_level_lv"].append(buses_data["res_voltage_level"][bus_lv_idx])

    buses_gdf = gpd.GeoDataFrame(buses_data, crs=network.crs)
    lines_gdf = gpd.GeoDataFrame(lines_data, crs=network.crs)
    transformers_gdf = gpd.GeoDataFrame(transformers_data, crs=network.crs)

    def style_color_callback(et, eid):
        if et == "bus":
            return _RESULT_COLORS[network.buses[eid]._res_state_getter()]
        elif et == "line":
            return _RESULT_COLORS[network.lines[eid]._res_state_getter()]
        elif et == "transformer":
            return _RESULT_COLORS[network.transformers[eid]._res_state_getter()]
        else:
            return style_color

    m = _plot_interactive_map_internal(
        network=network,
        dataframes={"bus": buses_gdf, "line": lines_gdf, "transformer": transformers_gdf},
        fields={
            "bus": {
                "id": "Id:",
                "phases": "Phases:",
                "nominal_voltage": "Un (V):",
                "min_voltage_level": "Umin (%):",
                "max_voltage_level": "Umax (%):",
                "res_separator": "--",
                "res_voltage": "U (V):",
                "res_voltage_level": "U (%):",
            },
            "line": {
                "id": "Id:",
                "phases": "Phases:",
                "bus1_id": "Bus1:",
                "bus2_id": "Bus2:",
                "parameters_id": "Parameters:",
                "length": "Length (km):",
                "line_type": "Line Type:",
                "material": "Material:",
                "insulator": "Insulator:",
                "section": "Section (mm²):",
                "ampacity": "Ampacity (A):",
                "max_loading": "Max loading (%):",
                "res_separator": "--",
                "res_loading": "Loading (%):",
            },
            "transformer": {
                "id": "Id:",
                "bus_hv_id": "HV Bus:",
                "bus_lv_id": "LV Bus:",
                "phases": "Bus phases [ʜv,ʟv]:",
                "vg": "Vector Group:",
                "sn": "Sn (kVA):",
                "rated_voltages": "Ur [ʜv,ʟv] (V):",
                "tap": "Tap Position (%):",
                "parameters_id": "Parameters:",
                "max_loading": "Max loading (%):",
                "nominal_voltages": "Un [ʜv,ʟv] (V):",
                "min_voltage_levels": "Umin [ʜv,ʟv] (%):",
                "max_voltage_levels": "Umax [ʜv,ʟv] (%):",
                "res_separator": "--",
                "res_loading": "Loading (%):",
                "res_voltage_hv": "Uʜv (V):",
                "res_voltage_lv": "Uʟv (V):",
                "res_voltage_level_hv": "Uʜv (%):",
                "res_voltage_level_lv": "Uʟv (%):",
            },
        },
        style_color_callback=style_color_callback,
        highlight_color=highlight_color,
        style_function=style_function,
        highlight_function=highlight_function,
        map_kws=map_kws,
        add_tooltips=add_tooltips,
        add_popups=add_popups,
        add_search=add_search,
        fit_bounds=fit_bounds,
    )
    return m


#
# Voltage profile plotting functions
#
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _VoltageProfile[NetT: ElectricalNetwork | rlfs.ElectricalNetwork, ModeT: Literal["min", "max", ""]]:
    network: NetT
    mode: ModeT
    starting_bus_id: Id
    traverse_transformers: bool
    switch_length: float
    distance_unit: str
    colors: dict[ResultState, str] = dataclasses.field(repr=False)
    buses: dict[Id, "VoltageProfileNode"] = dataclasses.field(repr=False)
    lines: dict[Id, "VoltageProfileEdge"] = dataclasses.field(repr=False)
    transformers: dict[Id, "VoltageProfileEdge"] = dataclasses.field(repr=False)
    switches: dict[Id, "VoltageProfileEdge"] = dataclasses.field(repr=False)

    @classmethod
    def _from_network(
        cls,
        network: NetT,
        mode: ModeT,
        *,
        starting_bus_id: Id | None = None,
        traverse_transformers: bool = False,
        switch_length: float | None = None,
        distance_unit: str = "km",
    ) -> Self:
        network._check_valid_results()

        if starting_bus_id is None:
            starting_bus_id = network._get_starting_bus_id()
        elif starting_bus_id not in network.buses:
            raise ValueError(f"Bus {starting_bus_id!r} not found in the network.")

        try:
            distance_factor = Q_(1.0, units="km").m_as(distance_unit)
        except PintError as e:
            raise ValueError(f"Invalid distance unit: {distance_unit}") from e

        if switch_length is None:
            min_line_length = min((line._length for line in network.lines.values()), default=math.inf)
            switch_length = min(2e-3, min_line_length)
        elif switch_length < 0:
            raise ValueError("switch_length must be non-negative.")

        distances = network._shortest_paths(
            starting_bus_id,
            weight=lambda et, eid: (
                network.lines[eid]._length
                if et == "line"
                else (0.0 if traverse_transformers else None)
                if et == "transformer"
                else (switch_length if network.switches[eid].closed else None)
            ),
        )

        buses: dict[Id, VoltageProfileNode] = {}
        lines: dict[Id, VoltageProfileEdge] = {}
        transformers: dict[Id, VoltageProfileEdge] = {}
        switches: dict[Id, VoltageProfileEdge] = {}
        for bus_id, distance in distances.items():
            buses[bus_id] = cls._handle_bus(network.buses[bus_id], distance=distance * distance_factor, mode=mode)
        for line in network.lines.values():
            if not traverse_transformers and line.bus1.id not in distances:
                continue
            lines[line.id] = cls._handle_line(line)
        if traverse_transformers:
            for tr in network.transformers.values():
                transformers[tr.id] = cls._handle_transformer(tr)
                buses[tr.bus_hv.id]["is_tr_bus"] = True
                buses[tr.bus_lv.id]["is_tr_bus"] = True
        for switch in network.switches.values():
            if not switch.closed or (not traverse_transformers and switch.bus1.id not in distances):
                continue
            switches[switch.id] = cls._handle_switch(switch)

        return cls(
            network=network,
            mode=mode,
            starting_bus_id=starting_bus_id,
            traverse_transformers=traverse_transformers,
            switch_length=switch_length,
            distance_unit=distance_unit,
            buses=buses,
            lines=lines,
            transformers=transformers,
            switches=switches,
            colors=_RESULT_COLORS,
        )

    @classmethod
    def _handle_bus(cls, bus: "Bus | rlfs.Bus", distance: float, mode: ModeT) -> "VoltageProfileNode":
        if bus._nominal_voltage is None:
            raise ValueError(
                f"The voltage profile requires buses to have their nominal voltage defined. "
                f"Bus {bus.id!r} has no nominal voltage."
            )
        if isinstance(bus, Bus):
            voltages = bus._res_voltage_levels_getter(warning=False)
            assert voltages is not None
            voltages = voltages.tolist()
            voltage = {"min": min(voltages), "max": max(voltages)}[mode]
        else:
            voltages = None
            voltage = bus._res_voltage_level_getter(warning=False)
            assert voltage is not None

        return {
            "distance": distance,
            "voltage": voltage * 100,
            "voltages": _pu_to_pct(voltages),
            "min_voltage": _pu_to_pct(bus._min_voltage_level),
            "max_voltage": _pu_to_pct(bus._max_voltage_level),
            "state": bus._res_state_getter(),
            "is_tr_bus": False,  # Will be updated later if needed
        }

    @classmethod
    def _handle_line(cls, line: "Line | rlfs.Line") -> "VoltageProfileEdge":
        if isinstance(line, Line):
            loadings = line._res_loading_getter(warning=False)
            loading = None
            if loadings is not None:
                loadings = loadings.tolist()
                loading = max(loadings)
        else:
            loadings = None
            loading = line._res_loading_getter(warning=False)
        return {
            "from_bus": line.bus1.id,
            "to_bus": line.bus2.id,
            "loading": _pu_to_pct(loading),
            "loadings": _pu_to_pct(loadings),
            "max_loading": line._max_loading * 100,
            "state": line._res_state_getter(),
        }

    @classmethod
    def _handle_transformer(cls, tr: "Transformer | rlfs.Transformer") -> "VoltageProfileEdge":
        return {
            "from_bus": tr.bus_hv.id,
            "to_bus": tr.bus_lv.id,
            "loading": tr._res_loading_getter(warning=False) * 100,
            "loadings": None,
            "max_loading": tr._max_loading * 100,
            "state": tr._res_state_getter(),
        }

    @classmethod
    def _handle_switch(cls, switch: "Switch | rlfs.Switch") -> "VoltageProfileEdge":
        return {
            "from_bus": switch.bus1.id,
            "to_bus": switch.bus2.id,
            "loading": None,
            "loadings": None,
            "max_loading": 100.0,
            "state": "unknown",
        }

    @property
    def _title(self) -> str:
        title = f"Voltage Profile Starting at Bus {self.starting_bus_id!r}"
        if self.mode:
            title = f"{self.mode.capitalize()} {title}"
        return title

    @property
    def _xlabel(self) -> str:
        return f"Distance ({self.distance_unit})"

    @property
    def _ylabel(self) -> str:
        label = "Voltage (%)"
        if self.mode:
            label = f"{self.mode.capitalize()} {label}"
        return label

    def _edge_segs(self, edge: "VoltageProfileEdge") -> tuple[tuple[float, float], tuple[float, float]]:
        """Get the segments for an edge in the form ((x1, y1), (x2, y2))."""
        return (
            (self.buses[edge["from_bus"]]["distance"], self.buses[edge["from_bus"]]["voltage"]),
            (self.buses[edge["to_bus"]]["distance"], self.buses[edge["to_bus"]]["voltage"]),
        )

    def _edge_xs(self, edge: "VoltageProfileEdge") -> tuple[float, float]:
        """Get the x coordinates for an edge in the form (x1, x2)."""
        return (self.buses[edge["from_bus"]]["distance"], self.buses[edge["to_bus"]]["distance"])

    def _edge_ys(self, edge: "VoltageProfileEdge") -> tuple[float, float]:
        """Get the y coordinates for an edge in the form (y1, y2)."""
        return (self.buses[edge["from_bus"]]["voltage"], self.buses[edge["to_bus"]]["voltage"])

    # Public API
    # ----------
    def plot_matplotlib(self, *, ax: "Axes | None" = None) -> "Axes":
        """Plot the network voltage profile using Matplotlib.

        Args:
            ax:
                The axes to plot on. If None, the current axes will be used.

        Returns:
            The Matplotlib Axes with the voltage profile plot.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError as e:
            e.add_note("matplotlib is required for plotting the voltage profile using plot_matplotlib.")
            raise
        from matplotlib.collections import LineCollection
        from matplotlib.markers import MarkerStyle
        from matplotlib.patheffects import Normal, Stroke

        if ax is None:
            ax = plt.gca()

        ax.add_collection(
            LineCollection(
                segments=[self._edge_segs(ln) for ln in self.lines.values()],
                colors=[self.colors[ln["state"]] for ln in self.lines.values()],
                zorder=2,
            )
        )

        if self.transformers:
            ax.add_collection(
                LineCollection(
                    segments=[self._edge_segs(tr) for tr in self.transformers.values()],
                    colors=[self.colors[tr["state"]] for tr in self.transformers.values()],
                    linewidths=3,
                    zorder=3,
                    path_effects=[Stroke(linewidth=6, foreground="k"), Normal()],
                )
            )

        if self.switches:
            ax.add_collection(
                LineCollection(
                    segments=[self._edge_segs(sw) for sw in self.switches.values()],
                    colors=[self.colors[sw["state"]] for sw in self.switches.values()],
                    linestyles="dashed",
                    linewidths=3,
                    zorder=3,
                )
            )

        bus_pc = ax.scatter(
            x=[bus["distance"] for bus in self.buses.values()],
            y=[bus["voltage"] for bus in self.buses.values()],
            c=[self.colors[bus["state"]] for bus in self.buses.values()],
            s=10,
            zorder=4,
        )
        if self.traverse_transformers:
            # ax.scatter does not support per-point marker styles, so we set them manually
            bus_pc.set_paths(
                [
                    (m := MarkerStyle("s" if bus["is_tr_bus"] else "o")).get_path().transformed(m.get_transform())
                    for bus in self.buses.values()
                ]
            )

        ax.set_title(self._title, fontsize=10)
        ax.set_xlabel(self._xlabel)
        ax.set_ylabel(self._ylabel)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(alpha=0.25)
        return ax

    def plot_plotly(self) -> "go.Figure":
        """Plot the network voltage profile using Plotly.

        Returns:
            A Plotly Figure with the voltage profile plot.
        """
        try:
            import plotly.graph_objects as go
        except ImportError as e:
            e.add_note("plotly is required for plotting the voltage profile using plot_plotly.")
            raise

        traces: list[go.Scatter] = []

        # Buses
        voltage_key = "voltages" if self.network.is_multi_phase else "voltage"
        buses_trace = go.Scatter(
            x=[bus["distance"] for bus in self.buses.values()],
            y=[bus["voltage"] for bus in self.buses.values()],
            mode="markers",
            marker={
                "color": [self.colors[bus["state"]] for bus in self.buses.values()],
                "symbol": (
                    ["square" if bus["is_tr_bus"] else "circle" for bus in self.buses.values()]
                    if self.traverse_transformers
                    else "circle"
                ),
                "size": 6,
            },
            customdata=[  # used in hovers
                (bus_id, _pp_num(bus[voltage_key]), _pp_num(bus["min_voltage"]), _pp_num(bus["max_voltage"]))
                for bus_id, bus in self.buses.items()
            ],
            hovertemplate=(
                "Bus: %{customdata[0]}"
                "<br>Voltage (%): %{customdata[1]}"
                "<br>Voltage limits (%): [%{customdata[2]}, %{customdata[3]}]"
                "<extra></extra>"
            ),
            zorder=3,
        )
        traces.append(buses_trace)

        # Transformers
        if self.transformers:
            # Black borders for transformers
            traces.append(
                go.Scatter(
                    x=[x for tr in self.transformers.values() for x in (*self._edge_xs(tr), None)],
                    y=[y for tr in self.transformers.values() for y in (*self._edge_ys(tr), None)],
                    mode="lines",
                    line={"color": "black", "width": 6},
                    zorder=2,
                    hoverinfo="skip",
                )
            )
            # Traces for transformers (grouped by color for better performance)
            tr_traces: dict[ResultState, dict[str, list[float | None]]] = {
                state: {"x": [], "y": []} for state in ("normal", "high", "very-high")
            }
            for tr in self.transformers.values():
                tr_traces[tr["state"]]["x"].extend((*self._edge_xs(tr), None))
                tr_traces[tr["state"]]["y"].extend((*self._edge_ys(tr), None))
            traces.extend(
                go.Scatter(
                    x=t["x"],
                    y=t["y"],
                    mode="lines",
                    line={"color": self.colors[s], "width": 3},
                    zorder=2,
                    hoverinfo="skip",
                )
                for s, t in tr_traces.items()
                if t["x"]  # skip empty colors
            )
            # Cannot hover on line traces, add invisible midpoint markers to show hover info
            # https://github.com/plotly/plotly.js/issues/1960
            traces.append(
                go.Scatter(
                    x=[sum(self._edge_xs(tr)) / 2 for tr in self.transformers.values()],
                    y=[sum(self._edge_ys(tr)) / 2 for tr in self.transformers.values()],
                    mode="markers",
                    marker={"opacity": 0, "color": [self.colors[tr["state"]] for tr in self.transformers.values()]},
                    customdata=[(tr_id, tr["loading"], tr["max_loading"]) for tr_id, tr in self.transformers.items()],
                    hovertemplate=(
                        # For parallel transformers, only the last one might be shown in hover
                        # https://github.com/plotly/plotly.py/issues/2476
                        "Transformer: %{customdata[0]}"
                        "<br>Loading (%): %{customdata[1]:.5g}"
                        "<br>Loading limit (%): %{customdata[2]:.5g}"
                        "<extra></extra>"
                    ),
                )
            )

        # Lines
        lines_traces: dict[ResultState, dict[str, list[float | None]]] = {
            state: {"x": [], "y": []} for state in ("normal", "high", "very-high", "unknown")
        }
        loading_key = "loadings" if self.network.is_multi_phase else "loading"
        for line in self.lines.values():
            lines_traces[line["state"]]["x"].extend((*self._edge_xs(line), None))
            lines_traces[line["state"]]["y"].extend((*self._edge_ys(line), None))
        # Traces for lines (grouped by color for better performance)
        traces.extend(
            go.Scatter(
                x=t["x"],
                y=t["y"],
                mode="lines",
                line={"color": self.colors[s], "width": 1.5},
                zorder=1,
                hoverinfo="skip",
            )
            for s, t in lines_traces.items()
            if t["x"]  # skip empty colors
        )
        # Cannot hover on line traces, add invisible midpoint markers to show hover info
        # https://github.com/plotly/plotly.js/issues/1960
        traces.append(
            go.Scatter(
                x=[sum(self._edge_xs(line)) / 2 for line in self.lines.values()],
                y=[sum(self._edge_ys(line)) / 2 for line in self.lines.values()],
                mode="markers",
                marker={"opacity": 0, "color": [self.colors[ln["state"]] for ln in self.lines.values()]},
                customdata=[
                    (ln_id, _pp_num(ln[loading_key]), _pp_num(ln["max_loading"])) for ln_id, ln in self.lines.items()
                ],
                hovertemplate=(
                    "Line: %{customdata[0]}"
                    "<br>Loading (%): %{customdata[1]}"
                    "<br>Loading limit (%): %{customdata[2]}"
                    "<extra></extra>"
                ),
            )
        )

        # Switches
        if self.switches:
            sw_traces: dict[ResultState, dict[str, list[float | None]]] = {
                state: {"x": [], "y": []} for state in ("normal", "high", "very-high", "unknown")
            }
            for sw in self.switches.values():
                sw_traces[sw["state"]]["x"].extend((*self._edge_xs(sw), None))
                sw_traces[sw["state"]]["y"].extend((*self._edge_ys(sw), None))
            # Traces for switches (grouped by color for better performance)
            traces.extend(
                go.Scatter(
                    x=t["x"],
                    y=t["y"],
                    mode="lines",
                    line={"color": self.colors[s], "width": 5, "dash": "dash"},
                    zorder=2,
                    hoverinfo="skip",
                )
                for s, t in sw_traces.items()
                if t["x"]  # skip empty colors
            )
            # Cannot hover on line traces, add invisible midpoint markers to show hover info
            # https://github.com/plotly/plotly.js/issues/1960
            traces.append(
                go.Scatter(
                    x=[sum(self._edge_xs(sw)) / 2 for sw in self.switches.values()],
                    y=[sum(self._edge_ys(sw)) / 2 for sw in self.switches.values()],
                    mode="markers",
                    marker={"opacity": 0, "color": [self.colors[sw["state"]] for sw in self.switches.values()]},
                    customdata=list(self.switches),
                    hovertemplate="Switch: %{customdata}<extra></extra>",
                )
            )

        return go.Figure(
            data=traces,
            layout=go.Layout(
                title=self._title,
                xaxis_title=self._xlabel,
                yaxis_title=self._ylabel,
                template="plotly_white",
                margin={"l": 20, "r": 20, "t": 40, "b": 20},
                showlegend=False,
                width=800,
            ),
        )


def voltage_profile(
    network: ElectricalNetwork,
    *,
    mode: Literal["min", "max"],
    starting_bus_id: Id | None = None,
    traverse_transformers: bool = False,
    switch_length: float | None = None,
    distance_unit: str = "km",
) -> _VoltageProfile[ElectricalNetwork, Literal["min", "max"]]:
    """Create a voltage profile of the network.

    A voltage profile shows the voltage (in %) of buses in the network as a function of distance
    from a starting bus. Lines and transformers are also represented, colored according to their
    loading levels.

    The network does not need to have geometries defined for this function to work, as distances are
    calculated based on line lengths. However, the network must have valid load flow results, and
    relevant buses must have nominal voltages defined.

    Args:
        network:
            The electrical network to create the voltage profile for.

        mode:
            The aggregation mode to use for bus voltages plots. `"min"` for the minimum voltage of
            buses' phases, `"max"` for the maximum.

        starting_bus_id:
            The ID of the bus to start the profile from. If None, the bus of the source with the
            highest voltage is used.

        traverse_transformers:
            If True, the entire network is traversed including transformers. If False, transformers
            are not traversed.

        switch_length:
            The length in km to assign to switches when calculating distances. If None, it is set to
            the minimum of 2 meters and the shortest line in the network. Must be non-negative.

        distance_unit:
            The unit to use for distances in the profile. Defaults to "km".

    Returns:
        An object containing the voltage profile data for plotting. Use its plotting methods to
        create plots. E.g., ``rlf.plotting.voltage_profile(en).plot_matplotlib()``.
    """
    if not network.is_multi_phase:
        raise TypeError("Only multi-phase networks can be plotted. Did you mean to use rlfs.plotting.voltage_profile?")
    return _VoltageProfile._from_network(
        network,
        mode=mode,
        starting_bus_id=starting_bus_id,
        traverse_transformers=traverse_transformers,
        switch_length=switch_length,
        distance_unit=distance_unit,
    )
