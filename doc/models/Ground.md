---
myst:
  html_meta:
    description lang=en: |
      Include Ground elements in your electrical model with Roseau Load Flow - Three-phase unbalanced load flow solver
      in a Python API by Roseau Technologies.
    keywords lang=en: simulation, distribution grid, ground, earth, model
    # spellchecker:off
    description lang=fr: |
      Inclure des éléments Terre dans votre modèle de électrique avec Roseau Load Flow - Solveur d'écoulement de
      charge triphasé et déséquilibré dans une API Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, terre, roseau load flow, modèle
    # spellchecker:on
---

# Ground

## Definition

The `Ground` element represents the Earth as an infinite perfectly-conductive plane. Connections to the ground can be
made with ideal or impedant connections using the `GroundConnection` element. Lines with shunt admittances require a
`Ground` element for their shunt connections. The symbols of `Ground` and `GroundConnection` elements are the following:

```{image} /_static/Ground.svg
---
alt: A diagram of a ground element
width: 200px
align: center
---
```

`Ground` adds the equation $\underline{I_{\mathrm{g}}} = 0$, where $\underline{I_{\mathrm{g}}}$ is the sum of the
currents of all elements connected to the ground. `GroundConnection` adds the equation
$\underline{I} = \frac{\underline{V} - \underline{V_{\mathrm{g}}}}{\underline{Z}}$, where $\underline{I}$ is the current
flowing through the ground connection towards the ground, $\underline{V}$ is the potential of the terminal element
connected to the ground, $\underline{V_{\mathrm{g}}}$ is the potential of the ground and $\underline{Z}$ is the
impedance of the ground connection.

```{warning}
In electrical engineering, it is common to also add the equation $\underline{V_{\mathrm{g}}}=0$ when
defining a ground element. If you want to do so, you must add a `PotentialRef` element as defined in
[](PotentialRef.md).
```

## Available Results

The following results are available for a `Ground` element:

| Result Accessor | Default Unit | Type    | Description                 |
| --------------- | ------------ | ------- | --------------------------- |
| `res_potential` | $V$          | complex | The potential of the ground |

and the following results are available for a `GroundConnection` element:

| Result Accessor | Default Unit | Type    | Description                                       |
| --------------- | ------------ | ------- | ------------------------------------------------- |
| `res_current`   | $A$          | complex | The current flowing through the ground connection |

## Usage

In _Roseau Load Flow_, a `Ground` element is used with:

1. A line with shunt components (i.e, `y_shunt` in `LineParameters` is non-zero).
2. A ground connection (using the `GroundConnection` element) to connect a phase of a bus or other terminal elements to
   the ground.
3. A potential reference (using the `PotentialRef` element) to set the potential of the ground to 0V.

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Define the ground element
gnd = rlf.Ground(id="Gnd")

# Define two buses
bus1 = rlf.Bus(id="Bus1", phases="abcn")
bus2 = rlf.Bus(id="Bus2", phases="abcn")

# Define a voltage source on bus1
vs = rlf.VoltageSource(id="Src", bus=bus1, voltages=rlf.Q_(230, "V"))

# Define the parameters of the lines
lp = rlf.LineParameters(
    id="LP",
    z_line=rlf.Q_((0.12 + 0.1j) * np.eye(4), "ohm/km"),
    y_shunt=rlf.Q_(2e-4j * np.eye(4), "S/km"),
)

# Define a line between bus1 and bus2 (using gnd for the shunt connections)
line = rlf.Line(
    id="Line",
    bus1=bus1,
    bus2=bus2,
    parameters=lp,
    length=rlf.Q_(2, "km"),
    ground=gnd,
)

# Add an unbalanced load on bus2
load = rlf.PowerLoad(id="Load", bus=bus2, powers=rlf.Q_([5.0, 2.5, 0], "kVA"))

# Connect the neutral of bus1 to the ground
gc = rlf.GroundConnection(id="GC", ground=gnd, element=bus1, phase="n")

# Set the potential of the ground element gnd to 0V
pref = rlf.PotentialRef(id="PRef", element=gnd)

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# The potential of gnd is 0V as defined by the potential reference element
en.res_grounds.transform([np.abs, ft.partial(np.angle, deg=True)])
# | ground_id   |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:------------|----------------------------:|-------------------------:|
# | Gnd         |                           0 |                        0 |

# The potential of the neutral of bus1 is 0V as well
en.res_buses.transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:--------------|----------------------------:|-------------------------:|
# | ('Bus1', 'a') |                         230 |                        0 |
# | ('Bus1', 'b') |                         230 |                     -120 |
# | ('Bus1', 'c') |                         230 |                      120 |
# | ('Bus1', 'n') |                           0 |                  21.4768 |
# | ('Bus2', 'a') |                     224.443 |                 -1.13582 |
# | ('Bus2', 'b') |                     227.364 |                 -120.528 |
# | ('Bus2', 'c') |                     230.009 |                  119.997 |
# | ('Bus2', 'n') |                     6.18435 |                  10.2185 |

# Very small current flows through the ground connection as only the shunt admittances
# of the line are connected to the ground
en.res_ground_connections.transform([np.abs, ft.partial(np.angle, deg=True)])
# | connection_id   |   ('current', 'absolute') |   ('current', 'angle') |
# |:----------------|--------------------------:|-----------------------:|
# | GC              |               4.35309e-14 |                 155.81 |

# Now connect the neutral of bus2 to the ground with a 1Ω impedance
gc2 = rlf.GroundConnection(id="GC2", ground=gnd, element=bus2, phase="n", impedance=1)
en.solve_load_flow()

# Now more current flows through the ground connections
en.res_ground_connections.transform([np.abs, ft.partial(np.angle, deg=True)])
# | connection_id   |   ('current', 'absolute') |   ('current', 'angle') |
# |:----------------|--------------------------:|-----------------------:|
# | GC              |                   4.88787 |               -179.052 |
# | GC2             |                   4.88767 |               0.950372 |

# The sum of all currents flowing to the ground is still zero as expected
abs(
    sum(line.side1.res_shunt_currents.m)
    + sum(line.side2.res_shunt_currents.m)
    + gc.res_current.m
    + gc2.res_current.m
)
# 0

# The potential of the neutral of bus2 is now closer to 0V as it is connected
# to the ground with a 1Ω impedance
en.res_buses.transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:--------------|----------------------------:|-------------------------:|
# | ('Bus1', 'a') |                         230 |                        0 |
# | ('Bus1', 'b') |                         230 |                     -120 |
# | ('Bus1', 'c') |                         230 |                      120 |
# | ('Bus1', 'n') |                           0 |                  8.94368 |
# | ('Bus2', 'a') |                     224.496 |                 -1.13599 |
# | ('Bus2', 'b') |                     227.351 |                 -120.533 |
# | ('Bus2', 'c') |                     230.009 |                  119.997 |
# | ('Bus2', 'n') |                     4.88767 |                 0.950372 |
```

## Advanced Usage

In _Roseau Load Flow_, several grounds can be defined to represent separate Earth references. You almost never need to
do that but in case you do, create multiple `Ground` elements and use them independently in the `GroundConnection` and
`Line` elements.

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.Ground
   :members:
   :show-inheritance:
   :no-index:
.. autoapiclass:: roseau.load_flow.models.GroundConnection
   :members:
   :show-inheritance:
   :no-index:
```
