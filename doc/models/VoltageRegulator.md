---
myst:
  html_meta:
    description lang=en: |
      Voltage regulators in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python
      API by Roseau Technologies.
    keywords lang=en: |
      simulation, distribution grid, voltage regulator, step-voltage regulator, model
    # spellchecker:off
    description lang=fr: |
      Les régulateurs de tension dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et
      déséquilibré dans une API Python par Roseau Technologies.
    keywords lang=fr: |
      simulation, réseau, électrique, régulateur de tension, roseau load flow, modèle
    # spellchecker:on
---

# Voltage Regulator

## Definition

A voltage regulator (or step-voltage regulator) keeps the voltage of its load side (`bus2`) at a
target value `u_ref` by adjusting its tap ratio. It is modelled as a bank of single-phase **units**,
each of them an autotransformer with an on-load tap changer located in its series winding. The two
windings of a unit share a _common_ terminal: unlike a transformer, a voltage regulator does not
isolate its source side from its load side.

Every unit has its own tap ratio $a$, controlled independently: the tap of a unit is an _output_ of
the load flow, not an input. The ideal controller keeps the regulated voltage of the unit at `u_ref`
while its tap stays within $[1 - u_\mathrm{range}, 1 + u_\mathrm{range}]$, and holds the tap at its
bound otherwise.

Each unit is represented below: its input (source side) is connected to the tap of the winding, its
output (load side) to the end of the winding through the series impedance, and the other end of the
winding is the common terminal.

```{image} /_static/VoltageRegulator/Unit.svg
---
alt: Voltage regulator unit diagram
width: 600px
align: center
---
```

## Connections

How the units are connected is given by the `connection` of the
{class}`~roseau.load_flow.RegulatorParameters` (the regulators' counterpart of the vector group of a
transformer). The phases of the regulator, common to both of its sides, must be compatible with it:

| Connection                  | Phases                                                     | Common terminal of the unit of phase $p$     | Regulated voltage |
| --------------------------- | ---------------------------------------------------------- | -------------------------------------------- | ----------------- |
| `"wye"`                     | `"an"`, `"bn"`, `"cn"`, `"abn"`, `"bcn"`, `"can"`, `"abcn"` | The neutral, carried through the regulator   | Phase-to-neutral  |
| `"delta_positive_rotation"` | `"abc"`                                                    | The load-side terminal of the next phase     | Phase-to-phase    |
| `"delta_negative_rotation"` | `"abc"`                                                    | The load-side terminal of the previous phase | Phase-to-phase    |

The `"wye"` connection is a star of single-phase units: each unit is connected between a phase and
the neutral, the neutral being carried through the regulator from one side to the other.

```{image} /_static/VoltageRegulator/Wye_Voltage_Regulator.svg
---
alt: Wye voltage regulator diagram
width: 600px
align: center
---
```

The closed-delta connections are rings: the common terminal of each unit is the load-side terminal
of its neighbour (A → B → C → A for the positive rotation, A → C → B → A for the negative one). At no
load, the unit of phase $p$ whose common terminal is the load-side terminal of phase $q$ outputs

```{math}
\underline{V_{2,p}} = \underline{V_{2,q}} + a_p \left( \underline{V_{1,p}} - \underline{V_{2,q}} \right)
```

