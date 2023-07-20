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
lp = LineParameters(id="lp", z_line=Q_(0.35 * np.eye(4), "ohm/km"))
line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(1, "km"))

# A voltage source on the first bus
un = 400 / np.sqrt(3)
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)

# The neutral of the voltage source is fixed at potential 0
pref = PotentialRef(id="pref", element=bus1, phase="n")

# A power load on the second bus
load = PowerLoad(
    id="load", bus=bus2, powers=Q_(np.array([5.0, 2.5, 0]) * (1 - 0.3j), "kVA")
)

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

# The current flowing into the line from bus1
en.res_branches[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    24.1958 |                 16.4456 |
# | ('line', 'b') |                    11.3722 |               -105.263  |
# | ('line', 'c') |                     0      |                  0      |
# | ('line', 'n') |                    20.628  |                168.476  |

# The current flowing into the line from bus2
en.res_branches[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current2', 'absolute') |   ('current2', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    24.1958 |               -163.554  |
# | ('line', 'b') |                    11.3722 |                 74.7366 |
# | ('line', 'c') |                     0      |                  0      |
# | ('line', 'n') |                    20.628  |                -11.5242 |

# The two currents are equal in magnitude and opposite in phase, as expected

# The losses of the line can also be accessed. One can remark that there are no shunt losses
en.res_lines_losses
# |               |   'series_losses'      | 'shunt_losses' |  'total_losses'       |
# |:--------------|-----------------------:|---------------:|----------------------:|
# | ('line', 'a') | 204.904 -2.66329e-15   |             0j | 204.904 -2.66329e-15  |
# | ('line', 'b') |  45.2646 -8.96306e-16  |             0j |  45.2646 -8.96306e-16 |
# | ('line', 'c') |   0j                   |             0j |   0j                  |
# | ('line', 'n') | 148.93 + 6.11606e-15   |             0j | 148.93 + 6.11606e-15  |
```
