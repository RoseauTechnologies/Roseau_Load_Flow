---
myst:
  html_meta:
    description lang=en: |
      Learn how to plot an MV or LV network with Roseau Load Flow, a powerful load flow solver for the electrical
      calculation of smart grids.
    keywords lang=en: simulation, distribution grid, map, plot
    # spellchecker:off
    description lang=fr: |
      Apprenez à tracer une carte du réseau MT ou BT avec Roseau Load Flow, solveur d'écoulements de charge pour le
      calcul électrique des réseaux intelligents.
    keywords lang=fr: simulation, réseau, électrique, carte, tracé
    # spellchecker:on
---

# Plotting

_Roseau Load Flow_ provides plotting functionality in the `rlf.plotting` module.

## Plotting a network on a map

The simplest way to visualize an electrical network with bus and line geometries is to plot it on a map using the
{func}`~roseau.load_flow.plotting.plot_interactive_map` function. Example:

```pycon
>>> import roseau.load_flow as rlf
>>> en = rlf.ElectricalNetwork.from_catalogue(name="MVFeeder210", load_point_name="Winter")
>>> en
<ElectricalNetwork: 128 buses, 126 lines, 0 transformers, 1 switch, 82 loads, 1 source, 1 ground, 1 potential ref, 0 ground connections>
>>> rlf.plotting.plot_interactive_map(en)
```

<iframe src="../_static/Plotting/MVFeeder210.html" height="500px" width="100%" frameborder="0"></iframe>

Make sure you have [folium](https://python-visualization.github.io/folium/latest) installed in your Python environment
and that your network has a coordinate reference system (CRS) set via the `en.crs` attribute.

### Features

1. **Interactive map**: zoom in/out, pan, hover or click on elements to see their properties
2. **Base maps**: all
   [folium tilesets](https://python-visualization.github.io/folium/latest/getting_started.html#Choosing-a-tileset) are
   supported
3. **Search**: search for specific elements by their ID
4. **Line laying**: underground cables are dashed, other lines are solid
5. **Voltage levels**: HV/MV/LV elements have different sizes for easier identification
6. **Layer control**: toggle visibility of buses, lines, transformers
7. **Custom styling**: customize colors, sizes, and styles of elements based on their properties.

Use the `map_kws` keyword to pass additional arguments to the `folium.Map` constructor. Refer to the function's
documentation for more details.

**Note**

Only buses, lines and transformers are currently plotted.

## Plotting a network with results on a map

The {func}`~roseau.load_flow.plotting.plot_results_interactive_map` function can be used to plot load flow results on
the map. The network must have valid results before calling this function. Example:

```pycon
>>> import roseau.load_flow as rlf
>>> en = rlf.ElectricalNetwork.from_catalogue(name="MVFeeder210", load_point_name="Winter")
>>> # Let's create some extreme conditions to see  voltage drops/rises and line overloads
>>> en.loads["MVLV14633_consumption"].powers = 3.5e6
>>> en.loads["MVLV15838_production"].powers = -5.5e6
>>> en.solve_load_flow()
(3, 3.725290298461914e-09)
>>> rlf.plotting.plot_results_interactive_map(en)
```

<iframe src="../_static/Plotting/MVFeeder210_Results.html" height="500px" width="100%" frameborder="0"></iframe>

The plot shows the color-coded voltage levels at buses and color-coded loading of lines and transformers. The following
states are represented:

- **very-low (blue)**: bus voltage below {math}`U_{min}`
- **low (light blue)**: bus voltage in the first quadrant of the {math}`(U_{min}, U_{n})` range
- **normal (green)**: bus voltage in the last three quadrants of the {math}`(U_{min}, U_{n})` range or in the first
  three quadrants of the {math}`(U_{n}, U_{max})` range; line or transformer loading below 75% {math}`load_{max}`
- **high (orange)**: bus voltage in the last quadrant of the {math}`(U_{n}, U_{max})` range; line or transformer loading
  between 75% and 100% {math}`load_{max}`
- **very-high (red)**: bus voltage above {math}`U_{max}`; line or transformer loading above 100% {math}`load_{max}`
- **unknown (gray)**: bus nominal voltage or limits not defined; line ampacity not defined

```{image} /_static/Plotting/Result_States.png
---
alt: The different states for bus voltages and line/transformer loadings
align: center
---
```

## Plotting a network with no geometries

If the network does not have geometries defined for its elements, the `plot_interactive_map` function will not work. In
this case, you can use the {meth}`~roseau.load_flow.ElectricalNetwork.to_graph` method to convert the network to a
networkx `MultiGraph` and plot it using the `networkx` library. In the following example we plot the graph of the
network `MVFeeder210` from the previous example:

```pycon
>>> import networkx as nx
... import roseau.load_flow as rlf
... en = rlf.ElectricalNetwork.from_catalogue(name="MVFeeder210", load_point_name="Winter")
... for bus in en.buses.values():
...     bus.geometry = None  # Pretend buses don't have geometries
... G = en.to_graph()
... nx.draw(G, node_size=50)  # This works even if the geometries are not defined
```

```{image} /_static/Plotting/MVFeeder210_Graph_No_Geometries.png
---
alt: The graph of the network MVFeeder210 with no geometries using networkx
align: center
---
```

See the [networkx docs](https://networkx.org/documentation/stable/tutorial.html#drawing-graphs) for more information.

## Plotting voltage phasors

The {func}`~roseau.load_flow.plotting.plot_voltage_phasors` function plots the voltage phasors of a bus, load or source
in the complex plane. This function can be used to visualize voltage unbalance in multi-phase systems for instance. It
takes the element and an optional matplotlib `Axes` object to use for the plot. Note that the element must have load
flow results to plot the voltage phasors.

```pycon
>>> import matplotlib.pyplot as plt
... import roseau.load_flow as rlf
... from roseau.load_flow.plotting import plot_voltage_phasors

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
---
alt: The voltage phasors of a wye-connected source and a delta-connected load
align: center
---
```

A similar function {func}`~roseau.load_flow.plotting.plot_symmetrical_voltages` plots the symmetrical components of the
voltage phasors of a three-phase bus, load or source.
