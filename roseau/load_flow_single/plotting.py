from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

import geopandas as gpd

from roseau.load_flow.plotting import _RESULT_COLORS, _check_folium, _plot_interactive_map_internal, _pp_num, _pu_to_pct
from roseau.load_flow.typing import Id
from roseau.load_flow_single.models import Transformer
from roseau.load_flow_single.network import ElectricalNetwork

if TYPE_CHECKING:
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
        line_id: Id = lines_gdf.at[idx, "id"]  # type: ignore
        lp = network.lines[line_id].parameters
        lines_gdf.at[idx, "ampacity"] = lp._ampacity
        lines_gdf.at[idx, "section"] = lp._section
        lines_gdf.at[idx, "line_type"] = lp._line_type
        lines_gdf.at[idx, "material"] = lp._material
        lines_gdf.at[idx, "insulator"] = lp._insulator

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
                "nominal_voltage": "Un (V):",
                "min_voltage_level": "Umin (%):",
                "max_voltage_level": "Umax (%):",
            },
            "line": {
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
                "uhv": "» Ur (V):",
                "lv_side": "LV Side",
                "bus_lv_id": "» Bus:",
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
            ``None``, the default style is used. By default, buses and lines are colored according
            to their voltage levels and loadings, respectively.

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

    if network.is_multi_phase:
        # TODO: add " Did you mean to use rlf.plotting.plot_results_interactive_map?" when it is implemented
        raise TypeError("Only single-phase networks can be plotted.")
    network._check_valid_results()

    buses_data: list[dict[str, Any]] = [
        {
            "id": bus.id,
            "element_type": "bus",
            "nominal_voltage": bus._nominal_voltage,
            "min_voltage_level": _pu_to_pct(bus._min_voltage_level),
            "max_voltage_level": _pu_to_pct(bus._max_voltage_level),
            "geometry": bus.geometry,
            "res_separator": "",  # Results separator
            "res_voltage": abs(bus._res_voltage_getter(warning=False)),
            "res_voltage_level": _pu_to_pct(bus._res_voltage_level_getter(warning=False)),
        }
        for bus in network.buses.values()
    ]
    buses_data_by_id = {bus["id"]: bus for bus in buses_data}

    lines_data: list[dict[str, Any]] = [
        {
            "id": line.id,
            "element_type": "line",
            "bus1_id": line.bus1.id,
            "bus2_id": line.bus2.id,
            "parameters_id": line._parameters.id,
            "length": line._length,
            "line_type": line._parameters._line_type,
            "material": line._parameters._material,
            "insulator": line._parameters._insulator,
            "section": line._parameters._section,
            "ampacity": line._parameters._ampacity,
            "geometry": line.geometry,
            "res_separator": "",  # Results separator
            "max_loading": line._max_loading * 100,
            "res_loading": _pu_to_pct(line._res_loading_getter(warning=False)),
        }
        for line in network.lines.values()
    ]

    def _get_tr_buses_data(tr: Transformer, field: str) -> str:
        return _pp_num([buses_data_by_id[bus_id][field] for bus_id in (tr.bus_hv.id, tr.bus_lv.id)])

    transformers_data: list[dict[str, Any]] = [
        {
            "id": tr.id,
            "element_type": "transformer",
            "bus_hv_id": tr.bus_hv.id,
            "bus_lv_id": tr.bus_lv.id,
            "parameters_id": tr._parameters.id,
            "geometry": tr.bus_hv.geometry,
            "vg": tr._parameters.vg,
            "sn": tr._parameters._sn / 1e3,  # Convert to kVA
            "tap": tr._tap * 100,  # Convert to percentage
            "rated_voltages": _pp_num([tr._parameters._uhv, tr._parameters._ulv]),
            "max_loading": tr._max_loading * 100,
            "nominal_voltages": _get_tr_buses_data(tr, "nominal_voltage"),
            "min_voltage_levels": _get_tr_buses_data(tr, "min_voltage_level"),
            "max_voltage_levels": _get_tr_buses_data(tr, "max_voltage_level"),
            "res_separator": "",  # Results separator
            "res_loading": tr._res_loading_getter(warning=False) * 100,
            "res_voltages": _get_tr_buses_data(tr, "res_voltage"),
            "res_voltage_levels": _get_tr_buses_data(tr, "res_voltage_level"),
        }
        for tr in network.transformers.values()
    ]

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
                "nominal_voltage": "Un (V):",
                "min_voltage_level": "Umin (%):",
                "max_voltage_level": "Umax (%):",
                "res_separator": "--",
                "res_voltage": "U (V):",
                "res_voltage_level": "U (%):",
            },
            "line": {
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
            },
            "transformer": {
                "id": "Id:",
                "bus_hv_id": "HV Bus:",
                "bus_lv_id": "LV Bus:",
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
                "res_voltages": "U [ʜv,ʟv] (V):",
                "res_voltage_levels": "U [ʜv,ʟv] (%):",
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
