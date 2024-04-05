import re
from pathlib import Path

import folium
import pandas as pd
from branca.element import CssLink, Element, Figure
from jinja2 import Template

from roseau.load_flow import ElectricalNetwork

OUTPUT_DIR = Path("doc") / "_static" / "Network"


def buses_style_function(feature):
    if feature["properties"]["id"].startswith("HVMV"):  # HV/MV substation
        return {
            "fill": True,
            "fillColor": "#000000",
            "color": "#000000",
            "fillOpacity": 1,
            "radius": 7,
        }
    elif feature["properties"]["id"].startswith("MVLV"):  # MV/LV substations
        return {
            "fill": True,
            "fillColor": "#234e83",
            "color": "#234e83",
            "fillOpacity": 1,
            "radius": 5,
        }
    elif feature["properties"]["id"].startswith("MV"):  # MV buses
        return {
            "fill": True,
            "fillColor": "#234e83",
            "color": "#234e83",
            "fillOpacity": 1,
            "radius": 3,
        }
    else:  # LV buses
        return {
            "fill": True,
            "fillColor": "#adb9cb",
            "color": "#adb9cb",
            "fillOpacity": 1,
            "radius": 1,
        }


def buses_highlight_function(feature):
    return {"color": "#cad40e", "fillColor": "#cad40e"}


buses_tooltip = folium.GeoJsonTooltip(
    fields=["id", "phases"],
    aliases=["Id:", "Phases:"],
    localize=True,
    sticky=False,
    labels=True,
    max_width=800,
)


def lines_style_function(feature):
    if feature["properties"]["network"].startswith("MV"):
        return {"color": "#234e83", "weight": 4}
    else:
        return {"color": "#adb9cb", "weight": 3}


def lines_highlight_function(feature):
    return {"color": "#cad40e"}


lines_tooltip = folium.GeoJsonTooltip(
    fields=["id", "bus1_id", "bus2_id", "parameters_id"],
    aliases=["Id:", "Bus1:", "Bus2:", "Parameters:"],
    localize=True,
    sticky=False,
    labels=True,
    max_width=800,
)


class RoseauMap(folium.Map):
    def render(self, title: str | None, **kwargs) -> None:
        """Add the network name to the function signature.

        Args:
            title:
                The pretty version of the network name.

        Keyword Args:
            Traditional render arguments
        """
        figure = self.get_root()
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
        figure.html.add_child(
            Element("{% if kwargs['title'] %}<h1>{{kwargs['title']}}</h1>{% endif %}"), name="h1_title"
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

        super().render(title=title, **kwargs)

        # Add custom css file (at the end of the header)
        figure.header.add_child(CssLink(url="../css/custom.css", download=False), name="custom_css")


def prettify_network_name(name: str) -> str:
    match = re.fullmatch(pattern=r"([LM]V)Feeder([0-9]+)", string=name)
    if match:
        return f"{match.group(1)} Feeder {match.group(2)}"
    else:
        return name


if __name__ == "__main__":
    catalogue_data = ElectricalNetwork.catalogue_data()
    aggregated_buses_gdf_list = []
    aggregated_lines_gdf_list = []
    for network_name in catalogue_data:
        print(f"Plotting network {network_name!r}")
        # Read the network data
        en = ElectricalNetwork.from_catalogue(name=network_name, load_point_name="Winter")
        buses_gdf = en.buses_frame.reset_index()
        lines_gdf = en.lines_frame.reset_index()
        transformers_gdf = en.transformers_frame.reset_index()
        switches_gdf = en.switches_frame.reset_index()
        buses_gdf["network"] = network_name
        lines_gdf["network"] = network_name

        # Create the map
        zoom_start = 12 if network_name.startswith("MV") else 16
        title = prettify_network_name(name=network_name)
        m = RoseauMap(location=list(reversed(buses_gdf.unary_union.centroid.coords[0])), zoom_start=zoom_start)
        folium.GeoJson(
            data=lines_gdf,
            name="lines",
            marker=folium.CircleMarker(),
            style_function=lines_style_function,
            highlight_function=lines_highlight_function,
            tooltip=lines_tooltip,
        ).add_to(m)
        folium.GeoJson(
            data=buses_gdf,
            name="buses",
            marker=folium.CircleMarker(),
            style_function=buses_style_function,
            highlight_function=buses_highlight_function,
            tooltip=buses_tooltip,
        ).add_to(m)
        folium.LayerControl().add_to(m)

        # Save the map
        m.save(outfile=OUTPUT_DIR / f"{network_name}.html", title=title)

        # Aggregate the data frame
        aggregated_buses_gdf_list.append(buses_gdf)
        aggregated_lines_gdf_list.append(lines_gdf)

    # Create the global map
    print("Plotting the global map")
    buses_gdf = pd.concat(objs=aggregated_buses_gdf_list, ignore_index=True)
    lines_gdf = pd.concat(objs=aggregated_lines_gdf_list, ignore_index=True)

    # Create the map
    title = "Available networks"
    m = RoseauMap(location=list(reversed(buses_gdf.unary_union.centroid.coords[0])), zoom_start=9)
    folium.GeoJson(
        data=lines_gdf,
        name="lines",
        marker=folium.CircleMarker(),
        style_function=lines_style_function,
        highlight_function=lines_highlight_function,
        tooltip=lines_tooltip,
    ).add_to(m)
    folium.GeoJson(
        data=buses_gdf,
        name="buses",
        marker=folium.CircleMarker(),
        style_function=buses_style_function,
        highlight_function=buses_highlight_function,
        tooltip=buses_tooltip,
    ).add_to(m)
    folium.LayerControl().add_to(m)

    # Save the map
    m.save(outfile=OUTPUT_DIR / "Catalogue.html", title=None)
