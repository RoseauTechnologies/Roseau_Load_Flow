"""Plotting functions for `roseau.load_flow`."""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

import numpy as np

import roseau.load_flow as rlf
from roseau.load_flow.typing import Complex, ComplexArray, Float

if TYPE_CHECKING:
    import folium
    from matplotlib.axes import Axes

    FeatureMap = dict[str, Any]
    StyleDict = dict[str, Any]

_COLORS = {"a": "#234e83", "b": "#cad40e", "c": "#55b2aa", "n": "#000000"}
_COLORS.update(
    {
        "an": _COLORS["a"],
        "bn": _COLORS["b"],
        "cn": _COLORS["c"],
        "ab": _COLORS["a"],
        "bc": _COLORS["b"],
        "ca": _COLORS["c"],
        "zero": _COLORS["a"],
        "pos": _COLORS["b"],
        "neg": _COLORS["c"],
    }
)


#
# Utility functions
#
def _get_rot(vector: Complex) -> float:
    """Get the rotation of a vector in degrees."""
    rot = np.angle(vector, deg=True)
    if rot > 90:
        rot -= 180
    elif rot < -90:
        rot += 180
    return rot  # type: ignore


def _get_align(rot: Float) -> tuple[str, str]:
    """Get the horizontal and vertical alignment corresponding to a rotation angle."""
    if 45 < abs(rot) < 135:
        return "right", "center"
    else:
        return "center", "bottom"


def _configure_axes(ax: "Axes", vector: ComplexArray) -> None:
    """Configure the axes for a plot of complex data."""
    center = np.mean(vector)
    ax_lim = max(abs(vector - center)) * 1.2
    ax.grid()
    ax.set_axisbelow(True)
    ax.set_aspect("equal")
    ax.set_xlim(-ax_lim + center.real, ax_lim + center.real)
    ax.set_ylim(-ax_lim + center.imag, ax_lim + center.imag)


def _draw_voltage_phasor(ax: "Axes", potential1: Complex, potential2: Complex, color: str) -> None:
    """Draw a voltage phasor between two potentials."""
    voltage = potential1 - potential2
    midpoint = (potential1 + potential2) / 2
    ax.arrow(potential2.real, potential2.imag, voltage.real, voltage.imag, color=color)  # type: ignore
    rot = _get_rot(voltage)
    ha, va = _get_align(rot)
    ax.annotate(f"{abs(voltage):.0f}V", (midpoint.real, midpoint.imag), ha=ha, va=va, rotation=rot)  # type: ignore


#
# Phasor plotting functions
#
def plot_voltage_phasors(
    element: rlf.Bus | rlf.AbstractLoad | rlf.VoltageSource, *, ax: "Axes | None" = None
) -> "Axes":
    """Plot the voltage phasors of a bus, load, or voltage source.

    Args:
        element:
            The bus, load or source whose voltages to plot.

        ax:
            The axes to plot on. If None, the currently active axes object is used.

    Returns:
        The axes with the plot.
    """
    from roseau.load_flow.utils._optional_deps import pyplot as plt

    if ax is None:
        ax = plt.gca()
    potentials = element.res_potentials.m
    _configure_axes(ax, potentials)
    ax.set_title(f"{element.id}")
    if "n" in element.phases:
        origin = potentials.flat[-1]
        for phase, potential in zip(element.phases[:-1], potentials[:-1].flat, strict=True):
            _draw_voltage_phasor(ax, potential, origin, color=_COLORS[phase])
        for phase, potential in zip(element.phases, potentials.flat, strict=True):
            ax.scatter(potential.real, potential.imag, color=_COLORS[phase], label=phase)
    elif len(element.phases) == 2:
        v1, v2 = potentials.flat
        phase = element.phases
        _draw_voltage_phasor(ax, v1, v2, color=_COLORS[phase])
        for v, ph in ((v1, phase[0]), (v2, phase[1])):
            ax.scatter(v.real, v.imag, color=_COLORS[ph], label=ph)
    else:
        assert element.phases == "abc"
        va, vb, vc = potentials.flat
        for v1, v2, phase in ((va, vb, "ab"), (vb, vc, "bc"), (vc, va, "ca")):
            _draw_voltage_phasor(ax, v1, v2, color=_COLORS[phase])
        for v, phase in ((va, "a"), (vb, "b"), (vc, "c")):
            ax.scatter(v.real, v.imag, color=_COLORS[phase], label=phase)
    ax.legend()
    return ax


