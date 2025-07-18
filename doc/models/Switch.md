---
myst:
  html_meta:
    description lang=en: |
      Switches in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau Technologies.
    keywords lang=en: simulation, distribution grid, switch, switches, model
    # spellchecker:off
    description lang=fr: |
      Les interrupteurs dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une API
      Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, bus, roseau load flow, interrupteurs, modèle
    # spellchecker:on
---

# Switch

## Definition

It represents an ideal switch, a lossless element that connects two buses.

```{image} /_static/Switch.svg
---
alt: Switch diagram
width: 300px
align: center
---
```

## Equations

The associated equations are the following for a closed switch:

```{math}
\left\{
    \begin{aligned}
        \underline{I_1} &= - \underline{I_2}\\
        \underline{V_1} &= \underline{V_2}\\
    \end{aligned}
\right.
```

and for an open switch:

```{math}
\left\{
    \begin{aligned}
        \underline{I_1} &= 0\\
        \underline{I_2} &= 0\\
    \end{aligned}
\right.
```

## Available Results

The following results are available for all switches:

| Result Accessor  | Default Unit | Type             | Description                                                                                      |
| ---------------- | ------------ | ---------------- | ------------------------------------------------------------------------------------------------ |
| `res_potentials` | $V$          | 2 complex arrays | The potentials of each phase of the switch                                                       |
| `res_currents`   | $A$          | 2 complex arrays | The currents flowing into each phase of the switch                                               |
| `res_powers`     | $V\!A$       | 2 complex arrays | The powers flowing into each phase of the switch                                                 |
| `res_voltages`   | $V$          | 2 complex arrays | The phase-to-neutral voltages if the switch has a neutral, the phase-to-phase voltages otherwise |

```{note}
These result accessors contain tuples for the results of the first and second sides of the switch.
These are the old accessors to the results of the sides of the switch. They may be deprecated in the
future. The new interface is to use `<side>.res_*` presented below.
```

The following results are available on each side of the switch accessible with `<side>.` prefix where `<side>` is either
`side1` or `side2`:

| Result Accessor         | Default Unit | Type          | Description                                                                                                   |
| ----------------------- | ------------ | ------------- | ------------------------------------------------------------------------------------------------------------- |
| `<side>.res_potentials` | $V$          | complex array | The potentials of each phase of the corresponding switch side                                                 |
| `<side>.res_currents`   | $A$          | complex array | The currents flowing **into** each phase of the corresponding switch side                                     |
| `<side>.res_powers`     | $V\!A$       | complex array | The powers flowing **into** each phase of the corresponding switch side                                       |
| `<side>.res_voltages`   | $V$          | complex array | The voltages of the corresponding switch side: phase-to-neutral if it has a neutral, phase-to-phase otherwise |

And the following results are available for switches _with a neutral and at least one phase_:

| Result Accessor                | Default Unit  | Type          | Description                                                                                            |
| ------------------------------ | ------------- | ------------- | ------------------------------------------------------------------------------------------------------ |
| `<side>.res_voltages_pn`       | $V$           | complex array | The phase-to-neutral voltages of the corresponding switch side                                         |
| `<side>.res_voltage_levels_pn` | $\mathrm{pu}$ | number array  | The voltage levels of each phase of the corresponding switch side ($\sqrt{3} V_{pn} / V_\mathrm{nom}$) |

And the following results are available for switches _with more than one phase_:

| Result Accessor                | Default Unit  | Type          | Description                                                                                   |
| ------------------------------ | ------------- | ------------- | --------------------------------------------------------------------------------------------- |
| `<side>.res_voltages_pp`       | $V$           | complex array | The phase-to-phase voltages of the corresponding switch side                                  |
| `<side>.res_voltage_levels_pp` | $\mathrm{pu}$ | number array  | The voltage levels of each phase of the corresponding switch side ($V_{pp} / V_\mathrm{nom}$) |

And the following results are available for _three-phase_ switches:

| Result Accessor                  | Default Unit | Type   | Description                                                                                          |
| -------------------------------- | ------------ | ------ | ---------------------------------------------------------------------------------------------------- |
| `<side>.res_voltage_unbalance()` | $\%$         | number | The voltage unbalance of the corresponding switch side according to the IEC, IEEE or NEMA definition |
| `<side>.res_current_unbalance()` | $\%$         | number | The Current Unbalance Factor (CUF) of the switch side                                                |

## Usage

Here is a switch connecting a constant power load to a voltage source.

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Two buses
bus1 = rlf.Bus(id="bus1", phases="abcn")
bus2 = rlf.Bus(id="bus2", phases="abcn")

# A switch connecting the two buses
switch = rlf.Switch(id="switch", bus1=bus1, bus2=bus2)

# A voltage source on the first bus
vs = rlf.VoltageSource(id="source", bus=bus1, voltages=400 / rlf.SQRT3)

# The potential of the neutral of bus1 is fixed at 0V
pref = rlf.PotentialRef(id="pref", element=bus1)

# An unbalanced constant-power load on the second bus
load = rlf.PowerLoad(id="load", bus=bus2, powers=[5000 + 1600j, 2500 + 800j, 0])

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# The current flowing into the switch from bus1
en.res_switches[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                 |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:----------------|---------------------------:|------------------------:|
# | ('switch', 'a') |                    22.7321 |                -17.7447 |
# | ('switch', 'b') |                    11.3661 |               -137.745  |
# | ('switch', 'c') |                     0      |                  0      |
# | ('switch', 'n') |                    19.6866 |                132.255  |

# The current flowing into the switch from bus2
en.res_switches[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
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

# The switch is closed by default. Let's open it and add a line

switch.open()
lp = rlf.LineParameters(id="LP", z_line=(0.1 + 0.1j) * np.eye(4))
rlf.Line(id="line", bus1=bus1, bus2=bus2, length=0.1, parameters=lp)
en.solve_load_flow()
# No current flows through the switch now
en.res_switches[["current1"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                 |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:----------------|---------------------------:|------------------------:|
# | ('switch', 'a') |                          0 |                       0 |
# | ('switch', 'b') |                          0 |                       0 |
# | ('switch', 'c') |                          0 |                       0 |
# | ('switch', 'n') |                          0 |                       0 |
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.Switch
   :members:
   :show-inheritance:
   :no-index:
```
