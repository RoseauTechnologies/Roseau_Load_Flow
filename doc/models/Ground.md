# Ground

## Definition

The ground element can be used to connect several elements. It is notably necessary to connect the shunt admittances
of a line. Its representation is:

```{image}  /_static/Ground.svg
:alt: Ground diagram
:width: 100px
:align: center
```

This element adds the equation $\underline{I_{\mathrm{g}}} = 0$.

```{warning}
In electrical engineering, it is common to also add the equation $\underline{V_{\mathrm{g}}}=0$ when defining a
ground element. If you want to do so, you must add a `PotentialRef` element as defined in <project:./PotentialRef.md>.
```

## Usage

In *Roseau Load Flow*, several grounds can be defined leading to grounds elements with a non-zero potential. Here is
an example with two ground elements `g1` and `g2`.

After solving this load flow, the following assertions will be verified:
* The potential of the ground `g1` will be 0V as defined by the potential reference `pref`.
* There is no reason for the potential of `g2` to be zero too.
* The sum of currents flowing through the shunt admittance of the first line will be zero as they are all connected
  to the ground `g1`.
* The sum of currents flowing through the shunt admittance of the second line will be zero as they are all connected
  to the ground `g2`.

```python
import numpy as np
import functools as ft
from roseau.load_flow import (
    Bus,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    VoltageSource,
    ElectricalNetwork,
    Q_,
    PowerLoad,
)

# Define two grounds elements
g1 = Ground(id="g1")
g2 = Ground(id="g2")

# Define three buses
bus1 = Bus(id="bus1", phases="abc")
bus2 = Bus(id="bus2", phases="abc")
bus3 = Bus(id="bus3", phases="abc")

# Define a voltage source on the first bus
un = 400 / np.sqrt(3)
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)

# Define a line between bus1 and bus2 (using g1 in the shunt line)
parameters = LineParameters(
    id="parameters",
    z_line=Q_((0.12 + 0.1j) * np.eye(3), "ohm/km"),
    y_shunt=Q_(2e-4j * np.eye(3), "S/km"),
)
line1 = Line(
    id="line1", bus1=bus1, bus2=bus2, parameters=parameters, length=Q_(2, "km"), ground=g1
)

# Define a line between bus2 and bus3 (using g2 in the shunt line)
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
    id="load", bus=bus3, powers=Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA")
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
# The potential of g1 is 0 as defined by the potential reference object
# The potential of g2 has no reason to be zero
en.res_grounds.transform([np.abs, ft.partial(np.angle, deg=True)])
# | ground_id   |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:------------|----------------------------:|-------------------------:|
# | g1          |                       0     |                    0     |
# | g2          |                     133.339 |                  149.997 |

# As requested, the potential of the phase "a" of bus1 is zero
en.res_buses.transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('potential', 'absolute') |   ('potential', 'angle') |
# |:--------------|----------------------------:|-------------------------:|
# | ('bus1', 'a') |                     0       |                    0     |
# | ('bus1', 'b') |                   230.94    |                 -180     |
# | ('bus1', 'c') |                   230.94    |                  120     |
# | ('bus2', 'a') |                     7.63356 |                 -132.413 |
# | ('bus2', 'b') |                   227.6     |                  177.657 |
# | ('bus2', 'c') |                   226.978   |                  120.107 |
# | ('bus3', 'a') |                    17.1667  |                 -132.444 |
# | ('bus3', 'b') |                   223.953   |                  174.641 |
# | ('bus3', 'c') |                   222.013   |                  120.253 |

# The requested voltages of the voltage sources are respected
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'ab') |                   230.94  |            1.30411e-21 |
# | ('bus1', 'bc') |                   230.94  |         -120           |
# | ('bus1', 'ca') |                   230.94  |          120           |
# | ('bus2', 'ab') |                   222.762 |           -3.84568     |
# | ('bus2', 'bc') |                   218.821 |         -121.261       |
# | ('bus2', 'ca') |                   229.386 |          118.288       |
# | ('bus3', 'ab') |                   214.04  |           -9.02746     |
# | ('bus3', 'bc') |                   203.814 |         -123.038       |
# | ('bus3', 'ca') |                   227.709 |          116.126       |
```
