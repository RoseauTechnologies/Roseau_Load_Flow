import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import folium
from branca.element import CssLink, Element, Figure
from jinja2 import Template

import roseau.load_flow as rlf
from roseau.load_flow.plotting import _scalar_if_unique
from roseau.load_flow.typing import Id

OUTPUT_DIR = Path("doc") / "_static" / "Network"

if TYPE_CHECKING:
    type FeatureMap = dict[str, Any]
    type StyleDict = dict[str, Any]

type MapElementType = Literal["bus", "line", "transformer"]


def enhance_map(map: "folium.Map", title: str) -> "folium.Map":
    """Add the network name to the function signature.

    Args:
        map:
            The map to enhance.

        title:
            The pretty version of the network name.
    """
    figure = map.get_root()
    assert isinstance(figure, Figure), "You cannot render this Element if it is not in a Figure."

    # Add a title to the figure
    figure.title = title

    # Add description and keywords in the headers
    figure.header.add_child(
        Element(
            '<meta content="The Roseau Load Flow solver includes 40 medium and low voltage distribution networks." '
            'lang="en" name="description" xml:lang="en"/>'
        ),
        name="meta_description",
    )
    figure.header.add_child(
        Element(
            '<meta content="distribution grid, network data, lv network, mv network, free" lang="en" '
            'name="keywords" xml:lang="en"/>'
        ),
        name="meta_keywords",
    )

    # Add a H1 section in the body
    figure.header.add_child(
        Element("{% if kwargs['title'] %}<style>h1 {text-align: center;}</style>{% endif %}"),
        name="h1_css_style",
    )
    figure.html.add_child(Element("{% if kwargs['title'] %}<h1>{{kwargs['title']}}</h1>{% endif %}"), name="h1_title")

    # Modify the template of the figure to add the lang to the HTML document
    figure._template = Template(
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"  # <---- Modified here
        "<head>\n"
        "{% if this.title %}<title>{{this.title}}</title>{% endif %}"
        "    {{this.header.render(**kwargs)}}\n"
        "</head>\n"
        "<body>\n"
        "    {{this.html.render(**kwargs)}}\n"
        "</body>\n"
        "<script>\n"
        "    {{this.script.render(**kwargs)}}\n"
        "</script>\n"
        "</html>\n",
    )

    # Add custom CSS file (at the end of the header)
    figure.header.add_child(CssLink(url="../css/custom.css", download=False), name="custom_css")

    return m


def prettify_network_name(name: str) -> str:
    match = re.fullmatch(pattern=r"([LM]V)Feeder([0-9]+)", string=name)
    if match:
        return f"{match.group(1)} Feeder {match.group(2)}"
    else:
        return name


