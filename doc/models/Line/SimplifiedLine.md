---
myst:
  html_meta:
    "description lang=en": |
      Simplified line models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    "description lang=fr": |
      Les modèles de ligne simplifiés dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré
      dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, lignes, modèle
    "keywords lang=en": simulation, distribution grid, switch, lines, model
---

# Simplified line

If the line is modeled with only series impedance, the model is simplified as there is no coupling
with the ground. This is a common model of short lines, typically in distribution networks.

The corresponding diagram is:

````{tab} European standards
```{image} /_static/Line/European_Simplified_Line.svg
:alt: Simplified line diagram
:width: 600px
:align: center
```
````

````{tab} American standards
```{image} /_static/Line/American_Simplified_Line.svg
:alt: Simplified line diagram
:width: 600px
:align: center
```
````

## Equations

With $\underline{Y} = 0$, the equations become:

```{math}
\left\{
    \begin{aligned}
        \underline{V_1} - \underline{V_2} &= \underline{Z} \cdot \underline{I_1} \\
        \underline{I_2} &= -\underline{I_1}
    \end{aligned}
\right.
```

## Usage

To create a simplified line, create an instance of `LineParameter` without providing `y_shunt`.
Here is a simplified line connecting a constant power load to a voltage source.

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

# An unbalanced constant-power load on the second bus
load = rlf.PowerLoad(
    id="load", bus=bus2, powers=rlf.Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA")
)

# The impedance matrix (in Ohm) can be accessed from the line instance
line.z_line
# array(
#     [[0.35+0.j, 0.  +0.j, 0.  +0.j, 0.  +0.j],
#      [0.  +0.j, 0.35+0.j, 0.  +0.j, 0.  +0.j],
#      [0.  +0.j, 0.  +0.j, 0.35+0.j, 0.  +0.j],
#      [0.  +0.j, 0.  +0.j, 0.  +0.j, 0.35+0.j]]
# ) <Unit('ohm')>

# For a simplified line, the property `with_shunt` is False and the `y_shunt` matrix is zero
line.with_shunt
# False

line.y_shunt
# array(
#     [[0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j],
#      [0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j],
#      [0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j],
#      [0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j]]
# ) <Unit('siemens')>

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# The current flowing into the line from bus1
en.res_lines[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    24.1958 |                 16.4456 |
# | ('line', 'b') |                    11.3722 |               -105.263  |
# | ('line', 'c') |                     0      |                  0      |
# | ('line', 'n') |                    20.628  |                168.476  |

# The current flowing into the line from bus2
en.res_lines[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current2', 'absolute') |   ('current2', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    24.1958 |               -163.554  |
# | ('line', 'b') |                    11.3722 |                 74.7366 |
# | ('line', 'c') |                     0      |                  0      |
# | ('line', 'n') |                    20.628  |                -11.5242 |

# The currents in the series components of the line
en.res_lines[["series_current"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('series_current', 'absolute') |   ('series_current', 'angle') |
# |:--------------|---------------------------------:|------------------------------:|
# | ('line', 'a') |                          24.1958 |                       16.4456 |
# | ('line', 'b') |                          11.3722 |                     -105.263  |
# | ('line', 'c') |                           0      |                        0      |
# | ('line', 'n') |                          20.628  |                      168.476  |

# All currents are equal in magnitude for a simplified lines as no current escapes to the ground.
# The current from bus 2 has an opposite direction to the current from bus 1 as expected.

# The losses of the line can also be accessed. One can remark that there are no shunt losses
en.res_lines[["series_losses"]].transform([np.real, np.imag])
# |               |   ('series_losses', 'real') |   ('series_losses', 'imag') |
# |:--------------|----------------------------:|----------------------------:|
# | ('line', 'a') |                    204.904  |                -2.66329e-15 |
# | ('line', 'b') |                     45.2646 |                -8.96306e-16 |
# | ('line', 'c') |                      0      |                 0           |
# | ('line', 'n') |                    148.93   |                 7.62657e-16 |

# With a simplified model, all the losses are caused by the series impedance of the line
res_lines = en.res_lines
total_losses = res_lines["power1"] + res_lines["power2"]  # total = series + shunt
np.allclose(total_losses, res_lines["series_losses"])
# True
```
