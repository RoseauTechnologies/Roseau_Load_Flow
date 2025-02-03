---
myst:
  html_meta:
    "description lang=en": |
      Include Ground elements in your electrical model with Roseau Load Flow - Three-phase unbalanced load flow solver
      in a Python API by Roseau Technologies.
    "description lang=fr": |
      Inclure des éléments Terre dans votre modèle de électrique avec Roseau Load Flow - Solveur d'écoulement de
      charge triphasé et déséquilibré dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, terre, roseau load flow, modèle
    "keywords lang=en": simulation, distribution grid, ground, earth, model
---

# Ground

## Definition

The ground element represents an earth connection where the earth is represented as an ideal
conductor. The symbol of a ground element is:

```{image} /_static/Ground.svg
:alt: A diagram of a ground element
:width: 100px
:align: center
```

This element adds the equation $\underline{I_{\mathrm{g}}} = 0$, where $\underline{I_{\mathrm{g}}}$
is the sum of the currents of all elements connected to the ground.

```{warning}
In electrical engineering, it is common to also add the equation $\underline{V_{\mathrm{g}}}=0$ when
defining a ground element. If you want to do so, you must add a `PotentialRef` element as defined in
[](PotentialRef.md).
```

Lines with shunt elements require a ground element to be defined. Terminal elements like buses,
loads, and sources, can also be connected to a ground, although it is not mandatory. Transformers
can also be optionally connected to a ground on either of their sides. Several elements can be
connected to the same ground and a single element can be connected to multiple grounds.

## Usage

In _Roseau Load Flow_, you can define distinct ground elements using the `Ground` class. This class
only takes an `id` as an argument.

To connect a bus, load, or source element to a ground, use the element's `connect_ground` method and
pass it the ground element and the phase to connect to the ground (defaults to the neutral phase, if
available).

```python
import roseau.load_flow as rlf

# Define a ground element
g = rlf.Ground(id="g")

# Define a bus
bus = rlf.Bus(id="bus", phases="abcn")

# Connect the neutral phase of the bus to the ground
bus.connect_ground(g, phase="n")  # phase="n" is the default
```

For transformers, use the `connect_ground_hv` method to connect the HV side to a ground and the
`connect_ground_lv` method to connect the LV side to a ground.

```python
import roseau.load_flow as rlf

# Define a ground element
g = rlf.Ground(id="g")

# Define two buses
bus_hv = rlf.Bus(id="bus_hv", phases="abc")
bus_lv = rlf.Bus(id="bus_lv", phases="abcn")

# Define a transformer
tp = rlf.TransformerParameters(
    id="tp", vg="Ynzn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j
)
tr = rlf.Transformer(id="tr", bus_hv=bus_hv, bus_lv=bus_lv, parameters=tp)

# Connect the neutral of LV side of the transformer to the ground
tr.connect_ground_lv(g, phase="n")
# equivalently, the neutral of the LV bus can be connected to the ground
# because the transformer's neutral is connected to the LV bus's neutral
bus_lv.connect_ground(g, phase="n")

# The HV side can also be connected to the ground
tr.connect_ground_hv(g, phase="n")
# here the transformer's HV neutral was floating, so we could not connect
# it to the ground via the HV bus which has a separate neutral
```

Lines with shunt elements require a ground element to be passed to their constructor.

```python
import numpy as np
import roseau.load_flow as rlf

# Define two grounds elements
g = rlf.Ground(id="g")

# Define three buses
bus1 = rlf.Bus(id="bus1", phases="abc")
bus2 = rlf.Bus(id="bus2", phases="abc")

# Define a line between bus1 and bus2 (using g for the shunt connections)
lp = rlf.LineParameters(
    id="lp",
    z_line=(0.12 + 0.1j) * np.eye(3),
    y_shunt=2e-4j * np.eye(3),  # <- the shunt admittance
)
line1 = rlf.Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=2, ground=g)
```

In the following more advanced example, we demonstrate the flexibility of our design by defining two
grounds `g1` and `g2`. After solving this load flow, the following assertions will be verified:

- The potential of the ground `g1` will be 0V as set by the potential reference `pref`.
- There is no reason for the potential of `g2` to be zero too.
- The sum of the currents flowing through the shunt admittances of the second line will be zero as
  they are all connected to the ground `g2` and no other elements are connected to this ground.
- The sum of the currents flowing through the shunt admittances of the first line will be equal to
  the sum of the currents of the elements connected to phase "a" of the first bus.

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
vs = rlf.VoltageSource(id="source", bus=bus1, voltages=rlf.Q_(400, "V"))

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

# Connect phase "a" of the first bus to the ground g1
bus1.connect_ground(g1, phase="a")

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

# The sum of the shunt currents of line2 is zero (separate ground g2)
sum(sum(line2.res_shunt_currents))
# (1.388e-17+3.469e-17j) ampere

# The sum of the shunt currents of line1 is equal to the total current
# of the phase "a" of elements of the first bus (shared ground g1)
sum(sum(line1.res_shunt_currents))
# (-0.13857-0.24000j) ampere
vs.res_currents[0] + line1.res_currents[0][0]
# (-0.13857-0.24000j) ampere
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.Ground
   :members:
   :show-inheritance:
   :no-index:
```
