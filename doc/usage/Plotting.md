---
myst:
  html_meta:
    "description lang=en": |
      Learn how to plot an MV or LV network with Roseau Load Flow, a powerful load flow solver for the electrical
      calculation of smart grids.
    "description lang=fr": |
      Apprenez à tracer une carte du réseau MT ou BT avec Roseau Load Flow, solveur d'écoulements de charge pour le
      calcul électrique des réseaux intelligents.
    "keywords lang=fr": simulation, réseau, électrique, carte
    "keywords lang=en": simulation, distribution grid, map,
---

# Plotting a distribution network

On this page, the [folium](https://python-visualization.github.io/folium/index.html) library is used to plot an
`ElectricalNetwork`.

Let's take a MV network from the catalogue:

```pycon
>>> from roseau.load_flow import ElectricalNetwork
>>> en = ElectricalNetwork.from_catalogue(name="MVFeeder210", load_point_name="Winter")
```

The plot will be done from the {doc}`GeoDataFrame <geopandas:docs/reference/geodataframe>` of buses and branches.

```pycon
>>> buses_gdf = en.buses_frame.reset_index()
>>> branches_gdf = en.branches_frame.reset_index()
```

In order to style the buses, a style function, a highlight function and a tooltip are defined. The `"id"` property of
the buses is used to separate the HV/MV substation and the MV/LV substations for the style function. Remaining buses
are junction buses. The color of the buses is changed when highlighted.

```pycon
>>> import folium

>>> def buses_style_function(feature):
...     if feature["properties"]["id"].startswith("HVMV"): # HV/MV substation
...         return {
...             "fill": True,
...             "fillColor": "#000000",
...             "color": "#000000",
...             "fillOpacity": 1,
...             "radius": 7,
...         }
...     elif feature["properties"]["id"].startswith("MVLV"): # MV/LV substations
...         return {
...             "fill": True,
...             "fillColor": "#234e83",
...             "color": "#234e83",
...             "fillOpacity": 1,
...             "radius": 5,
...         }
...     else: # Junctions buses
...         return {
...             "fill": True,
...             "fillColor": "#234e83",
...             "color": "#234e83",
...             "fillOpacity": 1,
...             "radius": 3,
...         }

>>> def buses_highlight_function(feature):
...     return {"color": "#cad40e", "fillColor": "#cad40e"}

>>> buses_tooltip = folium.GeoJsonTooltip(
...     fields=["id", "phases"],
...     aliases=["Id:", "Phases:"],
...     localize=True,
...     sticky=False,
...     labels=True,
...     max_width=800,
... )
```

The same is done for the branches. There are three types of branches: `"line"`, `"transformer"` and `"switch"`. Only
lines are plotted so the opacity of others is set to 0.

```pycon
>>> def branches_style_function(feature):
...     if feature["properties"]["type"] == "line":
...         return {"color": "#234e83", "weight": 4}
...     else:
...         # feature["properties"]["type"] in ("transformer", "switch")
...         return {"opacity": 0}

>>> def branches_highlight_function(feature):
...     return {"color": "#cad40e"}

>>> branches_tooltip = folium.GeoJsonTooltip(
...     fields=["id", "type", "bus1_id", "bus2_id"],
...     aliases=["Id:", "Type:", "Bus1:", "Bus2:"],
...     localize=True,
...     sticky=False,
...     labels=True,
...     max_width=800,
... )
```

Finally, the two geojson layers are added in a folium map.

```pycon
>>> m = folium.Map(
...     location=list(reversed(buses_gdf.unary_union.centroid.coords[0])), zoom_start=12
... )

>>> folium.GeoJson(
...     branches_gdf,
...     name="branches",
...     marker=folium.CircleMarker(),
...     style_function=branches_style_function,
...     highlight_function=branches_highlight_function,
...     tooltip=branches_tooltip,
... ).add_to(m)

>>> folium.GeoJson(
...     buses_gdf,
...     name="buses",
...     marker=folium.CircleMarker(),
...     style_function=buses_style_function,
...     highlight_function=buses_highlight_function,
...     tooltip=buses_tooltip,
... ).add_to(m)

>>> folium.LayerControl().add_to(m)
>>> m
```

It leads to this result:

<iframe src="../_static/Network/MVFeeder210.html" height="600px" width="100%" frameborder="0"></iframe>
