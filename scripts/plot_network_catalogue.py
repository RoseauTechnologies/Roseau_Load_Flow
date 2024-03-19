from pathlib import Path

import folium
import pandas as pd

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


def branches_style_function(feature):
    if feature["properties"]["type"] == "line":
        if feature["properties"]["network"].startswith("MV"):
            return {"color": "#234e83", "weight": 4}
        else:
            return {"color": "#adb9cb", "weight": 2}
    else:
        # feature["properties"]["type"] in ("transformer", "switch")
        return {"opacity": 0}


def branches_highlight_function(feature):
    return {"color": "#cad40e"}


branches_tooltip = folium.GeoJsonTooltip(
    fields=["id", "type", "bus1_id", "bus2_id"],
    aliases=["Id:", "Type:", "Bus1:", "Bus2:"],
    localize=True,
    sticky=False,
    labels=True,
    max_width=800,
)


if __name__ == "__main__":
    catalogue_data = ElectricalNetwork.catalogue_data()
    aggregated_buses_gdf_list = []
    aggregated_branches_gdf_list = []
    for network_name in catalogue_data:
        print(f"Plotting network {network_name}")
        # Read the network data
        en = ElectricalNetwork.from_catalogue(name=network_name, load_point_name="Winter")
        buses_gdf = en.buses_frame.reset_index()
        branches_gdf = en.branches_frame.reset_index()
        buses_gdf["network"] = network_name
        branches_gdf["network"] = network_name

        # Create the map
        zoom_start = 12 if network_name.startswith("MV") else 16
        m = folium.Map(location=list(reversed(buses_gdf.unary_union.centroid.coords[0])), zoom_start=zoom_start)
        folium.GeoJson(
            branches_gdf,
            name="branches",
            marker=folium.CircleMarker(),
            style_function=branches_style_function,
            highlight_function=branches_highlight_function,
            tooltip=branches_tooltip,
        ).add_to(m)
        folium.GeoJson(
            buses_gdf,
            name="buses",
            marker=folium.CircleMarker(),
            style_function=buses_style_function,
            highlight_function=buses_highlight_function,
            tooltip=buses_tooltip,
        ).add_to(m)
        folium.LayerControl().add_to(m)

        # Save the map
        m.save(OUTPUT_DIR / f"{network_name}.html")

        # Aggregate the data frame
        aggregated_buses_gdf_list.append(buses_gdf)
        aggregated_branches_gdf_list.append(branches_gdf)

    # Create the global map
    print("Plotting the global map")
    buses_gdf = pd.concat(aggregated_buses_gdf_list, ignore_index=True)
    branches_gdf = pd.concat(aggregated_branches_gdf_list, ignore_index=True)

    # Update the tooltips
    buses_tooltip = folium.GeoJsonTooltip(
        fields=["network", "id", "phases"],
        aliases=["Network:", "Id:", "Phases:"],
        localize=True,
        sticky=False,
        labels=True,
        max_width=800,
    )
    branches_tooltip = folium.GeoJsonTooltip(
        fields=["network", "id", "type", "bus1_id", "bus2_id"],
        aliases=["Network:", "Id:", "Type:", "Bus1:", "Bus2:"],
        localize=True,
        sticky=False,
        labels=True,
        max_width=800,
    )

    # Create the map
    m = folium.Map(location=list(reversed(buses_gdf.unary_union.centroid.coords[0])), zoom_start=9)
    folium.GeoJson(
        branches_gdf,
        name="branches",
        marker=folium.CircleMarker(),
        style_function=branches_style_function,
        highlight_function=branches_highlight_function,
        tooltip=branches_tooltip,
    ).add_to(m)
    folium.GeoJson(
        buses_gdf,
        name="buses",
        marker=folium.CircleMarker(),
        style_function=buses_style_function,
        highlight_function=buses_highlight_function,
        tooltip=buses_tooltip,
    ).add_to(m)
    folium.LayerControl().add_to(m)

    # Save the map
    m.save(OUTPUT_DIR / "Catalogue.html")
