---
myst:
  html_meta:
    "description lang=en": |
      Learn how to plot an MV or LV network with Roseau Load Flow, a powerful load flow solver for the electrical
      calculation of smart grids.
    "description lang=fr": |
      Apprenez à tracer une carte du réseau MT ou BT avec Roseau Load Flow, solveur d'écoulements de charge pour le
      calcul électrique des réseaux intelligents.
    "keywords lang=fr": simulation, réseau, électrique, carte, tracé
    "keywords lang=en": simulation, distribution grid, map, plot
---

# Plotting

_Roseau Load Flow_ provides a few tools to plot electric quantities and networks. The plotting
functions are available in the `roseau.load_flow.plotting` module.

## Plotting a network on a map

The {func}`~roseau.load_flow.plotting.plot_interactive_map` function plots an `ElectricalNetwork`
on a map using the [folium](https://python-visualization.github.io/folium/latest) library. The
function requires that the geometries of the elements are defined in the `ElectricalNetwork`. Only
buses and lines are currently plotted.

The `plot_interactive_map` function uses the `ElectricalNetwork` geo dataframes of buses and lines
to plot the network on a map. The function accepts optional arguments to customize the styles and
highlights of the elements. Refer to the function's documentation for more information.

To plot a network on an interactive map, simply call the `plot_interactive_map` function with an
`ElectricalNetwork`:

```pycon
>>> from roseau.load_flow.plotting import plot_interactive_map
>>> plot_interactive_map(en)
```

Let's take a MV network from the catalogue as an example:

```pycon
>>> import roseau.load_flow as rlf
>>> from roseau.load_flow.plotting import plot_interactive_map
>>> en = rlf.ElectricalNetwork.from_catalogue(name="MVFeeder210", load_point_name="Winter")
>>> en
<ElectricalNetwork: 128 buses, 126 lines, 0 transformers, 1 switch, 82 loads, 1 source, 1 ground, 1 potential ref>
```

As the `id` of the buses of this network contains information about the type of bus, we can use it
to style the buses differently. For example, we can give different styles for the HV/MV substation,
MV/LV substations, and junction buses. `plot_interactive_map` takes an optional `style_function` argument to
customize the style of the plots. The `style_function` is a function that accepts a GeoJSON feature
mapping and returns a dictionary of style properties. The available features are the columns of the
dataframes of the elements of the network in addition to an `"element_type"` key that indicates the
type of the element (bus, line, etc.). The following is an example

```pycon
>>> def style_function(feature: dict) -> dict | None:
...     # If the element is not a bus, use the default style
...     if feature["properties"]["element_type"] != "bus":
...         return None
...     # Override the default style of buses based on the bus id
...     if feature["properties"]["id"].startswith("HVMV"):  # HV/MV substation
...         return {
...             "fill": True,
...             "fillColor": "#000000",
...             "color": "#000000",
...             "fillOpacity": 1,
...             "radius": 7,
...         }
...     elif feature["properties"]["id"].startswith("MVLV"):  # MV/LV substations
...         return {
...             "fill": True,
...             "fillColor": "#234e83",
...             "color": "#234e83",
...             "fillOpacity": 1,
...             "radius": 5,
...         }
...     else:  # Junction buses
...         return {
...             "fill": True,
...             "fillColor": "#234e83",
...             "color": "#234e83",
...             "fillOpacity": 1,
...             "radius": 3,
...         }
...

```

Finally, calling the `plot_interactive_map` function with the custom style function produces an
interactive map of the network:

```pycon
>>> m = plot_interactive_map(en, style_function=style_function)
>>> m
```

<iframe src="../_static/Plotting/MVFeeder210.html" height="500px" width="100%" frameborder="0"></iframe>

## Plotting voltage phasors

The {func}`~roseau.load_flow.plotting.plot_voltage_phasors` function plots the voltage phasors of
a bus, load or source elements in the complex plane. The function takes the element and an optional
matplotlib `Axes` object to plot the voltage phasors. This function is useful to visualize voltage
unbalance in multi-phase systems for instance. Note that the element must have load flow results
available to plot the voltage phasors.

```pycon
>>> import matplotlib.pyplot as plt
>>> import roseau.load_flow as rlf
>>> from roseau.load_flow.plotting import plot_voltage_phasors

>>> bus = rlf.Bus("Bus", phases="abcn")
... source = rlf.VoltageSource("Wye Source", bus, voltages=230, phases="abcn")
... load = rlf.ImpedanceLoad("Delta Load", bus, impedances=50, phases="abc")
... rlf.PotentialRef("PRef", element=bus)
... en = rlf.ElectricalNetwork.from_element(bus)
... en.solve_load_flow()

>>> fig, axes = plt.subplots(1, 2, figsize=(8, 4))
... plot_voltage_phasors(source, ax=axes[0])
... plot_voltage_phasors(load, ax=axes[1])
... plt.show()
```

```{image} /_static/Plotting/Plot_Voltage_Phasors.png
:alt: A plot showing voltage phasors of a wye-connected source and a delta-connected load
:align: center
```

A similar function {func}`~roseau.load_flow.plotting.plot_symmetrical_voltages` plots the symmetrical
components of the voltage phasors of a three-phase bus, load or source.
