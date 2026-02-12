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

The `Ground` element represents the Earth as an infinite perfect conductor. Connections to the ground can be made with
ideal or impedant connections using the `GroundConnection` element. A ground is mandatory in a line model with shunt
elements. The symbol of a ground element is:

```{image} /_static/Ground.svg
---
alt: A diagram of a ground element
width: 100px
align: center
---
```

This element adds the equation $\underline{I_{\mathrm{g}}} = 0$, where $\underline{I_{\mathrm{g}}}$ is the sum of the
currents of all elements connected to the ground.

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

1. A line with shunt components (mandatory).
2. A ground connection (using the `GroundConnection` element) to connect a phase of a bus or other terminal element to
   the ground.
3. A potential reference (using the `PotentialRef` element) to set the potential of the ground to 0V.

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Define two grounds elements
gnd = rlf.Ground(id="Gnd")

# Define three buses
bus1 = rlf.Bus(id="Bus1", phases="abcn")
bus2 = rlf.Bus(id="Bus2", phases="abcn")

# Define a voltage source on bus1
vs = rlf.VoltageSource(id="Src", bus=bus1, voltages=rlf.Q_(400, "V"))

# Define the parameters of the lines
parameters = rlf.LineParameters(
    id="LP",
    z_line=rlf.Q_((0.12 + 0.1j) * np.eye(4), "ohm/km"),
    y_shunt=rlf.Q_(2e-4j * np.eye(4), "S/km"),
)

# Define a line between bus1 and bus2 (using gnd for the shunt connections)
line = rlf.Line(
    id="Line",
    bus1=bus1,
    bus2=bus2,
    parameters=parameters,
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

# Get the ground potentials
# The potential of gnd is 0 as defined by the potential reference element
en.res_grounds.transform([np.abs, ft.partial(np.angle, deg=True)])
# | ground_id   |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:------------|----------------------------:|-------------------------:|
# | Gnd         |                           0 |                        0 |

# As requested, the potential of the neutral of bus1 is zero
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
```

## Advanced Usage

In _Roseau Load Flow_, several grounds can be defined leading to ground elements with a non-zero potential. Here is an
example with two ground elements `g1` and `g2`.

After solving this load flow, the following assertions will be verified:

- The potential of the ground `g1` will be 0V as defined by the potential reference `pref`.
- There is no reason for the potential of `g2` to be zero too.
- The sum of currents flowing through the shunt admittances of the second line will be zero as they are all connected to
  the ground `g2` and no other elements are connected to this ground.
- The sum of currents flowing through the shunt admittances of the first line will be equal to the sum of the currents
  of the elements connected to phase "a" of the first bus.
  <!-- TODO: add an example when we have the shunt currents of the line -->

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Define two grounds elements
g1 = rlf.Ground(id="g1")
g2 = rlf.Ground(id="g2")

# Define three buses
bus1 = rlf.Bus(id="bus1", phases="abc")
bus2 = rlf.Bus(id="bus2", phases="abc")
bus3 = rlf.Bus(id="bus3", phases="abc")

# Define a voltage source on the first bus
un = 400
vs = rlf.VoltageSource(id="source", bus=bus1, voltages=rlf.Q_(un, "V"))

# Define the impedance and admittance parameters of the lines (can be reused)
parameters = rlf.LineParameters(
    id="parameters",
    z_line=rlf.Q_((0.12 + 0.1j) * np.eye(3), "ohm/km"),
    y_shunt=rlf.Q_(2e-4j * np.eye(3), "S/km"),
)

# Define a line between bus1 and bus2 (using g1 for the shunt connections)
line1 = rlf.Line(
    id="line1",
    bus1=bus1,
    bus2=bus2,
    parameters=parameters,
    length=rlf.Q_(2, "km"),
    ground=g1,
)

# Define a line between bus2 and bus3 (using g2 for the shunt connections)
line2 = rlf.Line(
    id="line2",
    bus1=bus2,
    bus2=bus3,
    parameters=parameters,
    length=rlf.Q_(2.5, "km"),
    ground=g2,
)

# Add a load on bus3
load = rlf.PowerLoad(
    id="load",
    bus=bus3,
    powers=rlf.Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA"),
)

# Connect the phase "a" of the first bus to the ground g1
gc = rlf.GroundConnection(id="gc", ground=g1, element=bus1, phase="a")

# Set the potential of the ground element g1 to 0V
pref = rlf.PotentialRef(id="pref", element=g1)

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# Get the ground potentials
# The potential of g1 is 0 as defined by the potential reference element
# The potential of g2 has no reason to be zero
en.res_grounds.transform([np.abs, ft.partial(np.angle, deg=True)])
# | ground_id   |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:------------|----------------------------:|-------------------------:|
# | g1          |                       0     |                    0     |
# | g2          |                     230.949 |                  149.997 |

# As requested, the potential of the phase "a" of bus1 is zero
en.res_buses.transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:--------------|----------------------------:|-------------------------:|
# | ('bus1', 'a') |                     0       |                    0     |
# | ('bus1', 'b') |                   400       |                 -180     |
# | ('bus1', 'c') |                   400       |                  120     |
# | ('bus2', 'a') |                     4.19152 |                 -126.007 |
# | ('bus2', 'b') |                   398.525   |                  179.238 |
# | ('bus2', 'c') |                   397.913   |                  120.016 |
# | ('bus3', 'a') |                     9.41474 |                 -126.102 |
# | ('bus3', 'b') |                   396.739   |                  178.283 |
# | ('bus3', 'c') |                   395.28    |                  120.043 |

# The requested voltages of the voltage sources are respected
en.res_buses_voltages[["voltage"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'ab') |                   400     |            6.31922e-19 |
# | ('bus1', 'bc') |                   400     |         -120           |
# | ('bus1', 'ca') |                   400     |          120           |
# | ('bus2', 'ab') |                   396.121 |           -1.25675     |
# | ('bus2', 'bc') |                   393.528 |         -120.45        |
# | ('bus2', 'ca') |                   399.634 |          119.467       |
# | ('bus3', 'ab') |                   391.499 |           -2.85404     |
# | ('bus3', 'bc') |                   385.429 |         -121.026       |
# | ('bus3', 'ca') |                   399.18  |          118.807       |
```

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