if __name__ == "__main__":
    catalogue_data = rlf.ElectricalNetwork.catalogue_data()

    #
    # Plot individual maps
    #
    for network_name in catalogue_data:
        print(f"Plotting network {network_name!r}")

        # Read the network data
        en = rlf.ElectricalNetwork.from_catalogue(name=network_name, load_point_name="Winter")

        # Plot the network
        m = rlf.plotting.plot_interactive_map(en)

        # Add some elements for Google Index
        title = prettify_network_name(name=network_name)
        m = enhance_map(map=m, title=title)

        # Save the map
        m.save(outfile=OUTPUT_DIR / f"{network_name}.html", title=title)

    #
    # Plot the global map
    #
    # This code is absolutely not optimised and well-written!
    print("Plotting the global map")
    m = folium.Map()

    mv, lv = 60e3, 1e3
    style_color: str = "#234e83"

    def style_color_callback(et):
        return "#000000" if et == "transformer" else style_color

    highlight_color: str = "#cad40e"
    add_tooltips: bool = True
    add_popups: bool = True
    add_search: bool = True
    fit_bounds: bool = True

    fields = {
        "bus": {
            "network": "Network: ",
            "id": "Id:",
            "phases": "Phases:",
            "nominal_voltage": "Un (V):",
            "min_voltage_level": "Umin (%):",
            "max_voltage_level": "Umax (%):",
        },
        "line": {
            "network": "Network: ",
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
            "network": "Network: ",
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
    }

    def internal_style_function(feature):
        # Default style
        e_type = feature["properties"]["element_type"]
        style_color = style_color_callback(e_type)
        if e_type == "bus":
            vn: int | float = feature["properties"]["approximate_nominal_voltage"]
            is_source: bool = feature["properties"]["is_source"]
            if is_source:
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
            line_type: rlf.LineType | None = feature["properties"]["line_type"]
            vn: int | float = feature["properties"]["approximate_nominal_voltage"]
            if vn < lv:
                weight = 1.5  # LV
            elif vn < mv:
                weight = 3.0  # MV
            else:
                weight = 4.5  # HV
            dash_array = "5, 5" if line_type == rlf.LineType.UNDERGROUND else None
            return {"color": style_color, "weight": weight, "dashArray": dash_array}
        elif e_type == "transformer":
            bus_hv_is_source = feature["properties"]["bus_hv_is_source"]
            bus_lv_is_source = feature["properties"]["bus_lv_is_source"]
            vn: int | float = feature["properties"]["approximate_hv_nominal_voltage"]
            if bus_hv_is_source or bus_lv_is_source:
                radius, margin = 15, -1
            else:
                if vn < lv:
                    radius, margin = 5, 3  # LV
                elif vn < mv:
                    radius, margin = 10, 1  # MV
                else:
                    radius, margin = 15, -1  # HV
            tr_color = style_color
            hv_color = style_color_callback("bus")
            lv_color = style_color_callback("bus")
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

    for network_name in catalogue_data:
        pretty_network_name = prettify_network_name(name=network_name)
        network = rlf.ElectricalNetwork.from_catalogue(name=network_name, load_point_name="Winter")

        buses_gdf = network.buses_frame
        buses_gdf["network"] = pretty_network_name
        buses_gdf["element_type"] = "bus"
        buses_gdf["min_voltage_level"] *= 100  # Convert to percentage
        buses_gdf["max_voltage_level"] *= 100  # Convert to percentage
        source_buses = {src.bus.id for src in network.sources.values()}
        buses_gdf["is_source"] = False
        for bus_id in source_buses:
            buses_gdf.at[bus_id, "is_source"] = True

        nominal_voltages = network._get_nominal_voltages()
        buses_gdf["approximate_nominal_voltage"] = None
        for bus_id, value in nominal_voltages.items():
            buses_gdf.at[bus_id, "approximate_nominal_voltage"] = value
        buses_gdf.reset_index(inplace=True)

        lines_gdf = network.lines_frame
        lines_gdf.reset_index(inplace=True)
        lines_gdf["network"] = pretty_network_name
        lines_gdf["element_type"] = "line"
        lines_gdf["max_loading"] *= 100  # Convert to percentage
        lines_gdf[["ampacity", "section", "line_type", "material", "insulator", "approximate_nominal_voltage"]] = None
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
            bus1_id = lines_gdf.at[idx, "bus1_id"]
            lines_gdf.at[idx, "approximate_nominal_voltage"] = nominal_voltages.get(bus1_id)

        transformers_gdf = network.transformers_frame
        transformers_gdf.reset_index(inplace=True)
        transformers_gdf["network"] = pretty_network_name
        transformers_gdf["element_type"] = "transformer"
        transformers_gdf["tap"] *= 100  # Convert to percentage
        transformers_gdf[["hv_side", "lv_side"]] = ""
        transformers_gdf[
            ["vg", "sn", "uhv", "ulv", "bus_hv_is_source", "bus_lv_is_source", "approximate_hv_nominal_voltage"]
        ] = None
        for idx in transformers_gdf.index:
            tr_id: Id = transformers_gdf.at[idx, "id"]  # type: ignore
            # Replace geometry with that of the HV bus
            bus_hv_id: Id = transformers_gdf.at[idx, "bus_hv_id"]  # type: ignore
            bus_lv_id: Id = transformers_gdf.at[idx, "bus_lv_id"]  # type: ignore
            transformers_gdf.at[idx, "geometry"] = network.buses[bus_hv_id].geometry  # type: ignore
            lp = network.transformers[tr_id].parameters
            transformers_gdf.at[idx, "vg"] = lp.vg
            transformers_gdf.at[idx, "sn"] = lp._sn / 1e3  # Convert to kVA
            transformers_gdf.at[idx, "uhv"] = lp._uhv
            transformers_gdf.at[idx, "ulv"] = lp._ulv
            transformers_gdf.at[idx, "bus_hv_is_source"] = bus_hv_id in source_buses
            transformers_gdf.at[idx, "bus_lv_is_source"] = bus_lv_id in source_buses
            transformers_gdf.at[idx, "approximate_hv_nominal_voltage"] = nominal_voltages.get(bus_hv_id)

        dataframes = {"bus": buses_gdf, "line": lines_gdf, "transformer": transformers_gdf}

        # Filter out transformer buses, these are represented by the transformers themselves
        transformer_buses = {side.bus.id for tr in network.transformers.values() for side in (tr.side_hv, tr.side_lv)}
        dataframes["bus"] = dataframes["bus"].loc[~dataframes["bus"]["id"].isin(transformer_buses)]

        tooltips: dict["MapElementType", folium.GeoJsonTooltip | None] = {}
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
                    fields=list(e_fields.keys()), aliases=list(e_fields.values()), localize=True, labels=True
                )
        else:
            popups = dict.fromkeys(fields.keys(), None)

        network_layer = folium.FeatureGroup(name=network_name).add_to(m)
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
                # ).add_to(FeatureGroupSubGroup(network_layer, name).add_to(m))
            ).add_to(network_layer)

    folium.LayerControl(collapsed=False, draggable=True, position="bottomright").add_to(m)
    folium.FitOverlays(padding=30).add_to(m)

    m = enhance_map(map=m, title="Available networks")

    # Hide the ReadTheDoc flyout in the Catalogue.html file
    m.get_root().header.add_child(Element("<style> readthedocs-flyout { visibility: hidden; }</style>"))

    # Save the map
    m.save(outfile=OUTPUT_DIR / "Catalogue.html", title=None)
