# Shunt line

## Equations

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

The corresponding equations are:

```{math}
\left\{
    \begin{aligned}
        V_1 &= a \cdot V_2 - b \cdot I_2 + g \cdot V_{\mathrm{g}} \\
        I_1 &= c \cdot V_2 - d \cdot I_2 + h \cdot V_{\mathrm{g}} \\
        I_{\mathrm{g}} &= f^t \cdot \left(V_1 + V_2 - 2\cdot V_{\mathrm{g}}\right)
    \end{aligned}
\right.
```

where

```{math}
\left\{
    \begin{aligned}
        a &= \mathcal{I}_4 + \dfrac{1}{2} \cdot Z \cdot Y  \\
        b &= Z  \\
        c &= Y + \dfrac{1}{4}\cdot Y \cdot Z \cdot Y  \\
        d &= \mathcal{I}_4 + \dfrac{1}{2} \cdot Y \cdot Z  \\
        f &= -\dfrac{1}{2} \cdot \begin{pmatrix} y_{\mathrm{ag}} & y_{\mathrm{bg}} & y_{\mathrm{cg}} &
        y_{\mathrm{ng}} \end{pmatrix} ^t  \\
        g &= Z \cdot f  \\
        h &= 2 \cdot f + \frac{1}{2}\cdot Y \cdot Z \cdot f  \\
    \end{aligned}
\right.
```

with $Z$ the series impedance matrix and $Y$ the shunt admittance matrix.


## Usage
To create a shunt line, the `LineParameter` instance must be created with the `y_shunt` argument. In addition, the
`ground` argument of the `Line` constructor is now mandatory. Here is a line with a power load.


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

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

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

# The losses of the line can also be accessed. One can remark that there are shunt losses
en.res_lines_losses
# |               |          'series_losses' |       'shunt_losses' | 'total_losses'    |
# |:--------------|-------------------------:|---------------------:|------------------:|
# | ('line', 'a') | 171.841+57.2802j         | -1.59017-26.6385j    | 170.251+ 30.6417j |
# | ('line', 'b') |  38.1291+12.7097j        | 1.01834-28.5657j     | 39.1474 -15.856j  |
# | ('line', 'c') |  0.00107497+0.000358324j | 3.69511-27.4104j     | 3.69618-27.41j    |
# | ('line', 'n') |  127.574  +42.5246j      | 0.0351686+0.0139828j | 127.609+42.5385j  |
```
