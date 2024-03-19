---
myst:
  html_meta:
    "description lang=en": |
      Shunt line models in Roseau Load Flow - three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    "description lang=fr": |
      Les modèles de ligne Shunt dans Roseau Load Flow - solveur d'écoulement de charge triphasé et déséquilibré dans
      une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, lignes, modèle
    "keywords lang=en": simulation, distribution grid, switch, lines, model
---

# Shunt line

The first model of line which can be used is a PI model with series impedance and shunt admittance. The
corresponding diagram is:

````{tab} European standards
```{image} /_static/Line/European_Shunt_Line.svg
:alt: Shunt line diagram
:width: 1000px
:align: center
```
````

````{tab} American standards
```{image} /_static/Line/American_Shunt_Line.svg
:alt: Shunt line diagram
:width: 1000px
:align: center
```
````

## Equations

The corresponding equations are:

```{math}
\left\{
    \begin{aligned}
        \underline{V_1} &= \underline{a} \cdot \underline{V_2} - \underline{b} \cdot \underline{I_2} + \underline{g}
        \cdot \underline{V_{\mathrm{g}}} \\
        \underline{I_1} &= \underline{c} \cdot \underline{V_2} - \underline{d} \cdot \underline{I_2} + \underline{h}
        \cdot \underline{V_{\mathrm{g}}} \\
        \underline{I_{\mathrm{g}}} &= \underline{f}^\top \cdot \left(\underline{V_1} + \underline{V_2} - 2\cdot
        \underline{V_{\mathrm{g}}}\right)
    \end{aligned}
\right.
```

where

```{math}
\left\{
    \begin{aligned}
        \underline{a} &= \mathcal{I}_4 + \dfrac{1}{2} \cdot \underline{Z} \cdot \underline{Y}  \\
        \underline{b} &= \underline{Z}  \\
        \underline{c} &= \underline{Y} + \dfrac{1}{4}\cdot \underline{Y} \cdot \underline{Z} \cdot \underline{Y}  \\
        \underline{d} &= \mathcal{I}_4 + \dfrac{1}{2} \cdot \underline{Y} \cdot \underline{Z}  \\
        \underline{f} &= -\dfrac{1}{2} \cdot \begin{pmatrix} \underline{y_{\mathrm{ag}}} & \underline{y_{\mathrm{bg}}
        } & \underline{y_{\mathrm{cg}}} & \underline{y_{\mathrm{ng}}} \end{pmatrix} ^\top  \\
        \underline{g} &= \underline{Z} \cdot \underline{f}  \\
        \underline{h} &= 2 \cdot \underline{f} + \frac{1}{2}\cdot \underline{Y} \cdot \underline{Z} \cdot \underline{f}  \\
    \end{aligned}
\right.
```

with $\underline{Z}$ the series impedance matrix and $\underline{Y}$ the shunt admittance matrix.

## Usage

To create a shunt line, create an instance of `LineParameter` with the `y_shunt` argument. The
`ground` argument of the `Line` constructor is mandatory for shunt lines. Here is a line that
connects a constant power load to a voltage source.

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
    Ground,
)

# Two buses
bus1 = Bus(id="bus1", phases="abcn")
bus2 = Bus(id="bus2", phases="abcn")

# Create a ground element and set its potential to zero
ground = Ground(id="ground")
pref = PotentialRef(id="pref", element=ground)

# A shunt line
z_line = Q_(
    np.array(
        [
            [0.3 + 0.35j, 0.25j, 0.25j, 0.25j],
            [0.25j, 0.3 + 0.35j, 0.25j, 0.25j],
            [0.25j, 0.25j, 0.3 + 0.35j, 0.25j],
            [0.25j, 0.25j, 0.25j, 0.3 + 0.35j],
        ]
    ),
    "ohm/km",
)
y_shunt = Q_(
    np.array(
        [
            [20 + 475j, -68j, -10j, -68j],
            [-68j, 20 + 475j, -68j, -10j],
            [-10j, -68j, 20 + 475j, -68j],
            [-68j, -10j, -68j, 20 + 475j],
        ]
    ),
    "uS/km",  # micro Siemens per kilometer
)
line_parameters = LineParameters(id="line_parameters", z_line=z_line, y_shunt=y_shunt)
line = Line(
    id="line",
    bus1=bus1,
    bus2=bus2,
    parameters=line_parameters,
    length=Q_(1, "km"),
    ground=ground,
)

