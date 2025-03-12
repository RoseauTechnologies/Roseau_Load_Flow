"""Plotting functions for `roseau.load_flow`."""

import cmath
import math
from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from roseau.load_flow.models import AbstractBranch, AbstractTerminal
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.sym import NegativeSequence, PositiveSequence, ZeroSequence, phasor_to_sym
from roseau.load_flow.typing import ComplexArray

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
    }
)


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
    element: AbstractTerminal | AbstractBranch,
    voltage_type: Literal["pp", "pn", "auto"],
    side: Literal[1, 2, "HV", "LV"] | None,
) -> tuple[str, ComplexArray]:
    if isinstance(element, AbstractTerminal):
        if side is not None:
            raise ValueError("The side argument is only valid for branch elements.")
        phases, potentials = element.phases, element.res_potentials.m
    elif side in (1, "HV"):
        phases, potentials = element.phases1, element.res_potentials[0].m
    elif side in (2, "LV"):
        phases, potentials = element.phases2, element.res_potentials[1].m
    elif side is None:
        expected = ("HV", "LV") if element.element_type == "transformer" else (1, 2)
        raise ValueError(f"The side for a {element.element_type} must be one of {expected}.")
    else:
        raise ValueError(f"Invalid side: {side!r}")
    if voltage_type == "auto":
        return phases, potentials
    elif voltage_type == "pn":
        if "n" not in phases:
            raise ValueError("The element must have a neutral to plot phase-to-neutral voltages.")
        return phases, potentials
    elif voltage_type == "pp":
        phases_pp = phases.removesuffix("n")
        n_pp = len(phases_pp)
        if n_pp == 1:
            raise ValueError("The element must have more than one phase to plot phase-to-phase voltages.")
        return phases_pp, potentials[:n_pp]
    else:
        raise ValueError(f"Invalid voltage_type: {voltage_type!r}")


#
# Phasor plotting functions
#
def plot_voltage_phasors(
    element: AbstractTerminal | AbstractBranch,
    *,
    voltage_type: Literal["pp", "pn", "auto"] = "auto",
    side: Literal[1, 2, "HV", "LV"] | None = None,
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
    phases, potentials = _get_phases_and_potentials(element, voltage_type, side)
    _configure_axes(ax, potentials)
    ax.set_title(f"{element.id}" if side is None else f"{element.id} ({side})")
    if "n" in phases:
        origin = potentials.flat[-1]
        for phase, potential in zip(phases[:-1], potentials[:-1].flat, strict=True):
            _draw_voltage_phasor(ax, potential, origin, color=_COLORS[phase])
        for phase, potential in zip(phases, potentials.flat, strict=True):
            ax.scatter(potential.real, potential.imag, color=_COLORS[phase], label=phase)
    elif len(phases) == 2:
        v1, v2 = potentials.flat
        phase = phases
        _draw_voltage_phasor(ax, v1, v2, color=_COLORS[phase])
        for v, ph in ((v1, phase[0]), (v2, phase[1])):
            ax.scatter(v.real, v.imag, color=_COLORS[ph], label=ph)
    else:
        assert phases == "abc"
        va, vb, vc = potentials.flat
        for v1, v2, phase in ((va, vb, "ab"), (vb, vc, "bc"), (vc, va, "ca")):
            _draw_voltage_phasor(ax, v1, v2, color=_COLORS[phase])
        for v, phase in ((va, "a"), (vb, "b"), (vc, "c")):
            ax.scatter(v.real, v.imag, color=_COLORS[phase], label=phase)
    ax.legend()
    return ax


def plot_symmetrical_voltages(
    element: AbstractTerminal | AbstractBranch,
    *,
    side: Literal[1, 2, "HV", "LV"] | None = None,
    axes: Iterable["Axes"] | None = None,
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

    phases, potentials = _get_phases_and_potentials(element, "auto", side)
    if phases not in {"abc", "abcn"}:
        raise ValueError("The element must have 'abc' or 'abcn' phases.")
    if axes is None:
        _, axes = plt.subplots(1, 3)
    ax0, ax1, ax2 = axes  # type: ignore
    u0, u1, u2 = sym_components = phasor_to_sym(potentials[:3])
    un = potentials[3] if "n" in phases else 0j
    ax_limits = np.array(1.2 * max(abs(sym_components)) * PositiveSequence, dtype=np.complex128)
    title = f"{element.id}" if side is None else f"{element.id} ({side})"

    def _draw_balanced_voltages(ax: "Axes", u: "complex", seq: "ComplexArray"):
        seq_potentials = np.array(u * seq, dtype=np.complex128)
        for phase, u in zip("abc", seq_potentials.flat, strict=False):
            _draw_voltage_phasor(ax, u, 0j, color=_COLORS[phase], annotate=False)
        for phase, u in zip("abc", seq_potentials.flat, strict=False):
            ax.scatter(u.real, u.imag, color=_COLORS[phase], label=phase)

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
        xy = u + ax_limits[0] / 20 * cmath.exp(1j * angle)  # move it 5% of the axis limits
        ax.annotate(f"{abs(u):.0f}V", (xy.real, xy.imag), ha=ha, va=va)
        ax.legend()

    return ax0, ax1, ax2


#
# Map plotting functions
#
def plot_interactive_map(
    network: ElectricalNetwork,
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
            zoom_lon = math.ceil(math.log2(360 * 2.0 / (max_x - min_x)))
            zoom_lat = math.ceil(math.log2(360 * 2.0 / (max_y - min_y)))
            map_kws["zoom_start"] = min(zoom_lon, zoom_lat)

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
        data=buses_gdf,
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
