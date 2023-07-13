# Bus

## Definition

It represents a node in the network that other elements (loads, lines, transformers, voltage sources...) can connect to.

```{image}  /_static/Bus.svg
:alt: Bus diagram
:width: 100px
:align: center
```

No equation is added for a bus.


## Short-circuit

The bus element can also be used to create a short-circuit on a network. Here is an example:

```python
import functools as ft

import numpy as np

from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    Line,
    LineParameters,
    PotentialRef,
    Q_,
    VoltageSource,
)

# Two buses
bus1 = Bus(id="bus1", phases="abcn")
bus2 = Bus(id="bus2", phases="abcn")

# A line
line_parameters = LineParameters(
    id="line_parameters", z_line=Q_((0.3 + 0.35j) * np.eye(4), "ohm/km")
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

# Create a short circuit on bus2 between phases "a" and "b"
bus2.short_circuit("a", "b")

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

# Get the current flowing from the bus1 to the line
# One can remark that the current flowing in phase a and b is extremely high
en.res_branches[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    433.861 |                -19.3987 |
# | ('line', 'b') |                    433.861 |                160.601  |
# | ('line', 'c') |                      0     |                  0      |
# | ('line', 'n') |                      0     |                  0      |
```
