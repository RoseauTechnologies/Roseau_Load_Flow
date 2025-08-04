from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

import geopandas as gpd

from roseau.load_flow.plotting import _check_folium, _plot_interactive_map_internal
from roseau.load_flow_single.network import ElectricalNetwork

if TYPE_CHECKING:
    import branca.colormap as cm
    import folium

    from roseau.load_flow.plotting import FeatureMap, StyleDict


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

        add_tooltips:
            If ``True`` (default), tooltips will be added to the map elements. Tooltips appear when
            hovering over an element.

        add_popups:
            If ``True`` (default), popups will be added to the map elements. Popups appear when
            clicking on an element.

        add_search:
            If ``True`` (default), a search bar will be added to the map to search for network
            elements by their ID.

    Returns:
        The :class:`folium.Map` object with the network plot.
    """
    _check_folium(func_name="plot_interactive_map")
    if network.is_multi_phase:
        raise TypeError(
            "Only single-phase networks can be plotted. Did you mean to use rlf.plotting.plot_interactive_map?"
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
    for idx in lines_gdf.index:
        lp = network.lines[lines_gdf.at[idx, "id"]].parameters
        lines_gdf.at[idx, "ampacity"] = lp._ampacity
        lines_gdf.at[idx, "section"] = lp._section
        lines_gdf.at[idx, "line_type"] = lp._line_type
        lines_gdf.at[idx, "material"] = lp._material
        lines_gdf.at[idx, "insulator"] = lp._insulator

    bus_fields = {
        "id": "Id:",
        "nominal_voltage": "Un (V):",
        "min_voltage_level": "Umin (%):",
        "max_voltage_level": "Umax (%):",
    }
    line_fields = {
        "id": "Id:",
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
    }

    m = _plot_interactive_map_internal(
        buses_gdf=buses_gdf,
        lines_gdf=lines_gdf,
        bus_fields=bus_fields,
        line_fields=line_fields,
        style_color_callback=lambda et, id: style_color,
        highlight_color=highlight_color,
        style_function=style_function,
        highlight_function=highlight_function,
        map_kws=map_kws,
        add_tooltips=add_tooltips,
        add_popups=add_popups,
        add_search=add_search,
    )
    return m


def plot_results_interactive_map(
    network: ElectricalNetwork,
    *,
    style_color: str = "#234e83",
    highlight_color: str = "#cad40e",
    style_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    highlight_function: Callable[["FeatureMap"], "StyleDict | None"] | None = None,
    bus_colormap: "cm.ColorMap | Sequence[str] | None" = None,
    line_colormap: "cm.ColorMap | Sequence[str] | None" = None,
    map_kws: Mapping[str, Any] | None = None,
    add_tooltips: bool = True,
    add_popups: bool = True,
    add_search: bool = True,
) -> "folium.Map":
    """Plot an electrical network on an interactive map with the load flow results.

    This function uses the `folium` library to create an interactive map of the electrical network
    with the buses colored according to their voltage levels and the lines colored according to their
    loading.

    Make sure you have defined the geometry of the buses and lines in the network before using this
    function. You can do this by setting the `geometry` attribute of the buses and lines. Also,
    ensure that the network has valid results by running a load flow calculation before plotting.

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

        bus_colormap:
            A callable that takes a voltage level in % and returns a color for the bus markers
            or a sequence of colors to create a linear colormap representing the voltage level
            from minimum to maximum. If not provided, a linear colormap is created with the
            colors ``["blue", "cyan", "green", "yellow", "red"]``

        line_colormap:
            A callable that takes a loading in % and returns a color for the line markers or a
            sequence of colors to create a linear colormap representing the loading from 0% to
            maximum. If not provided, a linear colormap is created with the colors
            ``["green", "yellow", "red"]``.

        map_kws:
            Additional keyword arguments to pass to the :class:`folium.Map` constructor. By default,
            `location` is set to the centroid of the network geometry and `zoom_start` is calculated
            based on its bounding box.

        add_tooltips:
            If ``True`` (default), tooltips will be added to the map elements. Tooltips appear when
            hovering over an element.

        add_popups:
            If ``True`` (default), popups will be added to the map elements. Popups appear when
            clicking on an element.

        add_search:
            If ``True`` (default), a search bar will be added to the map to search for network
            elements by their ID.

    Returns:
        The `folium.Map` object with the network plot.
    """
    _check_folium(func_name="plot_results_interactive_map")
    import branca.colormap as cm

    if network.is_multi_phase:
        # TODO: add " Did you mean to use rlf.plotting.plot_results_interactive_map?" when it is implemented
        raise TypeError("Only single-phase networks can be plotted.")
    network._check_valid_results()

    min_voltage = float("inf")
    max_voltage = 0.0
    max_loading = 0.0
    buses_data = []
    buses_voltage_levels = {}
    for bus in network.buses.values():
        if bus._nominal_voltage is None:
            no_nominal_voltage = [bus.id for bus in network.buses.values() if bus._nominal_voltage is None]
            raise ValueError(f"The following buses do not have a nominal voltage defined: {no_nominal_voltage}.")
        if bus._min_voltage_level is None:
            no_min_voltage = [bus.id for bus in network.buses.values() if bus._min_voltage_level is None]
            raise ValueError(f"The following buses do not have a minimum voltage level defined: {no_min_voltage}.")
        if bus._max_voltage_level is None:
            no_max_voltage = [bus.id for bus in network.buses.values() if bus._max_voltage_level is None]
            raise ValueError(f"The following buses do not have a maximum voltage level defined: {no_max_voltage}.")
        min_voltage = min(min_voltage, bus._min_voltage_level * 100)
        max_voltage = max(max_voltage, bus._max_voltage_level * 100)
        res_voltage_level = bus._res_voltage_level_getter(warning=False)
        assert res_voltage_level is not None
        res_voltage_level *= 100
        buses_data.append(
            {
                "id": bus.id,
                "element_type": "bus",
                "nominal_voltage": bus._nominal_voltage,
                "min_voltage_level": bus._min_voltage_level * 100,
                "max_voltage_level": bus._max_voltage_level * 100,
                "geometry": bus.geometry,
                "res_separator": "",  # Results separator
                "res_voltage": abs(bus.res_voltage.m),
                "res_voltage_level": res_voltage_level,
            }
        )
        buses_voltage_levels[bus.id] = res_voltage_level

    lines_data = []
    lines_loading = {}
    for line in network.lines.values():
        lp = line.parameters
        if lp._ampacity is None:
            no_ampacity = list(dict.fromkeys(lp.id for line in network.lines.values() if lp._ampacity is None))
            raise ValueError(f"The following line parameters do not have an ampacity defined: {no_ampacity}.")
        max_loading = max(max_loading, line._max_loading * 100)
        res_loading = line._res_loading_getter(warning=False)
        assert res_loading is not None
        res_loading *= 100
        lines_data.append(
            {
                "id": line.id,
                "element_type": "line",
                "bus1_id": line.bus1.id,
                "bus2_id": line.bus2.id,
                "parameters_id": lp.id,
                "length": line._length,
                "line_type": lp._line_type,
                "material": lp._material,
                "insulator": lp._insulator,
                "section": lp._section,
                "ampacity": lp._ampacity,
                "geometry": line.geometry,
                "res_separator": "",  # Results separator
                "max_loading": line._max_loading * 100,
                "res_loading": res_loading,
            }
        )
        lines_loading[line.id] = res_loading

    buses_gdf = gpd.GeoDataFrame(buses_data, crs=network.crs)
    lines_gdf = gpd.GeoDataFrame(lines_data, crs=network.crs)
    if not isinstance(bus_colormap, cm.ColorMap):
        bus_colormap = cm.LinearColormap(
            colors=["blue", "cyan", "green", "yellow", "red"] if bus_colormap is None else bus_colormap,
            vmin=min_voltage,
            vmax=max_voltage,
            caption="Voltage level (%)",
        )
    if not isinstance(line_colormap, cm.ColorMap):
        line_colormap = cm.LinearColormap(
            ["green", "yellow", "red"] if line_colormap is None else line_colormap,
            vmin=0,
            vmax=max_loading,
            caption="Line loading %",
        )

    def style_color_callback(et, eid):
        if et == "bus":
            return bus_colormap(buses_voltage_levels[eid])
        elif et == "line":
            return line_colormap(lines_loading[eid])
        else:
            return style_color

    bus_fields = {
        "id": "Id:",
        "nominal_voltage": "Un (V):",
        "min_voltage_level": "Umin (%):",
        "max_voltage_level": "Umax (%):",
        "res_separator": "--",
        "res_voltage": "U (V):",
        "res_voltage_level": "U (%):",
    }
    line_fields = {
        "id": "Id:",
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
    }
    m = _plot_interactive_map_internal(
        buses_gdf=buses_gdf,
        lines_gdf=lines_gdf,
        bus_fields=bus_fields,
        line_fields=line_fields,
        style_color_callback=style_color_callback,
        highlight_color=highlight_color,
        style_function=style_function,
        highlight_function=highlight_function,
        map_kws=map_kws,
        add_tooltips=add_tooltips,
        add_popups=add_popups,
        add_search=add_search,
    )
    bus_colormap.add_to(m)
    line_colormap.add_to(m)

    return m
