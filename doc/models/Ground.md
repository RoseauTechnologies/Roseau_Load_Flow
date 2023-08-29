# Ground

## Definition

The ground element represents an earth connection where the earth is represented as an ideal
conductor. A ground can be used to connect several elements. A ground is mandatory in a line
model with shunt elements. The symbol of a ground element is:

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

## Usage

In _Roseau Load Flow_, several grounds can be defined leading to ground elements with a non-zero
potential. Here is an example with two ground elements `g1` and `g2`.

After solving this load flow, the following assertions will be verified:

- The potential of the ground `g1` will be 0V as defined by the potential reference `pref`.
- There is no reason for the potential of `g2` to be zero too.
- The sum of currents flowing through the shunt admittances of the second line will be zero as they
  are all connected to the ground `g2` and no other elements are connected to this ground.
- The sum of currents flowing through the shunt admittances of the first line will be equal to the
  sum of the currents of the elements connected to phase "a" of the first bus.
  <!-- TODO: add an example when we have the shunt currents of the line -->

```python
import functools as ft
import numpy as np
from roseau.load_flow import (
    Q_,
    Bus,
    ElectricalNetwork,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    VoltageSource,
)

# Define two grounds elements
g1 = Ground(id="g1")
g2 = Ground(id="g2")

# Define three buses
bus1 = Bus(id="bus1", phases="abc")
bus2 = Bus(id="bus2", phases="abc")
bus3 = Bus(id="bus3", phases="abc")

# Define a voltage source on the first bus
un = 400
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)

# Define the impedance and admittance parameters of the lines (can be reused)
parameters = LineParameters(
    id="parameters",
    z_line=Q_((0.12 + 0.1j) * np.eye(3), "ohm/km"),
    y_shunt=Q_(2e-4j * np.eye(3), "S/km"),
)

# Define a line between bus1 and bus2 (using g1 for the shunt connections)
line1 = Line(
    id="line1",
    bus1=bus1,
    bus2=bus2,
    parameters=parameters,
    length=Q_(2, "km"),
    ground=g1,
)

# Define a line between bus2 and bus3 (using g2 for the shunt connections)
line2 = Line(
    id="line2",
    bus1=bus2,
    bus2=bus3,
    parameters=parameters,
    length=Q_(2.5, "km"),
    ground=g2,
)

# Add a load on bus3
load = PowerLoad(
    id="load",
    bus=bus3,
    powers=Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA"),
)

# Set the phase "a" of the first bus to the ground g1
g1.connect(bus=bus1, phase="a")

# Set the potential of the ground element g1 to 0V
pref = PotentialRef(id="pref", element=g1)

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

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
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
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
