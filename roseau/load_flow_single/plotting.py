from collections.abc import Callable, Mapping
from functools import partial
from typing import TYPE_CHECKING, Any, Literal

import geopandas as gpd
import shapely as shp

from roseau.load_flow.plotting import (
    _DEFAULT_MAP_STYLE_COLORS,
    _check_folium,
    _default_map_results_style_color,
    _make_style_color_callback,
    _multiply,
    _plot_interactive_map_internal,
    _pp_num,
    _VoltageProfile,
)
from roseau.load_flow.plotting import (
    _MAP_FIELDS as _MAP_FIELDS_MULTI,
)
from roseau.load_flow.plotting import (
    _MAP_RESULTS_FIELDS as _MAP_RESULTS_FIELDS_MULTI,
)
from roseau.load_flow.typing import Id
from roseau.load_flow_single.network import ElectricalNetwork

if TYPE_CHECKING:
    import folium

    from roseau.load_flow.plotting import FeatureMap, StyleColorCallback, StyleDict

_MAP_FIELDS = {et: {k: v for k, v in fields.items() if k != "phases"} for et, fields in _MAP_FIELDS_MULTI.items()}
_MAP_RESULTS_FIELDS = {
    et: {k: v for k, v in fields.items() if k != "phases"} for et, fields in _MAP_RESULTS_FIELDS_MULTI.items()
}


def _get_buses_data_for_map_plot(network: ElectricalNetwork, with_results: bool) -> gpd.GeoDataFrame:
    buses_data: dict[str, list[Any]] = {
        field: [] for field in (_MAP_RESULTS_FIELDS if with_results else _MAP_FIELDS)["bus"]
    }
    buses_data["geometry"] = []
    for bus in network.buses.values():
        buses_data["id"].append(bus.id)
        buses_data["nominal_voltage"].append(bus._nominal_voltage)
        buses_data["min_voltage_level"].append(_multiply(bus._min_voltage_level, 100))
        buses_data["max_voltage_level"].append(_multiply(bus._max_voltage_level, 100))
        buses_data["geometry"].append(bus.geometry)
        if not with_results:
            continue
        buses_data["res_separator"].append("")  # Results separator
        buses_data["res_voltage"].append(abs(bus._res_voltage_getter(warning=False)))
        buses_data["res_voltage_level"].append(_multiply(bus._res_voltage_level_getter(warning=False), 100))
        bus_agg_power = bus._res_agg_power_getter(warning=False) / 1e3  # Convert to kVA
        buses_data["res_active_power"].append(bus_agg_power.real)
        buses_data["res_reactive_power"].append(bus_agg_power.imag)
    return gpd.GeoDataFrame(buses_data, crs=network.crs)


def _get_lines_data_for_map_plot(network: ElectricalNetwork, with_results: bool) -> gpd.GeoDataFrame:
    lines_data: dict[str, list[Any]] = {
        field: [] for field in (_MAP_RESULTS_FIELDS if with_results else _MAP_FIELDS)["line"]
    }
    lines_data["geometry"] = []
    for line in network.lines.values():
        lp = line._parameters
        lines_data["id"].append(line.id)
        lines_data["bus1_id"].append(line.bus1.id)
        lines_data["bus2_id"].append(line.bus2.id)
        lines_data["parameters_id"].append(lp.id)
        lines_data["length"].append(line._length)
        lines_data["line_type"].append(lp._line_type)
        lines_data["material"].append(lp._material)
        lines_data["insulator"].append(lp._insulator)
        lines_data["section"].append(lp._section)
        lines_data["ampacity"].append(lp._ampacity)
        lines_data["max_loading"].append(line._max_loading * 100)
        lines_data["geometry"].append(line.geometry)
        if not with_results:
            continue
        lines_data["res_separator"].append("")  # Results separator
        lines_data["res_loading"].append(_multiply(line._res_loading_getter(warning=False), 100))
    return gpd.GeoDataFrame(lines_data, crs=network.crs)


