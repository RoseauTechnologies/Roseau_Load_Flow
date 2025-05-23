---
myst:
  html_meta:
    description lang=en: |
      Power load models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    keywords lang=en: simulation, distribution grid, switch, power load, model
    # spellchecker:off
    description lang=fr: |
      Les modèles de charge de puissance dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et
      déséquilibré dans une API Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, bus, roseau load flow, charges, modèle, puissance
# spellchecker:on
---

# Power loads (P)

They represent loads for which the power is considered constant, i.e. it is independent of the voltage.

_ZIP_ equation: $S = s \times V^0 + 0 \times V^1 + 0 \times V^2 \implies S = \mathrm{constant}$

## Equations

The equations are the following for star loads given the constant powers {math}`s_{\mathrm{abc}}`:

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{abc}}} &= \left(\frac{\underline{s_{\mathrm{abc}}}}{\underline{V_{\mathrm{abc}}}
        -\underline{V_{\mathrm{n}}}}\right)^{\star} \\
        \underline{I_{\mathrm{n}}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}\underline{I_{p}}
    \end{aligned}
\right.
```

And the following for delta loads given the constant powers {math}`s_{\mathrm{ab}}`, {math}`s_{\mathrm{bc}}` and
{math}`s_{\mathrm{ca}}`:

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{ab}}} &= \left(\frac{\underline{s_{\mathrm{ab}}}}{\underline{V_{\mathrm{a}}}-\underline
        {V_{\mathrm{b}}}}\right)^{\star} \\
        \underline{I_{\mathrm{bc}}} &= \left(\frac{\underline{s_{\mathrm{bc}}}}{\underline{V_{\mathrm{b}}}-\underline
        {V_{\mathrm{c}}}}\right)^{\star} \\
        \underline{I_{\mathrm{ca}}} &= \left(\frac{\underline{s_{\mathrm{ca}}}}{\underline{V_{\mathrm{c}}}-\underline
        {V_{\mathrm{a}}}}\right)^{\star}
    \end{aligned}
\right.
```

## Available Results

The results for constant-power loads are described [here](./index.md#available-results).

## Usage

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
un = 400 / rlf.SQRT3
vs = rlf.VoltageSource(id="source", bus=bus1, voltages=rlf.Q_(un, "V"))

# The potential of the neutral of bus1 is fixed at 0V
pref = rlf.PotentialRef(id="pref", element=bus1)

# A balanced constant-power load on the second bus
load = rlf.PowerLoad(id="load", bus=bus2, powers=rlf.Q_((1000 - 300j), "VA"))

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# Get the powers of the loads in the network
en.res_loads["power"]
# |               |                      power |
# |:--------------|---------------------------:|
# | ('load', 'a') | 1000-300j                  |
# | ('load', 'b') | 1000-300j                  |
# | ('load', 'c') | 1000-300j                  |
# | ('load', 'n') | -5.57569e-31+ 2.25385e-32j |

# Get the voltages of the network
en.res_buses_voltages["voltage"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |            9.69325e-22 |
# | ('bus1', 'bn') |                   230.94  |         -120           |
# | ('bus1', 'cn') |                   230.94  |          120           |
# | ('bus2', 'an') |                   229.414 |           -0.113552    |
# | ('bus2', 'bn') |                   229.414 |         -120.114       |
# | ('bus2', 'cn') |                   229.414 |          119.886       |

# Create an unbalanced load with three different power values
load.powers = rlf.Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA")
en.solve_load_flow()

# Get the powers of the loads in the network, the neutral power is no longer zero
en.res_loads["power"]
# |               |                  power |
# |:--------------|-----------------------:|
# | ('load', 'a') | 5154.28 - 1581.93j     |
# | ('load', 'b') | 2494.65 - 668.07j      |
# | ('load', 'c') |    0                   |
# | ('load', 'n') | -148.93 + 3.78664e-14j |

# Get the voltages of the network, bus2 voltages are no longer equal
en.res_buses_voltages["voltage"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |            4.05321e-24 |
# | ('bus1', 'bn') |                   230.94  |         -120           |
# | ('bus1', 'cn') |                   230.94  |          120           |
# | ('bus2', 'an') |                   215.746 |           -0.253646    |
# | ('bus2', 'bn') |                   229.513 |         -121.963       |
# | ('bus2', 'cn') |                   235.788 |          121.314       |
```
