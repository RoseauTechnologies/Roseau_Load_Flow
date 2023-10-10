# Switch

## Definition

It represents an ideal switch, a lossless element that connects two buses.

```{image} /_static/Switch.svg
:alt: Switch diagram
:width: 300px
:align: center
```

## Equations

The associated equations are:

```{math}
\left\{
    \begin{aligned}
        \underline{I_1} &= - \underline{I_2}\\
        \underline{V_1} &= \underline{V_2}\\
    \end{aligned}
\right.
```

## Example

Here is a switch connecting a constant power load to a voltage source.

```python
import functools as ft
import numpy as np
from roseau.load_flow import (
    Q_,
    Bus,
    ElectricalNetwork,
    PotentialRef,
    PowerLoad,
    Switch,
    VoltageSource,
)

# Two buses
bus1 = Bus(id="bus1", phases="abcn")
bus2 = Bus(id="bus2", phases="abcn")

# A line
switch = Switch(id="switch", bus1=bus1, bus2=bus2)

# A voltage source on the first bus
un = 400 / np.sqrt(3)
voltages = un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)

# The neutral of the voltage source is fixed at potential 0
pref = PotentialRef(id="pref", element=bus1, phase="n")

# A power load on the second bus
load = PowerLoad(id="load", bus=bus2, powers=[5000 + 1600j, 2500 + 800j, 0])

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

# The current flowing into the line from bus1
en.res_branches[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                 |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:----------------|---------------------------:|------------------------:|
# | ('switch', 'a') |                    22.7321 |                -17.7447 |
# | ('switch', 'b') |                    11.3661 |               -137.745  |
# | ('switch', 'c') |                     0      |                  0      |
# | ('switch', 'n') |                    19.6866 |                132.255  |

# The current flowing into the line from bus2
en.res_branches[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                 |   ('current2', 'absolute') |   ('current2', 'angle') |
# |:----------------|---------------------------:|------------------------:|
# | ('switch', 'a') |                    22.7321 |                162.255  |
# | ('switch', 'b') |                    11.3661 |                 42.2553 |
# | ('switch', 'c') |                     0      |                  0      |
# | ('switch', 'n') |                    19.6866 |                -47.7447 |

# The two currents are equal in magnitude and opposite in phase, as expected

# The two buses have the same voltages
en.res_buses_voltages[["voltage"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                    230.94 |                      0 |
# | ('bus1', 'bn') |                    230.94 |                   -120 |
# | ('bus1', 'cn') |                    230.94 |                    120 |
# | ('bus2', 'an') |                    230.94 |                      0 |
# | ('bus2', 'bn') |                    230.94 |                   -120 |
# | ('bus2', 'cn') |                    230.94 |                    120 |
```

## API Reference

```{eval-rst}
.. autoclass:: roseau.load_flow.models.Switch
   :members:
   :show-inheritance:
   :no-index:
```
