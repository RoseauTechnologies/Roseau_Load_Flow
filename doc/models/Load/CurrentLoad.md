# Current loads (I)

They represent loads for which the current is considered constant, i.e. the power is proportional
to the voltage.

_ZIP_ equation: $S = 0 \times V^0 + i \times V^1 + 0 \times V^2 \implies S \propto V$

## Equations

The equations are the following (star loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{abc}}} &= \mathrm{constant} \\
        \underline{I_{\mathrm{n}}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}\underline{I_{p}}
    \end{aligned}
\right.
```

And the following (delta loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{ab}}} &= \mathrm{constant} \\
        \underline{I_{\mathrm{bc}}} &= \mathrm{constant} \\
        \underline{I_{\mathrm{ca}}} &= \mathrm{constant}
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
    CurrentLoad,
    Q_,
    VoltageSource,
)

# Two buses
bus1 = Bus(id="bus1", phases="abcn")
bus2 = Bus(id="bus2", phases="abcn")

# A line
lp = LineParameters(id="lp", z_line=Q_(0.35 * np.eye(4), "ohm/km"))
line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(1, "km"))

# A voltage source on the first bus
un = 400 / np.sqrt(3)
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)

# The neutral of the voltage source is fixed at potential 0
pref = PotentialRef(id="pref", element=bus1, phase="n")

# A current load on the second bus
load = CurrentLoad(
    id="load",
    bus=bus2,
    currents=Q_(5 * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "A"),
)

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

# Get the current of the load (equal to the one provided)
en.res_loads["current"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |    absolute |   angle |
# |:--------------|------------:|--------:|
# | ('load', 'a') | 5           |       0 |
# | ('load', 'b') | 5           |    -120 |
# | ('load', 'c') | 5           |     120 |
# | ('load', 'n') | 1.77636e-15 |     180 |

# Get the voltages of the network
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                    230.94 |                      0 |
# | ('bus1', 'bn') |                    230.94 |                   -120 |
# | ('bus1', 'cn') |                    230.94 |                    120 |
# | ('bus2', 'an') |                    229.19 |                      0 |
# | ('bus2', 'bn') |                    229.19 |                   -120 |
# | ('bus2', 'cn') |                    229.19 |                    120 |

# Modify the load value to create an unbalanced load
load.currents = Q_(
    np.array([5.0, 2.5, 0]) * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "A"
)
en.solve_load_flow(auth=auth)

# Get the currents of the loads of the network
en.res_loads["current"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   absolute |   angle |
# |:--------------|-----------:|--------:|
# | ('load', 'a') |    5       |       0 |
# | ('load', 'b') |    2.5     |    -120 |
# | ('load', 'c') |    0       |     180 |
# | ('load', 'n') |    4.33013 |     150 |
```
