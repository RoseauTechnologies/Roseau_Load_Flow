---
myst:
  html_meta:
    "description lang=en": |
      Current load models in Roseau Load Flow - three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    "description lang=fr": |
      Les modèles de charge de courant dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré
      dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, charges, modèle, courant, intensité
    "keywords lang=en": simulation, distribution grid, switch, load, model, current, intensity
---

# Current loads (I)

They represent loads for which the current is considered constant, i.e. the power is proportional
to the voltage.

_ZIP_ equation: $S = 0 \times V^0 + i \times V^1 + 0 \times V^2 \implies S \propto V$

## Equations

The equations are the following for star loads given the constant currents {math}`i_{\mathrm{abc}}`:

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{abc}}} &= i_{\mathrm{abc}} \frac{\underline{V_{\mathrm{abc}}}
        -\underline{V_{\mathrm{n}}}}{|\underline{V_{\mathrm{abc}}}-\underline{V_{\mathrm{n}}}|} \\
        \underline{I_{\mathrm{n}}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}\underline{I_{p}}
    \end{aligned}
\right.
```

And the following for delta loads given the constant currents {math}`i_{\mathrm{ab}}`,
{math}`i_{\mathrm{bc}}` and {math}`i_{\mathrm{ca}}`:

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{ab}}} &= i_{\mathrm{ab}} \frac{\underline{V_{\mathrm{a}}}
        -\underline{V_{\mathrm{b}}}}{|\underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{b}}}|} \\
        \underline{I_{\mathrm{bc}}} &= i_{\mathrm{bc}} \frac{\underline{V_{\mathrm{b}}}
        -\underline{V_{\mathrm{c}}}}{|\underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{c}}}|} \\
        \underline{I_{\mathrm{ca}}} &= i_{\mathrm{ca}} \frac{\underline{V_{\mathrm{c}}}
        -\underline{V_{\mathrm{a}}}}{|\underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{a}}}|}
    \end{aligned}
\right.
```

## Example

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Two buses
bus1 = rlf.Bus(id="bus1", phases="abcn")
bus2 = rlf.Bus(id="bus2", phases="abcn")

# A line
lp = rlf.LineParameters(id="lp", z_line=rlf.Q_(0.35 * np.eye(4), "ohm/km"))
line = rlf.Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=rlf.Q_(1, "km"))

# A voltage source on the first bus
un = 400 / np.sqrt(3)
vs = rlf.VoltageSource(id="source", bus=bus1, voltages=rlf.Q_(un, "V"))

# The potential of the neutral of bus1 is fixed at 0V
pref = rlf.PotentialRef(id="pref", element=bus1)

# A balanced constant-current load on the second bus: 5A per phase
load = rlf.CurrentLoad(id="load", bus=bus2, currents=rlf.Q_(5, "A"))

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# Get the current of the load (equal to the one provided)
en.res_loads["current"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |    absolute |      angle |
# |:--------------|------------:|-----------:|
# | ('load', 'a') | 5           |          0 |
# | ('load', 'b') | 5           |       -120 |
# | ('load', 'c') | 5           |        120 |
# | ('load', 'n') | 1.77636e-15 |   -71.5651 |

# Get the voltages of the network
en.res_buses_voltages["voltage"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                    230.94 |                      0 |
# | ('bus1', 'bn') |                    230.94 |                   -120 |
# | ('bus1', 'cn') |                    230.94 |                    120 |
# | ('bus2', 'an') |                    229.19 |                      0 |
# | ('bus2', 'bn') |                    229.19 |                   -120 |
# | ('bus2', 'cn') |                    229.19 |                    120 |

# Create an unbalanced load with three different current values
load.currents = rlf.Q_(np.array([5.0, 2.5, 0]) * rlf.PositiveSequence, "A")

en.solve_load_flow()

# Get the currents of the loads of the network
en.res_loads["current"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   absolute |       angle |
# |:--------------|-----------:|------------:|
# | ('load', 'a') |    5       |   -0.187647 |
# | ('load', 'b') |    2.5     |     119.999 |
# | ('load', 'c') |    0       |          -0 |
# | ('load', 'n') |    4.32197 |    -150.188 |
```
