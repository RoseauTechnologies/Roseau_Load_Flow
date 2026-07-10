import re
from pathlib import Path

import folium
from jinja2 import Template

import roseau.load_flow as rlf
from roseau.load_flow.plotting import (
    _DEFAULT_MAP_STYLE_COLORS,
    _MAP_FIELDS,
    _get_buses_data_for_map_plot,
    _get_lines_data_for_map_plot,
    _get_switches_data_for_map_plot,
    _get_transformers_data_for_map_plot,
    _make_style_color_callback,
    _plot_interactive_map_elements,
)

OUTPUT_DIR = Path("doc") / "_static" / "Network"


def enhance_map(map: "folium.Map", title: str, hide_readthedocs_flyout: bool = False) -> "folium.Map":
    """Add the network name to the function signature.

    Args:
        map:
            The map to enhance.

        title:
            The pretty version of the network name.
    """
    figure = map.get_root()
    assert isinstance(figure, folium.Figure), "You cannot render this Element if it is not in a Figure."

    # Add a title to the figure
    figure.title = title

    # Add description and keywords in the headers
    figure.header.add_child(
        folium.Element(
            '<meta content="The Roseau Load Flow solver includes 40 medium and low voltage distribution networks." '
            'lang="en" name="description" xml:lang="en"/>'
        ),
        name="meta_description",
    )
    figure.header.add_child(
        folium.Element(
            '<meta content="distribution grid, network data, lv network, mv network, free" lang="en" '
            'name="keywords" xml:lang="en"/>'
        ),
        name="meta_keywords",
    )

    # Add a H1 section in the body
    figure.header.add_child(
        folium.Element("{% if kwargs['title'] %}<style>h1 {text-align: center;}</style>{% endif %}"),
        name="h1_css_style",
    )
    figure.html.add_child(
        folium.Element("{% if kwargs['title'] %}<h1>{{kwargs['title']}}</h1>{% endif %}"), name="h1_title"
    )

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
    figure.header.add_child(folium.CssLink(url="../css/custom.css", download=False), name="custom_css")

    # Hide the ReadTheDoc flyout in the Catalogue.html file
    if hide_readthedocs_flyout:
        figure.header.add_child(folium.Element("<style> readthedocs-flyout { visibility: hidden; }</style>"))

    # Add a custom script to enable highlighting of the markers
    figure.script.add_child(
        folium.Element(
            "L.Marker.include({"
            "  setStyle: function (style) {"
            "    this.setIcon(L.divIcon(Object.assign({}, this.options.icon.options, style)));"
            "  }"
            "});"
        )
    )

    return map


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
        pretty_network_name = prettify_network_name(name=network_name)

        # Read the network data
        en = rlf.ElectricalNetwork.from_catalogue(name=network_name, load_point_name="Winter")
        en.name = pretty_network_name

        # Plot the network
        m = rlf.plotting.plot_interactive_map(en)

        # Add some elements for Google Index
        m = enhance_map(map=m, title=pretty_network_name)

        # Save the map
        m.save(outfile=OUTPUT_DIR / f"{network_name}.html", title=pretty_network_name)

    #
    # Plot the global map
    #
    print("Plotting the global map")
    m = folium.Map(tiles="cartodbpositron")
    mv_feeders_layer = folium.FeatureGroup(name="MV Feeders").add_to(m)
    lv_feeders_layer = folium.FeatureGroup(name="LV Feeders").add_to(m)
    for network_name in catalogue_data:
        pretty_network_name = prettify_network_name(name=network_name)
        network = rlf.ElectricalNetwork.from_catalogue(name=network_name, load_point_name="Winter")
        buses_gdf = _get_buses_data_for_map_plot(network=network, with_results=False)
        lines_gdf = _get_lines_data_for_map_plot(network=network, with_results=False)
        transformers_gdf = _get_transformers_data_for_map_plot(
            network=network, with_results=False, buses_frame=buses_gdf
        )
        switches_gdf = _get_switches_data_for_map_plot(network=network, with_results=False)
        network_layer = folium.FeatureGroup(name=pretty_network_name).add_to(
            mv_feeders_layer if network_name.startswith("MVFeeder") else lv_feeders_layer
        )
        for element_layer in _plot_interactive_map_elements(
            network=network,
            dataframes={"bus": buses_gdf, "line": lines_gdf, "transformer": transformers_gdf, "switch": switches_gdf},
            fields=_MAP_FIELDS,
            style_color_callback=_make_style_color_callback(None, lambda et, eid: _DEFAULT_MAP_STYLE_COLORS[et]),
            highlight_color="#cad40e",
            style_function=None,
            highlight_function=None,
            add_tooltips=True,
            add_popups=True,
        ).values():
            element_layer.add_to(network_layer)

    folium.LayerControl(collapsed=False, draggable=True, position="bottomright").add_to(m)
    folium.FitOverlays(padding=30).add_to(m)

    m = enhance_map(map=m, title="Available networks", hide_readthedocs_flyout=True)

    # Save the map
    m.save(outfile=OUTPUT_DIR / "Catalogue.html", title=None)
