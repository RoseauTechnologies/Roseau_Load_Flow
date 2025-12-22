"""Plotting functions for `roseau.load_flow`."""

import cmath
import math
from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING, Any, Literal, overload

import geopandas as gpd
import numpy as np
from typing_extensions import deprecated

from roseau.load_flow.models import AbstractBranch, AbstractTerminal
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.sym import NegativeSequence, PositiveSequence, ZeroSequence, phasor_to_sym
from roseau.load_flow.types import LineType
from roseau.load_flow.typing import ComplexArray, Id, ResultState, Side
from roseau.load_flow.utils import warn_external

if TYPE_CHECKING:
    import folium
    from matplotlib.axes import Axes

    import roseau.load_flow_single as rlfs

    type FeatureMap = dict[str, Any]
    type StyleDict = dict[str, Any]
    type MapElementType = Literal["bus", "line", "transformer"]

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
    "ok": "#1a9850",  # greenish
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
    element: AbstractTerminal | AbstractBranch, voltage_type: Literal["pp", "pn", "auto"], side: Side | None
) -> tuple[AbstractTerminal, str, ComplexArray]:
    if not element.is_multi_phase:
        raise TypeError(f"Only multi-phase elements can be plotted. Did you mean to use rlf.{type(element).__name__}?")
    if isinstance(element, AbstractTerminal):
        if side is not None:
            raise ValueError("The side argument is only valid for branch elements.")
    else:
        if side in (1, "HV"):
            element = element.side1
        elif side in (2, "LV"):
            element = element.side2
        elif side is None:
            expected = ("HV", "LV") if element.element_type == "transformer" else (1, 2)
            raise ValueError(f"The side for a {element.element_type} must be one of {expected}.")
        else:
            raise ValueError(f"Invalid side: {side!r}")
        warn_external(
            (
                f"Plotting the voltages of a {element._branch.element_type} using the side argument "
                f"is deprecated. Use {element._branch.element_type}.side{element._side_suffix} "
                f"directly instead."
            ),
            category=DeprecationWarning,
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


def _pu_to_pct[V: (float, list[float], None, float | None, list[float] | None)](v: V, /) -> V:
    """Convert per unit value to percentage."""
    if v is None:
        return None
    elif isinstance(v, list):
        return [val * 100 for val in v]
    else:
        return v * 100


def _pp_num(v: float | list[float] | None, /, missing: str = "n/a") -> str:
    """Pretty print number(s) or `missing` if `None`."""
    if v is None:
        return missing
    elif isinstance(v, list):
        return "[" + ", ".join(f"{val:.5g}" for val in v) + "]"
    else:
        return f"{v:.5g}"


#
# Phasor plotting functions
#
@overload
def plot_voltage_phasors(
    element: AbstractTerminal, *, voltage_type: Literal["pp", "pn", "auto"] = "auto", ax: "Axes | None" = None
) -> "Axes": ...
@overload
@deprecated(
    "Plotting the voltage phasors of a branch using the side argument is deprecated. Use "
    "branch.side1 or branch.side2 directly instead."
)
def plot_voltage_phasors(
    element: AbstractBranch, *, voltage_type: Literal["pp", "pn", "auto"] = "auto", side: Side, ax: "Axes | None" = None
) -> "Axes": ...
def plot_voltage_phasors(
    element: AbstractTerminal | AbstractBranch,
    *,
    voltage_type: Literal["pp", "pn", "auto"] = "auto",
    side: Side | None = None,
    ax: "Axes | None" = None,
) -> "Axes":
    """Plot the voltage phasors of a terminal element or a branch element.

    Args:
        element:
            The bus, load, source, line, switch or transformer whose voltages to plot.

        voltage_type:
            The type of the voltages to plot.

            - ``"auto"``: Plots the phase-to-neutral voltages if the element has a neutral, otherwise
              the phase-to-phase voltages. This works for all elements and is the default.
            - ``"pp"``: Plots the phase-to-phase voltages. Raises an error if the element has only
              one phase (e.g. "an").
            - ``"pn"``: Plots the phase-to-neutral voltages. Raises an error if the element has no
              neutral.

        side:
            The side of the branch element to plot.

            - For transformers: ``"HV"`` or ``"LV"``
            - For lines/switches: ``1`` or ``2``
            - For buses/loads/sources: ignored

        ax:
            The axes to plot on. If None, the currently active axes object is used.

    Returns:
        The axes with the plot.
    """
    from roseau.load_flow.utils.optional_deps import pyplot as plt

    if ax is None:
        ax = plt.gca()
    element, phases, potentials = _get_phases_and_potentials(element, voltage_type, side)
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


@overload
def plot_symmetrical_voltages(
    element: AbstractTerminal, *, axes: Iterable["Axes"] | None = None
) -> "tuple[Axes, Axes, Axes]": ...
@overload
@deprecated(
    "Plotting the symmetrical voltages of a branch using the side argument is deprecated. Use "
    "branch.side1 or branch.side2 directly instead."
)
def plot_symmetrical_voltages(
    element: AbstractBranch, *, side: Side, axes: Iterable["Axes"] | None = None
) -> "tuple[Axes, Axes, Axes]": ...
def plot_symmetrical_voltages(
    element: AbstractTerminal | AbstractBranch, *, side: Side | None = None, axes: Iterable["Axes"] | None = None
) -> "tuple[Axes, Axes, Axes]":
    """Plot the symmetrical voltages of a terminal element or a branch element.

    Args:
        element:
            The bus, load, source, line, switch or transformer whose voltages to plot. The element
            must have ``'abc'`` or ``'abcn'`` phases.

        side:
            The side of the branch element to plot.

            - For transformers: ``"HV"`` or ``"LV"``
            - For lines/switches: ``1`` or ``2``
            - For buses/loads/sources: ignored

        axes:
            The three axes to plot on for the symmetrical components in the order zero, positive,
            negative. If None, new axes are created.

    Returns:
        The three axes with the plots of the symmetrical components in the order zero, positive,
        negative.
    """
    from roseau.load_flow.utils.optional_deps import pyplot as plt

    element, phases, potentials = _get_phases_and_potentials(element, "auto", side)
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

    def _scalar_if_unique(value):
        # If the value is the same for all phases, return it as a scalar, otherwise, return the array
        if value is None:
            return None
        unique = np.unique(value)
        if unique.size == 1:
            return unique.item()
        return value.tolist()

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
