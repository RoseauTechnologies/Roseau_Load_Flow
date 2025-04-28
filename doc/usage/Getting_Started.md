---
myst:
  html_meta:
    "description lang=en": |
      A first simple example to introduce you to power flow calculation with Roseau Load Flow: simulate a small
      network with a voltage source, a transformer, a line and a load.
    "description lang=fr": |
      Un premier exemple simple pour s'initier au calcul d'écoulement de puissance avec Roseau Load Flow. Simulez un
      petit réseau comportant une source de tension, un transformateur, une ligne et une charge.
    "keywords lang=fr": |
      load flow, python, écoulement de charge, écoulement de puissance, réseau de distribution, source, charge, ligne,
      exemple
    "keywords lang=en": |
      Roseau, Load flow, python, power flow, distribution grid, voltage source, power load, line, example
---

# Getting started with Roseau Load Flow

_Make sure you have followed the_ [installation instructions](../Installation.md).

In this tutorial you will learn how to:

1. [Create a simple electrical network with one source and one load](#creating-a-network);
2. [Solve a load flow](#solving-a-load-flow);
3. [Get the results of the load flow](#getting-the-results);
4. [Analyze the results](#analyzing-the-results-and-detecting-violations);
5. [Update the elements of the network](#updating-elements-of-the-network);
6. [Save the network to a file and load a saved network](#savingloading-the-network);

## Creating a network

An electrical network can be built by assembling basic elements described in the
[Models section](../models/index.md). The following is a summary of the available elements:

- Buses:

  - [`Bus`](../models/Bus.md): A multi-phase node where other elements can be connected. The bus
    optionally defines the nominal voltages and voltage limits of the network to study violations.

- Branches:

  - [`Line`](../models/Line/index.md): An impedant connection between two buses on the same voltage
    level. The impedance of the line and its physical characteristics are defined by the
    `LineParameters` object. This object can be defined once and used to describe multiple lines.
  - [`Switch`](../models/Switch.md): An ideal connection between two buses on the same voltage level.
    Currently, a switch cannot be opened.
  - [`Transformer`](../models/Transformer/index.md): A transformer connecting a buses on potentially
    different voltage levels called the high-voltage side and the low-voltage side. The impedance of
    the transformer and its physical characteristics including its winding configuration are defined
    by a `TransformerParameters` object. This object can be defined once and used to describe multiple
    transformers.

- Loads:

  The _ZIP load model_ is available via the following [load](../models/Load/index.md) classes:

  - [`ImpedanceLoad`](../models/Load/ImpedanceLoad.md): A constant impedance (Z) load:
    $\overline{S} = V^2 / \overline{Z}$ where $\overline{Z}$ is constant -- $S$ is proportional to
    $V^2$.
  - [`CurrentLoad`](../models/Load/CurrentLoad.md) A constant current (I) load:
    $\overline{S} = \overline{V} \times \overline{I}^*$ where $\overline{I}$ is constant -- $S$ is
    proportional to $V^1$.
  - [`PowerLoad`](../models/Load/PowerLoad.md): A constant power (P) load:
    $\overline{S} = \mathrm{constant}$ -- $S$ is proportional to $V^0$.

    A power load can be made [flexible](../models/Load/FlexibleLoad/index.md) (controllable) by
    using `FlexibleParameter` objects. This object defines the parameters of the flexible load's
    control (Maximum power, projection, type, etc.) Note that flexible loads are an advanced feature
    that most users don't need. They are explained in details [here](usage-flexible-loads).

- Sources:

  - [`VoltageSource`](../models/VoltageSource.md): An infinite power ideal source with a constant
    voltage.

- Other elements:
  - [`Ground`](../models/Ground.md): A perfect conductor that can be connected to various elements.
    If two elements are connected to the same ground, the potentials at the connection points are
    always equal.
  - [`PotentialRef`](../models/PotentialRef.md): Sets the reference of potentials in the network. It
    can be connected to buses or grounds.

Let's use some of these elements to build the following simple low voltage network. A voltage source
represents the upstream medium voltage network. A MV/LV transformer, a simple three-phase four-wire
line and a constant power load represent the low voltage network.

![Network](../_static/Getting_Started_Tutorial.svg)

```pycon
>>> import numpy as np
... import roseau.load_flow as rlf

>>> # Define the upstream MV network represented by an infinite voltage source
... # ------------------------------------------------------------------------
... # Define the MV bus with a nominal voltage of 20 kV
... mv_bus = rlf.Bus(
...     # ⮦ Required parameters
...     id="MV_Bus",  # Unique identifier
...     phases="abc",  # no neutral (typical MV bus)
...     # ⮦ Optional parameters for analyzing network violations
...     nominal_voltage=20e3,  # 20 kV (typical MV voltage)
...     min_voltage_level=0.95,  # 95% of the nominal voltage
...     max_voltage_level=1.05,  # 105% of the nominal voltage
... )
... # Create a three-phase voltage source at the MV bus
... vs = rlf.VoltageSource(id="Source", bus=mv_bus, voltages=20e3)

>>> # Define the LV network: 2km line ending with a 30kW load
... # -------------------------------------------------------
... lv_bus1 = rlf.Bus(
...     id="LV_Bus1",
...     phases="abcn",  # with neutral (typical LV bus)
...     nominal_voltage=400,  # 400 V (typical LV voltage)
...     min_voltage_level=0.9,
...     max_voltage_level=1.1,
... )
... lv_bus2 = rlf.Bus(
...     id="LV_Bus2",
...     phases="abcn",
...     nominal_voltage=400,
...     min_voltage_level=0.9,
...     max_voltage_level=1.1,
... )
... # Add a 2 km line between the LV buses with R = 0.1 Ohm/km and X = 0
... lp = rlf.LineParameters("LP", z_line=(0.1 + 0j) * np.eye(4), ampacities=500)
... line = rlf.Line(id="LV_Line", bus1=lv_bus1, bus2=lv_bus2, parameters=lp, length=2.0)
... # Add a 30kW load at the second bus (balanced load, 10 kW per phase)
... load = rlf.PowerLoad(id="Load", bus=lv_bus2, powers=10e3 + 0j)  # In VA

>>> # Define the MV/LV transformer connecting the two networks
... # --------------------------------------------------------
... # For simplicity, we choose a transformer from the catalogue
... tp = rlf.TransformerParameters.from_catalogue("SE Minera AA0Ak 160kVA 20kV 410V Dyn11")
... transformer = rlf.Transformer(
...     id="MV/LV_Transformer",
...     bus_hv=mv_bus,
...     bus_lv=lv_bus1,
...     parameters=tp,
... )
... # Earth the neutral wire of transformer's neutral on the LV side
... ground = rlf.Ground(id="Ground")  # Represents the earth
... rlf.GroundConnection(ground=ground, element=lv_bus1, phase="n")
... # # Optionally earth the load's neutral
... # rlf.GroundConnection(ground=ground, element=lv_bus2, phase="n")

>>> # Set the references of potentials for each network (explained later)
... # -------------------------------------------------------------------
... pref_mv = rlf.PotentialRef(id="PRef_MV", element=mv_bus)
... pref_lv = rlf.PotentialRef(id="PRef_LV", element=ground)  # or lv_bus1
```

Notice how the phases of the elements are not explicitly given. They are inferred from the buses
they are connected to. The load and line will have their phases set to `"abcn"` while the source
will have its phases set to `"abc"`. You can also explicitly declare the phases of these elements.
For example, to create a star-connected (Wye) source instead, you can explicitly set its phases to
`"abcn"`:

```pycon
>>> # A star-connected source has "abcn" phases
... vs_star = rlf.VoltageSource(
...     id="Y Source", bus=mv_bus, voltages=un / rlf.SQRT3, phases="abcn"
... )
```

Here, the source voltages become phase-to-neutral (`un / rlf.SQRT3`), and not phase-to-phase (`un`).
This is because, everywhere in `roseau-load-flow`, the `voltages` of an element depend on the
element's `phases`. Voltages of elements connected in a _Star (wye)_ configuration (elements that
have a neutral connection indicated by the presence of the `'n'` character in their `phases`
attribute) are the **phase-to-neutral** voltages. Voltages of elements connected in a _Delta_
configuration (elements that do not have a neutral connection indicated by the absence of the `'n'`
char from their `phases` attribute) are the **phase-to-phase** voltages. To see between which phases
the voltage is defined, you can use the `voltage_phases` property of the element.

```pycon
>>> vs.voltage_phases
['ab', 'bc', 'ca']
>>> vs_star.voltage_phases
['an', 'bn', 'cn']
```

When creating the load, we passed a single value to the `powers` argument. This is a convenience
feature that assumes that the load is balanced and that the value passed for the power should be
used for all phases. If the load is unbalanced, you can pass a list of `powers` for each phase:

```pycon
>>> load = rlf.PowerLoad(id="Load", bus=lv_bus2, powers=[10e3, 5e3, 5e3])
```

At this point, all the basic elements of the network have been defined and connected. Now,
everything can be encapsulated in an `ElectricalNetwork` object, but first, some important
notes on the `Ground` and `PotentialRef` elements:

```{important}
The `Ground` element does not have a fixed potential as one would expect from a real ground
connection. The ground element here merely represents a "perfect conductor", equivalent to a
single-conductor line with zero impedance. The potential reference, 0 Volts, is defined by the
`PotentialRef` element that itself can be connected to any bus or ground in the network. This
gives the users more flexibility to define the potential reference of their network.

A `PotentialRef` defines the potential reference for the network. It is a mandatory reference
for the load flow resolution to be well-defined. A network **MUST** have one and only one potential
reference **per galvanically isolated section**.

When in doubt, define the ground and potential references similar to the example above.
```

An `ElectricalNetwork` object can now be created using the `from_element` constructor. The source
bus `mv_bus` is given to this constructor. All the elements connected to this bus are automatically
included into the network.

```pycon
>>> en = rlf.ElectricalNetwork.from_element(mv_bus)
... en
<ElectricalNetwork: 3 buses, 1 line, 1 transformer, 0 switches, 1 load, 1 source, 1 ground, 2 potential refs>
```

## Solving a load flow

A [license](../License.md) is required. You can use the
[free but limited licence key](../License.md#types-of-licenses)
or get a personal and unlimited key by contacting us at
[contact@roseautechnologies.com](mailto:contact@roseautechnologies.com).
Once you have your license key, you can activate it by following the
[License activation instructions](../License.md#get-and-activate-your-license).

Afterwards, the load flow can be solved by calling the `solve_load_flow` method of the `ElectricalNetwork`

```pycon
>>> en.solve_load_flow()
(2, 1.8595620332462204e-07)
```

It returns the number of iterations performed by the solver, and the residual error after convergence.
Here, the load flow converged in 2 iterations with a residual error of $1.86 \times 10^{-7}$.

## Getting the results

Results can be accessed through the properties prefixed with `res_` on each element. For instance,
the potentials of the load bus (`"LV_Bus2"`) can be accessed using the `lv_bus2.res_potentials`
property. It contains 4 values representing the potentials of its phases `a`, `b`, `c` and `n`
(neutral). The potentials are returned as complex numbers. Calling `abs(lv_bus2.res_potentials)`
returns their magnitude (in Volts) and `np.angle(lv_bus2.res_potentials)` returns their angle
(phase shift) in radians.

Roseau Load Flow uses [Pint's](https://pint.readthedocs.io/en/stable/) `Quantity` objects to present
unit-aware data to the user. _Most_ input data (load powers, source voltages, etc.) are expected
to be either given in SI units or using the pint Quantity interface for non-SI units (example below).
Look at the documentation of a method to see its default units.

In the following example, we create a load with powers expressed in kVA:

```pycon
>>> load = rlf.PowerLoad(id="load", bus=lv_bus2, phases="abcn", powers=rlf.Q_(10, "kVA"))
```

The results returned by the `res_` properties are also `Quantity` objects.

### Available results

The available results depend on the type of element. The [models page](../models/index.md) of each
element lists its available results.

### Getting results per object

_All results shown below are rounded to 2 decimal places for better presentation._

In order to get the potentials of a bus, use its `res_potentials` property:

```pycon
>>> lv_bus2.res_potentials
<Quantity([ 227.4   -1.71j -115.18-196.08j -112.22+197.79j   -0.    +0.j  ], 'volt')>
>>> abs(lv_bus2.res_potentials)
<Quantity([227.41 227.41 227.41   0.  ], 'volt')>
```

As the results are _pint quantities_, they can be converted to different units easily.

```pycon
>>> abs(lv_bus2.res_potentials).to("kV")  # Get a Quantity in kV
<Quantity([0.23 0.23 0.23 0.  ], 'kilovolt')>
>>> abs(lv_bus2.res_potentials).m_as("kV")  # Get the magnitude in kV
array([0.23, 0.23, 0.23, 0.  ])
>>> abs(lv_bus2.res_potentials).m  # Get the magnitude in the default unit (V)
array([227.41, 227.41, 227.41,   0.  ])
```

```{note}
Voltages of a bus can be accessed similar to the potentials using the `res_voltages` property. This
returns the phase-to-neutral voltages of the bus if it has a neutral, and the phase-to-phase voltages
otherwise. If you want to always get the phase-to-neutral voltages, use the `res_voltages_pn`
property (only available for buses with a neutral). If you want to always get the phase-to-phase
voltages, use the `res_voltages_pp` property (only available for buses with more than one phase).
For a list of available results for buses, see the [Bus model page](../models/Bus.md#available-results).
```

The currents of the line are available using the `res_currents` property of the `line` object.
It contains two arrays:

- the first is the current flowing from the first bus of the line to the second bus of the line.
  It contains 4 values: one per phase and the neutral current.
- the second is the current flowing from the second bus of the line to the first bus of the line.

```pycon
>>> line.res_currents
(<Quantity([ 43.97 -0.33j -22.27-37.92j -21.7 +38.25j   0.   -0.j  ], 'ampere')>,
 <Quantity([-43.97 +0.33j  22.27+37.92j  21.7 -38.25j  -0.   +0.j  ], 'ampere')>)
>>> line.res_currents[0] + line.res_currents[1]
<Quantity([0.+0.j 0.+0.j 0.+0.j 0.+0.j], 'ampere')>
```

Here, the sum of these currents is 0 as we have chosen a simple line model, i.e, a line with only
series impedance elements without shunt components. If shunt components were modelled, the sum
would have been non-zero.

### Dataframe network results

The results can also be retrieved for the entire network using `res_` properties of the
`ElectricalNetwork` instance as pandas dataframes.

The main results available on the network are:

- `res_buses`: Buses potentials indexed by _(bus id, phase)_
- `res_transformers`: Transformers currents, powers, potentials, and power limits indexed by
  _(transformer id, phase)_
- `res_lines`: Lines currents, powers, potentials, series losses, series currents, and current
  limits indexed by _(line id, phase)_
- `res_switches`: Switches currents, powers, and potentials indexed by _(switch id, phase)_
- `res_loads`: Loads currents, powers, and potentials indexed by _(load id, phase)_
- `res_sources`: Sources currents, powers, and potentials indexed by _(source id, phase)_
- `res_grounds`: Grounds potentials indexed by _ground id_
- `res_potential_refs`: Potential references currents indexed by _potential ref id_ (always zero
  for a successful load flow)

The following additional results are also available for the network:

- `res_buses_voltages`: Buses voltages and voltage limits indexed by _(bus id, voltage phase²)_
- `res_buses_voltages_pn`: Buses phase-to-neutral voltages and voltage limits indexed by
  _(bus id, voltage phase²)_. Only buses with a neutral are included
- `res_buses_voltages_pp`: Buses phase-to-phase voltages and voltage limits indexed by
  _(bus id, voltage phase²)_. Only buses with more than one phase are included
- `res_loads_voltages`: Loads voltages indexed by _(load id, voltage phase)_
- `res_loads_voltages_pn`: Loads phase-to-neutral voltages indexed by _(load id, voltage phase)_
  Only loads with a neutral are included
- `res_loads_voltages_pp`: Loads phase-to-phase voltages indexed by _(load id, voltage phase)_. Only
  loads with more than one phase are included
- `res_loads_flexible_powers`: Loads flexible powers indexed by _(load id, voltage phase)_. Only
  flexible loads are included
- `res_sources_voltages`: Sources voltages indexed by _(source id, voltage phase)_
- `res_sources_voltages_pn`: Sources phase-to-neutral voltages indexed by _(source id, voltage phase)_
  Only sources with a neutral are included
- `res_sources_voltages_pp`: Sources phase-to-phase voltages indexed by _(source id, voltage phase)_.
  Only sources with more than one phase are included

² _a "voltage phase" is a composite phase like `an` or `ab`_

All the results are complex numbers. You can always access the magnitude of the results using
the `abs` function and the angle in radians using the `np.angle` function. For instance,
`abs(network.res_loads)` gives you the magnitude of the loads' results in SI units.

Below are the results of the load flow for `en`:

```pycon
>>> en.res_buses
```

| bus_id  | phase |          potential |
| :------ | :---- | -----------------: |
| MV_Bus  | a     |  10000.00-5773.50j |
| MV_Bus  | b     | -10000.00-5773.50j |
| MV_Bus  | c     |     0.00+11547.01j |
| LV_Bus1 | a     |       236.19-1.77j |
| LV_Bus1 | b     |    -119.63-203.66j |
| LV_Bus1 | c     |    -116.56+205.44j |
| LV_Bus1 | n     |         0.00+0.00j |
| LV_Bus2 | a     |       227.40-1.71j |
| LV_Bus2 | b     |    -115.18-196.08j |
| LV_Bus2 | c     |    -112.22+197.79j |
| LV_Bus2 | n     |        -0.00+0.00j |

```pycon
>>> en.res_lines
```

| line_id | phase |      current1 |     current2 |         power1 |          power2 |      potential1 |      potential2 | series_losses | series_current | violated | loading | max_loading | ampacity |
| :------ | :---- | ------------: | -----------: | -------------: | --------------: | --------------: | --------------: | ------------: | -------------: | :------- | ------: | ----------: | -------: |
| LV_Line | a     |   43.97-0.33j | -43.97+0.33j | 10386.74+0.00j | -10000.00-0.00j |    236.19-1.77j |    227.40-1.71j |  386.74+0.00j |    43.97-0.33j | False    |    0.09 |        1.00 |   500.00 |
| LV_Line | b     | -22.27-37.92j | 22.27+37.92j | 10386.74+0.00j | -10000.00-0.00j | -119.63-203.66j | -115.18-196.08j |  386.74+0.00j |  -22.27-37.92j | False    |    0.09 |        1.00 |   500.00 |
| LV_Line | c     | -21.70+38.25j | 21.70-38.25j | 10386.74+0.00j | -10000.00-0.00j | -116.56+205.44j | -112.22+197.79j |  386.74+0.00j |  -21.70+38.25j | False    |    0.09 |        1.00 |   500.00 |
| LV_Line | n     |    0.00-0.00j |  -0.00+0.00j |     0.00+0.00j |      0.00-0.00j |      0.00+0.00j |     -0.00+0.00j |    0.00-0.00j |     0.00-0.00j | False    |    0.00 |        1.00 |   500.00 |

```pycon
>>> en.res_transformers
```

| transformer_id    | phase |  current_hv |   current_lv |          power_hv |        power_lv |       potential_hv |    potential_lv | violated | loading | max_loading |        sn |
| :---------------- | :---- | ----------: | -----------: | ----------------: | --------------: | -----------------: | --------------: | :------- | ------: | ----------: | --------: |
| MV/LV_Transformer | a     |  0.44-1.06j | -43.97+0.33j | 10471.96+8077.92j | -10386.74-0.00j |  10000.00-5773.50j |    236.19-1.77j | False    |    0.25 |        1.00 | 160000.00 |
| MV/LV_Transformer | b     | -1.14+0.15j | 22.27+37.92j | 10471.96+8077.92j | -10386.74-0.00j | -10000.00-5773.50j | -119.63-203.66j | False    |    0.25 |        1.00 | 160000.00 |
| MV/LV_Transformer | c     |  0.70+0.91j | 21.70-38.25j | 10471.96+8077.92j | -10386.74-0.00j |     0.00+11547.01j | -116.56+205.44j | False    |    0.25 |        1.00 | 160000.00 |
| MV/LV_Transformer | n     |   nan+0.00j |   0.00-0.00j |         nan+0.00j |      0.00+0.00j |          nan+0.00j |      0.00+0.00j | False    |    0.25 |        1.00 | 160000.00 |

```pycon
>>> en.res_switches  # empty as the network does not contain switches
```

| switch_id | phase | current1 | current2 | power1 | power2 | potential1 | potential2 |
| --------- | ----- | -------- | -------- | ------ | ------ | ---------- | ---------- |

```pycon
>>> en.res_loads
```

| load_id | phase | type  |       current |          power |       potential |
| :------ | :---- | :---- | ------------: | -------------: | --------------: |
| Load    | a     | power |   43.97-0.33j | 10000.00+0.00j |    227.40-1.71j |
| Load    | b     | power | -22.27-37.92j | 10000.00+0.00j | -115.18-196.08j |
| Load    | c     | power | -21.70+38.25j | 10000.00+0.00j | -112.22+197.79j |
| Load    | n     | power |    0.00-0.00j |    -0.00-0.00j |     -0.00+0.00j |

```pycon
>>> en.res_sources
```

| source_id | phase | type    |     current |              power |          potential |
| :-------- | :---- | :------ | ----------: | -----------------: | -----------------: |
| Source    | a     | voltage | -0.44+1.06j | -10471.96-8077.92j |  10000.00-5773.50j |
| Source    | b     | voltage |  1.14-0.15j | -10471.96-8077.92j | -10000.00-5773.50j |
| Source    | c     | voltage | -0.70-0.91j | -10471.96-8077.92j |     0.00+11547.01j |

```pycon
>>> en.res_grounds
```

| ground_id |  potential |
| :-------- | ---------: |
| Ground    | 0.00+0.00j |

```pycon
>>> en.res_potential_refs
```

| potential_ref_id |    current |
| :--------------- | ---------: |
| PRef_MV          | 0.00+0.00j |
| PRef_LV          | 0.00-0.00j |

And some voltage results:

```pycon
>>> en.res_buses_voltages
```

| bus_id  | phase |             voltage | violated | voltage_level | min_voltage_level | max_voltage_level | nominal_voltage |
| :------ | :---- | ------------------: | :------- | ------------: | ----------------: | ----------------: | --------------: |
| MV_Bus  | ab    |      20000.00+0.00j | False    |          1.00 |              0.95 |              1.05 |        20000.00 |
| MV_Bus  | bc    | -10000.00-17320.51j | False    |          1.00 |              0.95 |              1.05 |        20000.00 |
| MV_Bus  | ca    | -10000.00+17320.51j | False    |          1.00 |              0.95 |              1.05 |        20000.00 |
| LV_Bus1 | an    |        236.19-1.77j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus1 | bn    |     -119.63-203.66j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus1 | cn    |     -116.56+205.44j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | an    |        227.40-1.71j | False    |          0.98 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | bn    |     -115.18-196.08j | False    |          0.98 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | cn    |     -112.22+197.79j | False    |          0.98 |              0.90 |              1.10 |          400.00 |

The voltage results are a mix of phase-to-phase and phase-to-neutral voltages. To get only
phase-to-phase voltages, use the `res_buses_voltages_pp` property:

```pycon
>>> en.res_buses_voltages_pp
```

| bus_id  | phase |             voltage | violated | voltage_level | min_voltage_level | max_voltage_level | nominal_voltage |
| :------ | :---- | ------------------: | :------- | ------------: | ----------------: | ----------------: | --------------: |
| MV_Bus  | ab    |      20000.00+0.00j | False    |          1.00 |              0.95 |              1.05 |        20000.00 |
| MV_Bus  | bc    | -10000.00-17320.51j | False    |          1.00 |              0.95 |              1.05 |        20000.00 |
| MV_Bus  | ca    | -10000.00+17320.51j | False    |          1.00 |              0.95 |              1.05 |        20000.00 |
| LV_Bus1 | ab    |      355.83+201.89j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus1 | bc    |       -3.07-409.10j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus1 | ca    |     -352.76+207.21j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | ab    |      342.58+194.37j | False    |          0.98 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | bc    |       -2.96-393.87j | False    |          0.98 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | ca    |     -339.62+199.50j | False    |          0.98 |              0.90 |              1.10 |          400.00 |

And to get only phase-to-neutral voltages, use the `res_buses_voltages_pn` property. Note that
only buses with a neutral are included in the results:

```pycon
>>> en.res_buses_voltages_pn
```

| bus_id  | phase |         voltage | violated | voltage_level | min_voltage_level | max_voltage_level | nominal_voltage |
| :------ | :---- | --------------: | :------- | ------------: | ----------------: | ----------------: | --------------: |
| LV_Bus1 | an    |    236.19-1.77j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus1 | bn    | -119.63-203.66j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus1 | cn    | -116.56+205.44j | False    |          1.02 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | an    |    227.40-1.71j | False    |          0.98 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | bn    | -115.18-196.08j | False    |          0.98 |              0.90 |              1.10 |          400.00 |
| LV_Bus2 | cn    | -112.22+197.79j | False    |          0.98 |              0.90 |              1.10 |          400.00 |

The same can be done for the loads:

```pycon
>>> en.res_loads_voltages
```

| load_id | phase | type  |         voltage |
| :------ | :---- | :---- | --------------: |
| Load    | an    | power |    227.40-1.71j |
| Load    | bn    | power | -115.18-196.08j |
| Load    | cn    | power | -112.22+197.79j |

Using the `transform` method of data frames, the results can easily be converted from complex values
to magnitude and angle values (radians).

```pycon
>>> en.res_buses_voltages_pp["voltage"].transform([np.abs, np.angle])
```

| bus_id  | phase | absolute | angle |
| :------ | :---- | -------: | ----: |
| MV_Bus  | ab    | 20000.00 |  0.00 |
| MV_Bus  | bc    | 20000.00 | -2.09 |
| MV_Bus  | ca    | 20000.00 |  2.09 |
| LV_Bus1 | ab    |   409.11 |  0.52 |
| LV_Bus1 | bc    |   409.11 | -1.58 |
| LV_Bus1 | ca    |   409.11 |  2.61 |
| LV_Bus2 | ab    |   393.88 |  0.52 |
| LV_Bus2 | bc    |   393.88 | -1.58 |
| LV_Bus2 | ca    |   393.88 |  2.61 |

Or, if you prefer the angles in degrees:

```pycon
>>> import functools as ft
... en.res_buses_voltages_pp["voltage"].transform([np.abs, ft.partial(np.angle, deg=True)])
```

| bus_id  | phase | absolute |   angle |
| :------ | :---- | -------: | ------: |
| MV_Bus  | ab    | 20000.00 |    0.00 |
| MV_Bus  | bc    | 20000.00 | -120.00 |
| MV_Bus  | ca    | 20000.00 |  120.00 |
| LV_Bus1 | ab    |   409.11 |   29.57 |
| LV_Bus1 | bc    |   409.11 |  -90.43 |
| LV_Bus1 | ca    |   409.11 |  149.57 |
| LV_Bus2 | ab    |   393.88 |   29.57 |
| LV_Bus2 | bc    |   393.88 |  -90.43 |
| LV_Bus2 | ca    |   393.88 |  149.57 |

## Analyzing the results and detecting violations

In the example network above, `min_voltage_level`, `max_voltage_level` and `nominal_voltage` arguments
were passed to the `Bus` constructor and `ampacities` was passed to the `LineParameters` constructor.
In addition with the `max_loading` parameters of the `Line` and `Transformer`, these arguments define
the limits of the network that can be used to check if the network is in a valid state or not. Note
that these limits have no effect on the load flow calculation.

If you set `nominal_voltage` with `min_voltage_level` or `max_voltage_level` on a bus, the
`res_violated` property will tell you if the voltage limits are violated or not at this bus. Here,
the voltage limits are not violated.

```pycon
>>> lv_bus2.res_violated
array([False, False, False])
```

Similarly, if you set `ampacities` on a line parameters and `max_loading` (defaults to 100% of the
ampacity) on a line, the `res_loading` property will give you the current loading of each phase of
the line. The `res_violated` property will tell you if the current loading of the line in any phase
exceeds its limit. Here, the current limit is not violated.

```pycon
>>> line.res_loading
<Quantity([0.09 0.09 0.09 0.  ], 'dimensionless')>
>>> line.res_violated
array([False, False, False, False])
```

The maximum loading of the transformer can be defined using the `max_loading` argument of the
`Transformer` (defaults to 100% of the nominal power). Transformers also have a `res_loading` to
indicate the loading of the transformer and a `res_violated` property that indicates whether the
power loading of the transformer exceeds its limit.

```pycon
>>> transformer.res_loading
<Quantity(0.247978811, 'dimensionless')>
>>> transformer.res_violated
False
```

The data frame results on the electrical network also include a `loading`, a `max_loading` and a
`violated` columns.

```{tip}
You can use the {meth}`Bus.propagate_limits() <roseau.load_flow.Bus.propagate_limits>` method to
propagate the limits from a bus to buses connected to it galvanically (i.e. via lines or switches).
```

## Updating elements of the network

Network elements can be updated. For example, we can change the load's power values to create an
unbalanced situation.

```pycon
>>> # 15 kW on phase "a", 0 W on phases "b" and "c"
... load.powers = rlf.Q_([15 + 0j, 0 + 0j, 0 + 0j], "kVA")
>>> en.solve_load_flow()
(3, 1.1027623258996755e-11)
>>> abs(lv_bus2.res_potentials)
<Quantity([221.36 236.71 236.71  14.5 ], 'volt')>
```

Notice how the unbalance is manifested in the neutral's potential of the bus no longer being at 0 V.
You can also obtain the voltage unbalance factor (VUF) according to the IEC definition:

```pycon
>>> lv_bus2.res_voltage_unbalance()
<Quantity(2.24730245, 'percent')>
```

More information on modifying the network elements can be found [here](./Connecting_Elements.md).

## Saving/loading the network

An electrical network can be written to a JSON file for later analysis or for sharing with others
using the {meth}`~roseau.load_flow.ElectricalNetwork.to_json` method.

```pycon
>>> en.to_json("my_network.json")
```

For more information, see [network JSON serialization](./Data_Exchange.md#roseau-load-flow-json).