# A voltage source on the first bus
un = 400 / np.sqrt(3)
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)


# A power load on the second bus
load = PowerLoad(
    id="load", bus=bus2, powers=Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA")
)

# The impedance matrix (in Ohm) can be accessed from the line instance
line.z_line
# array(
#     [[0.3+0.35j, 0. +0.25j, 0. +0.25j, 0. +0.25j],
#      [0. +0.25j, 0.3+0.35j, 0. +0.25j, 0. +0.25j],
#      [0. +0.25j, 0. +0.25j, 0.3+0.35j, 0. +0.25j],
#      [0. +0.25j, 0. +0.25j, 0. +0.25j, 0.3+0.35j]]
# ) <Unit('ohm')>

# The shunt admittance matrix (in Siemens) can be accessed from the line instance
line.y_shunt
# array(
#     [[2.e-05+4.75e-04j, 0.e+00-6.80e-05j, 0.e+00-1.00e-05j, 0.e+00-6.80e-05j],
#      [0.e+00-6.80e-05j, 2.e-05+4.75e-04j, 0.e+00-6.80e-05j, 0.e+00-1.00e-05j],
#      [0.e+00-1.00e-05j, 0.e+00-6.80e-05j, 2.e-05+4.75e-04j, 0.e+00-6.80e-05j],
#      [0.e+00-6.80e-05j, 0.e+00-1.00e-05j, 0.e+00-6.80e-05j, 2.e-05+4.75e-04j]]
# ) <Unit('siemens')>

# For a shunt line, the property `with_shunt` is True
line.with_shunt
# True

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# The current "entering" into the line from the bus1
en.res_branches[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                  23.9459   |                 15.6886 |
# | ('line', 'b') |                  11.2926   |               -104.492  |
# | ('line', 'c') |                   0.119763 |               -157.68   |
# | ('line', 'n') |                  20.6151   |                167.381  |

# The current "entering" into the line from the bus2
en.res_branches[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current2', 'absolute') |   ('current2', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |               23.9202      |               -164.585  |
# | ('line', 'b') |               11.2551      |                 74.9044 |
# | ('line', 'c') |                5.68434e-14 |                  0      |
# | ('line', 'n') |               20.6273      |                -12.625  |

# The currents in the series components of the line
en.res_lines[["series_current"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('series_current', 'absolute') |   ('series_current', 'angle') |
# |:--------------|---------------------------------:|------------------------------:|
# | ('line', 'a') |                       23.9333    |                       15.5496 |
# | ('line', 'b') |                       11.2737    |                     -104.796  |
# | ('line', 'c') |                        0.0598601 |                     -157.579  |
# | ('line', 'n') |                       20.6215    |                      167.376  |

# The losses of the series components of line can also be accessed
en.res_lines[["series_losses"]].transform([np.real, np.imag])
# |               |   ('series_losses', 'real') |   ('series_losses', 'imag') |
# |:--------------|----------------------------:|----------------------------:|
# | ('line', 'a') |                171.841      |                57.2802      |
# | ('line', 'b') |                 38.1291     |                12.7097      |
# | ('line', 'c') |                  0.00107497 |                 0.000358324 |
# | ('line', 'n') |                127.574      |                42.5246      |

# The shunt losses can be computed. Notice that the shunt losses are not null for the shunt line.
res_lines = en.res_lines
total_losses = res_lines["power1"] + res_lines["power2"]  # total = series + shunt
shunt_losses = total_losses - res_lines["series_losses"]
shunt_losses.to_frame("shunt_losses").transform([np.real, np.imag])
# |               |   ('shunt_losses', 'real') |   ('shunt_losses', 'imag') |
# |:--------------|---------------------------:|---------------------------:|
# | ('line', 'a') |                 -1.59017   |                -26.6385    |
# | ('line', 'b') |                  1.01834   |                -28.5657    |
# | ('line', 'c') |                  3.69511   |                -27.4104    |
# | ('line', 'n') |                  0.0351686 |                  0.0139828 |
```
