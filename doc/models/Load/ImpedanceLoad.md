# Impedance loads

They represent loads for which the impedance is considered constant.

## Equations

The equations are the following (star loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{abc}}} &= \frac{\underline{V_{\mathrm{abc}}}-\underline{V_{\mathrm{n}}}}{
        \underline{Z_{\mathrm{abc}}}} \\
        \underline{I_{\mathrm{n}}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}\underline{I_{p}}
    \end{aligned}
\right.
```

And the following (delta loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{ab}}} &= \frac{\underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{b}}}}{\underline{Z_{\mathrm{ab}}}} \\
        \underline{I_{\mathrm{bc}}} &= \frac{\underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{c}}}}{\underline{Z_{\mathrm{bc}}}} \\
        \underline{I_{\mathrm{ca}}} &= \frac{\underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{a}}}}{\underline{Z_{\mathrm{ca}}}}
    \end{aligned}
\right.
```

## Example

```python
import functools as ft

import numpy as np

from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    Line,
    LineParameters,
    PotentialRef,
    ImpedanceLoad,
    Q_,
    VoltageSource,
)

# Two buses
bus1 = Bus(id="bus1", phases="abcn")
bus2 = Bus(id="bus2", phases="abcn")

# A line
line_parameters = LineParameters(
    id="line_parameters", z_line=Q_(0.35 * np.eye(4), "ohm/km")
)
line = Line(
    id="line", bus1=bus1, bus2=bus2, parameters=line_parameters, length=Q_(1, "km")
)

# A voltage source on the first bus
un = 400 / np.sqrt(3)
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)

# The neutral of the voltage source is fixed at potential 0
pref = PotentialRef(id="pref", element=bus1, phase="n")

# A power load on the second bus
load = ImpedanceLoad(
    id="load", bus=bus2, impedances=Q_(np.array([40 + 3j, 40 + 3j, 40 + 3j]), "ohm")
)

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

# Get the impedances of the load (the result is equal to the provided impednce
load.res_voltages / load.res_currents[:3]
# array([40.+3.j, 40.+3.j, 40.+3.j]) <Unit('volt / ampere')>

# Get the voltages of the network
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |           -6.40192e-19 |
# | ('bus1', 'bn') |                   230.94  |         -120           |
# | ('bus1', 'cn') |                   230.94  |          120           |
# | ('bus2', 'an') |                   228.948 |            0.0370675   |
# | ('bus2', 'bn') |                   228.948 |         -119.963       |
# | ('bus2', 'cn') |                   228.948 |          120.037       |

# Modify the load value to create an unbalanced load
load.impedances = Q_(np.array([40 + 4j, 20 + 2j, 10 + 1j]), "ohm")
en.solve_load_flow(auth=auth)

# Get the impedance of the load
load.res_voltages / load.res_currents[:3]
# array([40.+4.j, 20.+2.j, 10.+1.j]) <Unit('volt / ampere')>

# Get the voltages of the network
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |               0        |
# | ('bus1', 'bn') |                   230.94  |            -120        |
# | ('bus1', 'cn') |                   230.94  |             120        |
# | ('bus2', 'an') |                   232.313 |              -0.792296 |
# | ('bus2', 'bn') |                   228.33  |            -118.76     |
# | ('bus2', 'cn') |                   218.703 |             119.891    |
```
