# Bus

## Definition

It represents a multiphase node in the network that other elements (loads, lines, transformers,
voltage sources...) can connect to. A bus is a placeholder point where we want the voltage to be
computed during the load flow.

```{image} /_static/Bus.svg
:alt: Bus diagram
:width: 100px
:align: center
```

No equation is added for a bus.

## Usage

A bus is identified by its unique id and must define the phases it is connected to. A bus must
have all the phases of the elements connected to it.

```python
from roseau.load_flow import Bus, PowerLoad

bus1 = Bus(id="bus1", phases="abcn")  # A three-phase bus with a neutral
bus2 = Bus(id="bus2", phases="abc")  # A three-phase bus without a neutral
bus3 = Bus(id="bus3", phases="an")  # A single-phase bus

PowerLoad(id="load1", bus=bus1, powers=[100, 0, 50j], phases="abcn")  # OK
PowerLoad(id="load2", bus=bus1, powers=[100, 0, 50j], phases="abc")  # OK
PowerLoad(id="load3", bus=bus2, powers=[100], phases="ab")  # OK
PowerLoad(
    id="load4", bus=bus3, powers=[100], phases="ab"
)  # Error: bus3 does not have phase "b"
```

Since a bus represents a point in the network, it is possible to define the coordinates of this
point:

```python
from shapely import Point
from roseau.load_flow import Bus

bus = Bus(id="bus", phases="abc", geometry=Point(1.0, -2.5))
```

This information is not used by the load flow solver but could be used to generate geographical
plots of the results.

## Short-circuit

The bus element can also be used to create a short-circuit in the network to perform
[short-circuit analysis](../usage/Short_Circuit.md).

Here is an example of a simple short-circuit between two phases:

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
lp = LineParameters(id="lp", z_line=Q_((0.3 + 0.35j) * np.eye(4), "ohm/km"))
line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(1, "km"))

# A voltage source on the first bus
un = 400 / np.sqrt(3)
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus1, voltages=voltages)

# The neutral of the voltage source is fixed at potential 0
pref = PotentialRef(id="pref", element=bus1, phase="n")

# Create a short-circuit on bus2 between phases "a" and "b"
bus2.add_short_circuit("a", "b")

# Create a network and solve a load flow
en = ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# Get the currents flowing to the line from bus1
# Notice the extremely high currents in phases "a" and "b"
en.res_branches[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    433.861 |                -19.3987 |
# | ('line', 'b') |                    433.861 |                160.601  |
# | ('line', 'c') |                      0     |                  0      |
# | ('line', 'n') |                      0     |                  0      |
```

## API Reference

```{eval-rst}
.. autoclass:: roseau.load_flow.models.Bus
   :members:
   :show-inheritance:
   :no-index:
```
