# Power loads

## Equations

They represent loads for which the power is considered constant. The equations are the following (star loads):

```{math}
\left\{
    \begin{aligned}
        I_{\mathrm{abc}} &= \left(\frac{S_{\mathrm{abc}}}{V_{\mathrm{abc}}-V_{\mathrm{n}}}\right)^{\star} \\
        I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}
    \end{aligned}
\right.
```

And the following (delta loads):

```{math}
\left\{
    \begin{aligned}
        I_{\mathrm{ab}} &= \left(\frac{S_{\mathrm{ab}}}{V_{\mathrm{a}}-V_{\mathrm{b}}}\right)^{\star} \\
        I_{\mathrm{bc}} &= \left(\frac{S_{\mathrm{bc}}}{V_{\mathrm{b}}-V_{\mathrm{c}}}\right)^{\star} \\
        I_{\mathrm{ca}} &= \left(\frac{S_{\mathrm{ca}}}{V_{\mathrm{c}}-V_{\mathrm{a}}}\right)^{\star}
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
    PowerLoad,
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
load = PowerLoad(
    id="load", bus=bus2, powers=Q_(np.array([1000, 1000, 1000]) * (1 - 0.3j), "VA")
)

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

# Get the powers of the load
en.res_loads["power"]
# |               |                      power |
# |:--------------|---------------------------:|
# | ('load', 'a') | 1000-300j                  |
# | ('load', 'b') | 1000-300j                  |
# | ('load', 'c') | 1000-300j                  |
# | ('load', 'n') | -5.57569e-31+ 2.25385e-32j |

# Get the voltages of the network
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |            9.69325e-22 |
# | ('bus1', 'bn') |                   230.94  |         -120           |
# | ('bus1', 'cn') |                   230.94  |          120           |
# | ('bus2', 'an') |                   229.414 |           -0.113552    |
# | ('bus2', 'bn') |                   229.414 |         -120.114       |
# | ('bus2', 'cn') |                   229.414 |          119.886       |

# Modify the load value to create an unbalanced load
load.powers = Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA")
en.solve_load_flow(auth=auth)

# Get the powers of the load
en.res_loads["power"]
# |               |                  power |
# |:--------------|-----------------------:|
# | ('load', 'a') | 5154.28 - 1581.93j     |
# | ('load', 'b') | 2494.65 - 668.07j      |
# | ('load', 'c') |    0                   |
# | ('load', 'n') | -148.93 + 3.78664e-14j |

# Get the voltages of the network
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |            4.05321e-24 |
# | ('bus1', 'bn') |                   230.94  |         -120           |
# | ('bus1', 'cn') |                   230.94  |          120           |
# | ('bus2', 'an') |                   215.746 |           -0.253646    |
# | ('bus2', 'bn') |                   229.513 |         -121.963       |
# | ('bus2', 'cn') |                   235.788 |          121.314       |
```
