---
myst:
  html_meta:
    "description lang=en": |
      Impedance load models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    "description lang=fr": |
      Les modèles de charge d'impédance dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et
      déséquilibré dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, charges, modèle, impédance
    "keywords lang=en": simulation, distribution grid, switch, load, model, impedance
---

# Impedance loads (Z)

They represent loads for which the impedance is considered constant, i.e. the power is proportional
to the square of the voltage.

_ZIP_ equation: $S = 0 \times V^0 + 0 \times V^1 + z \times V^2 \implies S \propto V^2$

## Equations

The equations are the following for star loads given the constant impedances {math}`z_{\mathrm{abc}}`:

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{abc}}} &= \frac{\underline{V_{\mathrm{abc}}}-\underline{V_{\mathrm{n}}}}{
        \underline{z_{\mathrm{abc}}}} \\
        \underline{I_{\mathrm{n}}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}\underline{I_{p}}
    \end{aligned}
\right.
```

And the following for delta loads given the constant impedances {math}`z_{\mathrm{ab}}`,
{math}`z_{\mathrm{bc}}` and {math}`z_{\mathrm{ca}}`:

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{ab}}} &= \frac{\underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{b}}}}{\underline{z_{\mathrm{ab}}}} \\
        \underline{I_{\mathrm{bc}}} &= \frac{\underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{c}}}}{\underline{z_{\mathrm{bc}}}} \\
        \underline{I_{\mathrm{ca}}} &= \frac{\underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{a}}}}{\underline{z_{\mathrm{ca}}}}
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

# A balanced constant-impedance load on the second bus: R=40 ohm, X=3 ohm per phase
load = rlf.ImpedanceLoad(id="load", bus=bus2, impedances=rlf.Q_(40 + 3j, "ohm"))

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# Get the impedances of the load (the result is equal to the provided impedance
load.res_voltages / load.res_currents[:3]
# array([40.+3.j, 40.+3.j, 40.+3.j]) <Unit('volt / ampere')>

# Get the voltages of the network
en.res_buses_voltages["voltage"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |           -6.40192e-19 |
# | ('bus1', 'bn') |                   230.94  |         -120           |
# | ('bus1', 'cn') |                   230.94  |          120           |
# | ('bus2', 'an') |                   228.948 |            0.0370675   |
# | ('bus2', 'bn') |                   228.948 |         -119.963       |
# | ('bus2', 'cn') |                   228.948 |          120.037       |

# Create an unbalanced load with three different impedance values
load.impedances = rlf.Q_(np.array([40 + 4j, 20 + 2j, 10 + 1j]), "ohm")
en.solve_load_flow()

# Get the impedance of the load
load.res_voltages / load.res_currents[:3]
# array([40.+4.j, 20.+2.j, 10.+1.j]) <Unit('volt / ampere')>

# Get the voltages of the network
en.res_buses_voltages["voltage"].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                   230.94  |               0        |
# | ('bus1', 'bn') |                   230.94  |            -120        |
# | ('bus1', 'cn') |                   230.94  |             120        |
# | ('bus2', 'an') |                   232.313 |              -0.792296 |
# | ('bus2', 'bn') |                   228.33  |            -118.76     |
# | ('bus2', 'cn') |                   218.703 |             119.891    |
```