def plot_symmetrical_voltages(
    element: rlf.Bus | rlf.AbstractLoad | rlf.VoltageSource, *, ax: "Axes | None" = None
) -> "Axes":
    """Plot the symmetrical voltages of a bus, load, or voltage source.

    Args:
        element:
            The bus, load or source whose symmetrical voltages to plot. The element must have 'abc'
            or 'abcn' phases.

        ax:
            The axes to plot on. If None, the current axes object is used.

    Returns:
        The axes with the plot.
    """
    from roseau.load_flow.utils._optional_deps import pyplot as plt

    if element.phases not in {"abc", "abcn"}:
        raise ValueError("The element must have 'abc' or 'abcn' phases.")
    if ax is None:
        ax = plt.gca()
    voltages_sym = rlf.converters.phasor_to_sym(element.res_voltages.m)
    _configure_axes(ax, voltages_sym)
    ax.set_title(f"{element.id} (symmetrical)")
    for sequence, voltage in zip(("zero", "pos", "neg"), voltages_sym, strict=True):
        _draw_voltage_phasor(ax, voltage, 0j, color=_COLORS[sequence])
    for sequence, voltage in zip(("zero", "pos", "neg"), voltages_sym, strict=True):
        ax.scatter(voltage.real, voltage.imag, color=_COLORS[sequence], label=sequence)
    ax.legend()
    return ax


#
# Map plotting functions
#
def plot_interactive_map(
    network: rlf.ElectricalNetwork,
    *,
    style_color: str = "#234e83",
    highlight_color: str = "#cad40e",
    style_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    highlight_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    map_kws: Mapping[str, Any] | None = None,
) -> "folium.Map":
    """Plot an electrical network on an interactive map.

    This function uses the `folium` library to create an interactive map of the electrical network.

    Make sure you have defined the geometry of the buses and lines in the network before using this
    function. You can do this by setting the `geometry` attribute of the buses and lines.

    Args:
        network:
            The electrical network to plot. Only the buses and lines are currently plotted.

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
            `location` is set to the centroid of the network geometry and `zoom_start` is calculated
            based on its bounding box.

    Returns:
        The :class:`folium.Map` object with the network plot.
    """
    try:
        import folium
    except ImportError as e:
        raise ImportError(
            "The `folium` library is required when using `roseau.load_flow.plotting.plot_interactive_map`."
            "Install it with `pip install folium`."
        ) from e

    map_kws = dict(map_kws) if map_kws is not None else {}

    buses_gdf = network.buses_frame
    buses_gdf.reset_index(inplace=True)
    buses_gdf["element_type"] = "bus"
    lines_gdf = network.lines_frame
    lines_gdf.reset_index(inplace=True)
    lines_gdf["element_type"] = "line"

    def internal_style_function(feature):
        result = style_function(feature) if style_function is not None else None
        if result is not None:
            return result
        # Default style
        if feature["properties"]["element_type"] == "bus":
            return {
                "fill": True,
                "fillColor": style_color,
                "color": style_color,
                "fillOpacity": 1,
                "radius": 3,
            }
        elif feature["properties"]["element_type"] == "line":
            return {"color": style_color, "weight": 2}
        else:
            return {"color": style_color, "weight": 2}

    def internal_highlight_function(feature):
        result = highlight_function(feature) if highlight_function is not None else None
        if result is not None:
            return result
        # Default highlight style
        if feature["properties"]["element_type"] == "bus":
            return {"color": highlight_color, "fillColor": highlight_color}
        elif feature["properties"]["element_type"] == "line":
            return {"color": highlight_color}
        else:
            return {"color": highlight_color}

    # Calculate the center and zoom level of the map if not provided
    if "location" not in map_kws or "zoom_start" not in map_kws:
        geom_union = buses_gdf.union_all()
        if "location" not in map_kws:
            map_kws["location"] = list(reversed(geom_union.centroid.coords[0]))
        if "zoom_start" not in map_kws:
            # Calculate the zoom level based on the bounding box of the network
            min_x, min_y, max_x, max_y = geom_union.bounds
            zoom_lon = np.ceil(np.log2(360 * 2.0 / (max_x - min_x)))
            zoom_lat = np.ceil(np.log2(360 * 2.0 / (max_y - min_y)))
            map_kws["zoom_start"] = int(min(zoom_lon, zoom_lat))

    m = folium.Map(**map_kws)
    folium.GeoJson(
        data=lines_gdf,
        name="lines",
        marker=folium.CircleMarker(),
        style_function=internal_style_function,
        highlight_function=internal_highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["id", "phases", "bus1_id", "bus2_id", "parameters_id", "length"],
            aliases=["Id:", "Phases:", "Bus1:", "Bus2:", "Parameters:", "Length (km):"],
            localize=True,
            sticky=False,
            labels=True,
            max_width=800,
        ),
    ).add_to(m)
    folium.GeoJson(
        buses_gdf,
        name="buses",
        marker=folium.CircleMarker(),
        style_function=internal_style_function,
        highlight_function=internal_highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["id", "phases"],
            aliases=["Id:", "Phases:"],
            localize=True,
            sticky=False,
            labels=True,
            max_width=800,
        ),
    ).add_to(m)
    folium.LayerControl().add_to(m)
    return m