def _get_transformers_data_for_map_plot(
    network: ElectricalNetwork, with_results: bool, buses_frame: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    trs_data: dict[str, list[Any]] = {
        field: [] for field in (_MAP_RESULTS_FIELDS if with_results else _MAP_FIELDS)["transformer"]
    }
    trs_data["geometry"] = []
    buses_frame = buses_frame.set_index("id")
    for tr in network.transformers.values():
        tp = tr._parameters
        trs_data["id"].append(tr.id)
        trs_data["bus_hv_id"].append(tr.bus_hv.id)
        trs_data["bus_lv_id"].append(tr.bus_lv.id)
        trs_data["tap"].append(tr._tap * 100)  # Convert to percentage
        trs_data["vg"].append(tp.vg)
        trs_data["rating"].append(tp._rating_pretty())
        trs_data["parameters_id"].append(tp.id)
        trs_data["max_loading"].append(tr._max_loading * 100)
        trs_data["geometry"].append(tr.bus_hv.geometry)
        trs_data["nominal_voltages"].append(
            _pp_num([buses_frame.at[bus.id, "nominal_voltage"] for bus in (tr.bus_hv, tr.bus_lv)])
        )
        trs_data["min_voltage_levels"].append(
            _pp_num([buses_frame.at[bus.id, "min_voltage_level"] for bus in (tr.bus_hv, tr.bus_lv)])
        )
        trs_data["max_voltage_levels"].append(
            _pp_num([buses_frame.at[bus.id, "max_voltage_level"] for bus in (tr.bus_hv, tr.bus_lv)])
        )
        if not with_results:
            continue
        trs_data["res_separator"].append("")  # Results separator
        trs_data["res_loading"].append(tr._res_loading_getter(warning=False) * 100)
        trs_data["res_voltage_hv"].append(buses_frame.at[tr.bus_hv.id, "res_voltage"])
        trs_data["res_voltage_lv"].append(buses_frame.at[tr.bus_lv.id, "res_voltage"])
        trs_data["res_voltage_level_hv"].append(buses_frame.at[tr.bus_hv.id, "res_voltage_level"])
        trs_data["res_voltage_level_lv"].append(buses_frame.at[tr.bus_lv.id, "res_voltage_level"])
    return gpd.GeoDataFrame(trs_data, crs=network.crs)


def _get_switches_data_for_map_plot(network: ElectricalNetwork, with_results: bool) -> gpd.GeoDataFrame:
    # Switches as lines if their buses are not at the same point
    switches_data: dict[str, list[Any]] = {
        field: [] for field in (_MAP_RESULTS_FIELDS if with_results else _MAP_FIELDS)["switch"]
    }
    switches_data["geometry"] = []
    for sw in network.switches.values():
        geom1, geom2 = sw.bus1.geometry, sw.bus2.geometry
        if geom1 is None or geom2 is None:
            continue
        geom1, geom2 = geom1.centroid, geom2.centroid
        if geom1.equals(geom2):
            continue
        geom = shp.LineString([geom1, geom2])
        switches_data["id"].append(sw.id)
        switches_data["bus1_id"].append(sw.bus1.id)
        switches_data["bus2_id"].append(sw.bus2.id)
        switches_data["status"].append("closed" if sw.closed else "open")
        switches_data["geometry"].append(geom)
    return gpd.GeoDataFrame(switches_data, crs=network.crs)


def _get_regulators_data_for_map_plot(
    network: ElectricalNetwork, with_results: bool, buses_frame: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    regs_data: dict[str, list[Any]] = {
        field: [] for field in (_MAP_RESULTS_FIELDS if with_results else _MAP_FIELDS)["regulator"]
    }
    regs_data["geometry"] = []
    buses_frame = buses_frame.set_index("id")
    for reg in network.regulators.values():
        rp = reg._parameters
        regs_data["id"].append(reg.id)
        regs_data["bus1_id"].append(reg.bus1.id)
        regs_data["bus2_id"].append(reg.bus2.id)
        regs_data["rating"].append(rp._rating_pretty())
        regs_data["parameters_id"].append(rp.id)
        regs_data["max_loading"].append(reg._max_loading * 100)  # Convert to percentage
        regs_data["u_ref"].append(reg._u_ref * 100)  # Convert to percentage
        regs_data["u_range"].append(f"±{_pp_num(rp._u_range * 100)}")  # Convert to percentage
        regs_data["geometry"].append(reg.bus1.geometry)
        regs_data["nominal_voltage"].append(buses_frame.at[reg.bus1.id, "nominal_voltage"])
        regs_data["min_voltage_level"].append(buses_frame.at[reg.bus1.id, "min_voltage_level"])
        regs_data["max_voltage_level"].append(buses_frame.at[reg.bus1.id, "max_voltage_level"])
        if not with_results:
            continue
        regs_data["res_separator"].append("")
        regs_data["res_tap"].append(reg._res_tap_getter(warning=False) * 100)  # Convert to percentage
        regs_data["res_loading"].append(reg._res_loading_getter(warning=False) * 100)  # Convert to percentage
        regs_data["res_voltage1"].append(buses_frame.at[reg.bus1.id, "res_voltage"])
        regs_data["res_voltage2"].append(buses_frame.at[reg.bus2.id, "res_voltage"])
        regs_data["res_voltage_level1"].append(buses_frame.at[reg.bus1.id, "res_voltage_level"])
        regs_data["res_voltage_level2"].append(buses_frame.at[reg.bus2.id, "res_voltage_level"])
    return gpd.GeoDataFrame(regs_data, crs=network.crs)


def plot_interactive_map(
    network: ElectricalNetwork,
    *,
    style_color: "str | StyleColorCallback | None" = None,
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
            The electrical network to plot. Buses, lines, transformers and regulators are plotted.
            Buses of source elements are represented with bigger square markers.

        style_color:
            A string to use as the default color of all elements, or a callback function in the form
            ``(el_type, el_id, /) -> str`` returning the color of that specific element. ``el_type``
            is one of ``"bus"``, ``"line"``, ``"transformer"``, ``"switch"``, ``"regulator"``. Return
            ``None`` from the callable to use the default color for that element instead. Defaults to
            :roseau-primary:`■ #234e83` for buses and lines, :color-gray:`■ #888888` for switches and
            regulators, and :color-black:`■ #000000` for transformers.

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
            Additional keyword arguments to pass to the :class:`folium.Map` constructor. The
            following keywords are passed by default:

            - ``tiles="CartoDB Positron"``: A light background map that does not obscure network
              elements.
            - ``location``: The centroid of the network geometry if ``fit_bounds`` is false. No
              default value is set otherwise.
            - ``zoom_start``: Calculated based on its bounding box if ``fit_bounds`` is false. No
              default value is set otherwise.

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
    if network.is_multi_phase:
        raise TypeError(
            "Only single-phase networks can be plotted. Did you mean to use rlf.plotting.plot_interactive_map?"
        )
    buses_gdf = _get_buses_data_for_map_plot(network, with_results=False)
    lines_gdf = _get_lines_data_for_map_plot(network, with_results=False)
    transformers_gdf = _get_transformers_data_for_map_plot(network, with_results=False, buses_frame=buses_gdf)
    switches_gdf = _get_switches_data_for_map_plot(network, with_results=False)
    regulators_gdf = _get_regulators_data_for_map_plot(network, with_results=False, buses_frame=buses_gdf)
    m = _plot_interactive_map_internal(
        network=network,
        dataframes={
            "bus": buses_gdf,
            "line": lines_gdf,
            "transformer": transformers_gdf,
            "switch": switches_gdf,
            "regulator": regulators_gdf,
        },
        fields=_MAP_FIELDS,
        style_color_callback=_make_style_color_callback(style_color, lambda et, eid: _DEFAULT_MAP_STYLE_COLORS[et]),
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
    style_color: "str | StyleColorCallback | None" = None,
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
            The electrical network to plot. Buses, lines, transformers and regulators are plotted.
            Buses of source elements are represented with bigger square markers.

        style_color:
            A string to use as the default color of all elements, or a callback function in the form
            ``(el_type, el_id, /) -> str`` returning the color of that specific element. ``el_type``
            is one of ``"bus"``, ``"line"``, ``"transformer"``, ``"switch"``, ``"regulator"``. Return
            ``None`` from the callable to use the default color for that element instead. The default
            colors depend on the element type and its results:

            For buses, the default color is determined by their voltage levels:

            - blue: `U` below `Umin`
            - cyan: `U` close to `Umin`; specifically, `Umin ≤ U < 0.75 * Umin + 0.25`
            - green: `U` within `Umin` and `Umax` and not close to the limits
            - orange: `U` close to `Umax`; specifically, `0.75 * Umax + 0.25 < U ≤ Umax`
            - red: `U` above `Umax`

            For lines, transformers and regulators, the default color depends on their loadings:
            - green: below 75% of the maximum loading
            - orange: between 75% and 100% of the maximum loading
            - red: above 100% of the maximum loading

            For switches, the default color is :color-gray:`■ #888888`.

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
            Additional keyword arguments to pass to the :class:`folium.Map` constructor. The
            following keywords are passed by default:

            - ``tiles="CartoDB Positron"``: A light background map that does not obscure network
              elements.
            - ``location``: The centroid of the network geometry if ``fit_bounds`` is false. No
              default value is set otherwise.
            - ``zoom_start``: Calculated based on its bounding box if ``fit_bounds`` is false. No
              default value is set otherwise.

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
    if network.is_multi_phase:
        raise TypeError(
            "Only single-phase networks can be plotted. Did you mean to use rlf.plotting.plot_results_interactive_map?"
        )
    network._check_valid_results()
    buses_gdf = _get_buses_data_for_map_plot(network, with_results=True)
    lines_gdf = _get_lines_data_for_map_plot(network, with_results=True)
    transformers_gdf = _get_transformers_data_for_map_plot(network, with_results=True, buses_frame=buses_gdf)
    switches_gdf = _get_switches_data_for_map_plot(network, with_results=True)
    regulators_gdf = _get_regulators_data_for_map_plot(network, with_results=True, buses_frame=buses_gdf)
    m = _plot_interactive_map_internal(
        network=network,
        dataframes={
            "bus": buses_gdf,
            "line": lines_gdf,
            "transformer": transformers_gdf,
            "switch": switches_gdf,
            "regulator": regulators_gdf,
        },
        fields=_MAP_RESULTS_FIELDS,
        style_color_callback=_make_style_color_callback(
            style_color, partial(_default_map_results_style_color, network=network)
        ),
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


def voltage_profile(
    network: ElectricalNetwork,
    *,
    starting_bus_id: Id | None = None,
    traverse_transformers: bool = False,
    switch_length: float | None = None,
    distance_unit: str = "km",
) -> _VoltageProfile[ElectricalNetwork, Literal[""]]:
    """Create a voltage profile of the network.

    A voltage profile shows the voltage (in %) of buses in the network as a function of distance
    from a starting bus. Lines, transformers and regulators are also represented, colored according
    to their loading levels.

    The network does not need to have geometries defined for this function to work, as distances are
    calculated based on line lengths. However, the network must have valid load flow results, and
    relevant buses must have nominal voltages defined.

    Args:
        network:
            The electrical network to create the voltage profile for.

        starting_bus_id:
            The ID of the bus to start the profile from. If None, the bus of the source with the
            highest voltage is used.

        traverse_transformers:
            If True, the entire network is traversed including transformers. If False, transformers
            are not traversed. Regulators are always traversed regardless of this parameter.

        switch_length:
            The length in km to assign to switches when calculating distances. If None, it is set to
            the minimum of 2 meters and the shortest line in the network. Must be non-negative.

        distance_unit:
            The unit to use for distances in the profile. Defaults to "km".

    Returns:
        An object containing the voltage profile data for plotting. Use its plotting methods to
        create plots. E.g., ``rlfs.plotting.voltage_profile(en).plot_matplotlib()``.
    """
    if network.is_multi_phase:
        raise TypeError("Only single-phase networks can be plotted. Did you mean to use rlf.plotting.voltage_profile?")
    return _VoltageProfile._from_network(
        network,
        mode="",
        starting_bus_id=starting_bus_id,
        traverse_transformers=traverse_transformers,
        switch_length=switch_length,
        distance_unit=distance_unit,
    )