so that each tap acts on the three phase-to-phase voltages. This is the closed-delta wiring of
DIgSILENT PowerFactory: the `"delta_positive_rotation"` connection is its (and ANSI/IEEE's)
"lagging" connection, the output voltages leading the input ones when boosting, and the
`"delta_negative_rotation"` connection its "leading" one. A closed delta regulates the voltages over
about $\pm 1.5 \, u_\mathrm{range}$.

The closed delta with a positive rotation is represented below. With a negative rotation, the common
terminal of the unit of phase "a" is the load-side terminal of phase "c", that of the unit of phase
"b" the load-side terminal of phase "a", and that of the unit of phase "c" the load-side terminal of
phase "b".

```{image} /_static/VoltageRegulator/Closed_Delta_Voltage_Regulator.svg
---
alt: Closed-delta voltage regulator diagram
width: 650px
align: center
---
```

Open-delta regulators, stars with a floating neutral and ganged taps are not modelled.

## Equations

With $\underline{U_\mathrm{in}}$ and $\underline{U_\mathrm{out}}$ the source-side and load-side
voltages of a unit relative to its common terminal, the whole leakage impedance $\underline{Z_2}$
being carried by the series winding and $\underline{Y_m}$ being the magnetising admittance of the
shunt winding, the currents entering the unit are:

```{math}
\left\{
    \begin{aligned}
        \underline{I_\mathrm{out}} &= \frac{\underline{U_\mathrm{out}} - a \cdot \underline{U_\mathrm{in}}}{\underline{Z_2}}
        & \text{(load-side terminal)}\\
        \underline{I_\mathrm{in}} &= \underline{Y_m} \cdot \underline{U_\mathrm{in}} - a \cdot \underline{I_\mathrm{out}}
        & \text{(source-side terminal)}\\
        \underline{I_\mathrm{common}} &= - \left( \underline{I_\mathrm{in}} + \underline{I_\mathrm{out}} \right)
        & \text{(common terminal)}
    \end{aligned}
\right.
```

The control law of each unit is the fixed point

```{math}
a = \mathrm{clamp}\left( a \cdot \frac{u_\mathrm{ref}}{\left| \underline{U} \right|}, 1 - u_\mathrm{range}, 1 + u_\mathrm{range} \right)
```

where $\underline{U}$ is the regulated voltage of the unit, measured on the load side: the
phase-to-neutral voltage for a `"wye"` connection, the phase-to-phase voltage divided by $\sqrt{3}$
for a closed delta. `u_ref` is given in per-unit of the nominal (phase-to-phase) voltage `un` of the
parameters: a unit regulates its voltage to $u_\mathrm{ref} \cdot u_n / \sqrt{3}$ for a `"wye"`
connection and to $u_\mathrm{ref} \cdot u_n$ (phase-to-phase) for a closed delta.

The clamp is smoothed with softplus functions of steepness $\alpha$ (the `alpha` parameter, 1000 by
default): only the corners of the characteristic are rounded, over about $1 / \alpha$ in tap ratio.
Inside the regulation range, the regulated voltage is exactly `u_ref` (there is no droop); at a
bound, the tap is held at $1 \pm u_\mathrm{range}$.

## Parameters

The {class}`~roseau.load_flow.RegulatorParameters` define:

- `sn`: the rated (total, throughput) apparent power of the regulator (VA), the power flowing
  through the regulator at its rated current. It is used to compute the loading of the regulator.
  Note that this is not the own catalogue rating of the regulator, which only covers the boosted or
  bucked part of that power: $s_n \cdot u_\mathrm{range}$;
- `un`: the nominal (phase-to-phase) voltage of the regulator (V);
- `z2`: the series impedance of the series winding of each unit ($\Omega$), non-zero;
- `ym`: the magnetising admittance of the shunt winding of each unit (S);
- `u_range`: the voltage regulation range as a fraction, $\pm 10\,\%$ (`0.1`) by default;
- `connection`: how the units are connected, `"wye"` by default;
- `alpha`: the steepness of the softplus functions smoothing the tap bounds, `1000` by default.

The parameters can be shared by several regulators. The target voltage `u_ref` (1.0 p.u. by default)
is set on each {class}`~roseau.load_flow.VoltageRegulator`. The no-load tap of a unit can be computed
and plotted with the {meth}`~roseau.load_flow.RegulatorParameters.compute_tap`,
{meth}`~roseau.load_flow.RegulatorParameters.plot_tap` and
{meth}`~roseau.load_flow.RegulatorParameters.plot_voltage` methods.

## Available Results

The following results are available for all voltage regulators:

| Result Accessor    | Default Unit | Type             | Description                                                                                         |
| ------------------ | ------------ | ---------------- | --------------------------------------------------------------------------------------------------- |
| `res_taps`         | -            | number array     | The tap ratios applied by the units, in the order of `tap_phases`                                   |
| `res_potentials`   | $V$          | 2 complex arrays | The potentials of each phase of the regulator                                                       |
| `res_currents`     | $A$          | 2 complex arrays | The currents flowing into each phase of the regulator                                               |
| `res_powers`       | $V\!A$       | 2 complex arrays | The powers flowing into each phase of the regulator                                                 |
| `res_voltages`     | $V$          | 2 complex arrays | The phase-to-neutral voltages if the regulator has a neutral, the phase-to-phase voltages otherwise |
| `res_power_losses` | $V\!A$       | complex          | The total power losses of the regulator                                                             |
| `res_loading`      | $\mathrm{pu}$ | number          | The loading of the regulator compared to its nominal power                                          |
| `res_violated`     | -            | boolean          | Is the power loading of the regulator exceeding its maximal loading?                                |

The `tap_phases` of a regulator are the pairs of terminals its units are connected between:
`"an"`, `"bn"` and `"cn"` for a `"wye"` connection, `"ab"`, `"bc"` and `"ca"` for a closed delta.
A tap of `1.05` means that the unit boosts its output voltage by 5 %, a tap of `0.95` that it bucks
it by 5 %.

As for the other branches, the results of each side are also accessible with the `side1.` and
`side2.` prefixes, and the results of all the regulators of a network are available in the
{attr}`~roseau.load_flow.ElectricalNetwork.res_regulators` and
{attr}`~roseau.load_flow.ElectricalNetwork.res_regulators_taps` data frames.

## Usage

Here is a three-phase voltage regulator compensating the voltage drop of a long line feeding an
unbalanced load:

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Three buses
bus0 = rlf.Bus(id="bus0", phases="abcn", nominal_voltage=400)
bus1 = rlf.Bus(id="bus1", phases="abcn", nominal_voltage=400)
bus2 = rlf.Bus(id="bus2", phases="abcn", nominal_voltage=400)

# A voltage source on the first bus, its neutral is grounded
vs = rlf.VoltageSource(id="source", bus=bus0, voltages=400 / rlf.SQRT3)
ground = rlf.Ground(id="ground")
rlf.GroundConnection(ground=ground, element=bus0)
pref = rlf.PotentialRef(id="pref", element=ground)

# A long line between the source and the regulator
lp = rlf.LineParameters(id="lp", z_line=(0.3 + 0.1j) * np.eye(4))
line = rlf.Line(id="line", bus1=bus0, bus2=bus1, parameters=lp, length=0.5)

# A wye voltage regulator (one unit per phase, the neutral is carried through)
rp = rlf.RegulatorParameters(
    id="rp", sn=250e3, un=400, z2=0.002 + 0.008j, ym=0, u_range=0.1, connection="wye"
)
regulator = rlf.VoltageRegulator(
    id="regulator", bus1=bus1, bus2=bus2, parameters=rp, u_ref=1.0
)

# An unbalanced constant-power load on the regulated bus
load = rlf.PowerLoad(id="load", bus=bus2, powers=[20e3 + 5e3j, 15e3 + 3e3j, 25e3 + 6e3j])

# Create a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus0)
en.solve_load_flow()

# The voltages of the buses
en.res_buses_voltages[["voltage"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus0', 'an') |                    230.94 |                   0    |
# | ('bus0', 'bn') |                    230.94 |                -120    |
# | ('bus0', 'cn') |                    230.94 |                 120    |
# | ('bus1', 'an') |                    216.43 |                  -2    |
# | ('bus1', 'bn') |                    226.15 |                -119.38 |
# | ('bus1', 'cn') |                    204.91 |                 120.37 |
# | ('bus2', 'an') |                    230.94 |                  -2.16 |
# | ('bus2', 'bn') |                    230.94 |                -119.51 |
# | ('bus2', 'cn') |                    224.96 |                 120.16 |

# The phases "a" and "b" are regulated to 230.94 V (1 pu). The tap of the unit of phase "c" is at
# its upper bound (+10%): its voltage cannot be raised further
en.res_regulators_taps
# |                      |    tap |
# |:---------------------|-------:|
# | ('regulator', 'an')  | 1.0686 |
# | ('regulator', 'bn')  | 1.0222 |
# | ('regulator', 'cn')  | 1.1    |

# The loading of the regulator
regulator.res_loading
# 0.2468 <Unit('dimensionless')>
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.VoltageRegulator
   :members:
   :no-index:

.. autoapiclass:: roseau.load_flow.RegulatorParameters
   :members:
   :no-index:
```
