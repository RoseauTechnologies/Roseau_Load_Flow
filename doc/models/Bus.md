---
myst:
  html_meta:
    "description lang=en": |
      Buses in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau Technologies.
    "keywords lang=en": simulation, distribution grid, bus, model
    # spellchecker:off
    "description lang=fr": |
      Les bus dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une API Python par
      Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, modèle
    # spellchecker:on
---

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

## Available Results

The following results are available for all buses:

| Result Accessor      | Default Unit  | Type          | Description                                                                                                                       |
| -------------------- | ------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `res_potentials`     | $V$           | complex array | The potentials of each phase of the bus                                                                                           |
| `res_voltages`       | $V$           | complex array | The phase-to-neutral voltages if the bus has a neutral, the phase-to-phase voltages otherwise                                     |
| `res_voltage_levels` | $\mathrm{pu}$ | number array  | The per-unit voltage levels: ($\sqrt{3} V_{pn} / V_\mathrm{nom}$) if the bus has a neutral, ($V_{pp} / V_\mathrm{nom}$) otherwise |
| `res_violated`       | -             | boolean array | Indicates if the voltage levels violate the limits                                                                                |

Additionally, the following results are available for buses _with a neutral_:

| Result Accessor         | Default Unit  | Type          | Description                                                                      |
| ----------------------- | ------------- | ------------- | -------------------------------------------------------------------------------- |
| `res_voltages_pn`       | $V$           | complex array | The phase-to-neutral voltages of the bus                                         |
| `res_voltage_levels_pn` | $\mathrm{pu}$ | number array  | The voltage levels of each phase of the bus ($\sqrt{3} V_{pn} / V_\mathrm{nom}$) |

And the following results are available for buses _with more than one phase_:

| Result Accessor         | Default Unit  | Type          | Description                                                             |
| ----------------------- | ------------- | ------------- | ----------------------------------------------------------------------- |
| `res_voltages_pp`       | $V$           | complex array | The phase-to-phase voltages of the bus                                  |
| `res_voltage_levels_pp` | $\mathrm{pu}$ | number array  | The voltage levels of each phase of the bus ($V_{pp} / V_\mathrm{nom}$) |

And the following results are available for _three-phase_ buses:

| Result Accessor           | Default Unit | Type   | Description                                                                    |
| ------------------------- | ------------ | ------ | ------------------------------------------------------------------------------ |
| `res_voltage_unbalance()` | $\%$         | number | The voltage unbalance of the bus according to the IEC, IEEE or NEMA definition |

## Usage

A bus is identified by its unique id and must define the phases it is connected to. A bus must
have all the phases of the elements connected to it.

```python
import roseau.load_flow as rlf

bus1 = rlf.Bus(id="bus1", phases="abcn")  # A three-phase bus with a neutral
bus2 = rlf.Bus(id="bus2", phases="abc")  # A three-phase bus without a neutral
bus3 = rlf.Bus(id="bus3", phases="an")  # A single-phase bus

rlf.PowerLoad(id="load1", bus=bus1, powers=1000, phases="abcn")  # OK
rlf.PowerLoad(id="load2", bus=bus1, powers=1000, phases="abc")  # OK
rlf.PowerLoad(id="load3", bus=bus2, powers=1000, phases="ab")  # OK
rlf.PowerLoad(
    id="load4", bus=bus3, powers=1000, phases="ab"
)  # Error: bus3 does not have phase "b"
```

Since a bus represents a point in the network, it is possible to define the coordinates of this
point:

```python
import roseau.load_flow as rlf
from shapely import Point

bus = rlf.Bus(id="bus", phases="abc", geometry=Point(1.0, -2.5))
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
import roseau.load_flow as rlf

# Two buses
bus1 = rlf.Bus(id="bus1", phases="abcn")
bus2 = rlf.Bus(id="bus2", phases="abcn")

# A line
lp = rlf.LineParameters(id="lp", z_line=rlf.Q_((0.3 + 0.35j) * np.eye(4), "ohm/km"))
line = rlf.Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=rlf.Q_(1, "km"))

# A voltage source on the first bus
un = 400 / rlf.SQRT3
vs = rlf.VoltageSource(id="source", bus=bus1, voltages=rlf.Q_(un, "V"))

# The neutral of bus1 is fixed at potential 0
pref = rlf.PotentialRef(id="pref", element=bus1)

# Create a short-circuit on bus2 between phases "a" and "b"
bus2.add_short_circuit("a", "b")

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# Get the currents flowing to the line from bus1
# Notice the extremely high currents in phases "a" and "b"
en.res_lines[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    433.861 |                -19.3987 |
# | ('line', 'b') |                    433.861 |                160.601  |
# | ('line', 'c') |                      0     |                  0      |
# | ('line', 'n') |                      0     |                  0      |
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.Bus
   :members:
   :show-inheritance:
   :no-index:
```
