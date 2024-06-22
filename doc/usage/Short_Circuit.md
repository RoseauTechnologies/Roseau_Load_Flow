---
myst:
  html_meta:
    "description lang=en": |
      A detailed example of a short-circuit calculation with Roseau Load Flow. Easily simulate a phase-to-phase,
      multiphase or phase-to-ground fault.
    "description lang=fr": |
      Un exemple détaillé de calcul de court-circuit avec Roseau Load Flow. Simulez aisément un défaut entre phases,
      multiphasé ou entre phases et terre.
    "keywords lang=fr": simulation, réseau, électrique, court-circuit, entre phases, multiphase, phase-terre
    "keywords lang=en": |
      simulation, distribution grid, short-circuit, phase-to-phase, multiphase, phase-to-ground, calculation
---

# Short-circuit calculations

Let's see how we can make a short-circuit calculation.

We will start by creating a simple network composed of two LV lines. As usual with short-circuit calculations, we
won't add any loads.

```{note}
While impedance and current loads could technically be added to the network, it is not possible to add a power load
on the same bus as the one we want to compute the short-circuit on. This is because having `I = (S/U)*` with `U=0`
is impossible.
```

```pycon
>>> import numpy as np
... import roseau.load_flow as rlf

>>> def create_network():
...     # Create three buses
...     source_bus = rlf.Bus(id="sb", phases="abcn")
...     bus1 = rlf.Bus(id="b1", phases="abcn")
...     bus2 = rlf.Bus(id="b2", phases="abcn")
...     # Define the reference of potentials
...     ground = rlf.Ground(id="gnd")
...     pref = rlf.PotentialRef(id="pref", element=ground)
...     ground.connect(bus=source_bus)
...     # Create a LV source at the first bus
...     un = 400 / np.sqrt(3)
...     source_voltages = [un, un * np.exp(-2j * np.pi / 3), un * np.exp(2j * np.pi / 3)]
...     vs = rlf.VoltageSource(
...         id="vs", bus=source_bus, phases="abcn", voltages=source_voltages
...     )
...     # Add LV lines
...     lp1 = rlf.LineParameters.from_geometry(
...         "U_AL_240",
...         line_type=rlf.LineType.UNDERGROUND,
...         conductor_type=rlf.ConductorType.AL,
...         insulator_type=rlf.InsulatorType.PVC,
...         section=240,
...         section_neutral=120,
...         height=rlf.Q_(-1.5, "m"),
...         external_diameter=rlf.Q_(50, "mm"),
...     )
...     line1 = rlf.Line(
...         id="line1", bus1=source_bus, bus2=bus1, parameters=lp1, length=1.0, ground=ground
...     )
...     lp2 = rlf.LineParameters.from_geometry(
...         "U_AL_150",
...         line_type=rlf.LineType.UNDERGROUND,
...         conductor_type=rlf.ConductorType.AL,
...         insulator_type=rlf.InsulatorType.PVC,
...         section=150,
...         section_neutral=150,
...         height=rlf.Q_(-1.5, "m"),
...         external_diameter=rlf.Q_(40, "mm"),
...     )
...     line2 = rlf.Line(
...         id="line2", bus1=bus1, bus2=bus2, parameters=lp2, length=2.0, ground=ground
...     )
...     # Create network
...     en = rlf.ElectricalNetwork.from_element(source_bus)
...     return en
...

>>> # Create network
... en = create_network()
```

## Phase-to-phase

We can now add a short-circuit. Let's first create a phase-to-phase short-circuit:

```pycon
>>> en.buses["b2"].add_short_circuit("a", "b")
```

Let's run the load flow, and get the current results.

```{note}
If you get an error saying
`roseau.load_flow.RoseauLoadFlowException: The license is not valid. Please use the activate_license(key="...")`,
make sure you follow the instructions in [Solving a load flow](gs-solving-load-flow).
```

```{note}
All the following tables are rounded to 2 decimals to be properly displayed.
```

```pycon
>>> en.solve_load_flow()
(1, 3.339550858072471e-13)
>>> en.res_branches
```

| branch_id | phase | type |           current1 |        current2 |             power1 |                  power2 |      potential1 |        potential2 |
| :-------- | :---- | :--- | -----------------: | --------------: | -----------------: | ----------------------: | --------------: | ----------------: |
| line1     | a     | line |      374.19+65.47j |  -374.2-65.22j) |  86414.44-15119.6j |     -69427.92+23726.69j |       230.94-0j |     190.79-30.15j |
| line1     | b     | line |     -373.43-65.15j |  373.71+64.99j) | 56149.99+67164.05j |     -39212.61-58608.72j |    -115.47-200j |    -75.38-169.94j |
| line1     | c     | line |        -0.88-0.32j |     0.61+0.24j) |      37.17-214.38j |          -22.32+155.56j |    -115.47+200j |   -116.82+208.22j |
| line1     | n     | line |         0.16-0.01j |       -0.13-0j) |                 0j |             -0.17+1.03j |              0j |        1.38-8.15j |
| line2     | a     | line |   **374.2+65.22j** | -374.11-64.94j) | 69427.92-23726.69j | **-15076.23+41188.79j** |   190.79-30.15j | **57.67-100.09j** |
| line2     | b     | line | **-373.71-64.99j** |  374.11+64.94j) | 39212.61+58608.72j |  **15076.23-41188.79j** |  -75.38-169.94j | **57.67-100.09j** |
| line2     | c     | line |        -0.61-0.24j |             -0j |      22.32-155.56j |                   -0-0j | -116.82+208.22j |   -119.55+224.61j |
| line2     | n     | line |            0.13+0j |             -0j |         0.17-1.03j |                     -0j |      1.38-8.15j |       4.18-24.45j |

Looking at the line results of the second bus of the line `line2`, which is `bus2` where we added the short-circuit,
one can notice that:

- the potentials of phases "a" and "b" are equal;
- the currents and powers in phases "a" and "b" are equal with opposite signs, i.e. the sum of the currents is zero;
- the currents and powers in these two phases are very high;

which is expected from a short-circuit.

## Multi-phase

It is possible to create short-circuits between several phases, not only two. Let's first remove the existing
short-circuit then create a new one between phases "a", "b", and "c".

```pycon
>>> en = create_network()
>>> en.buses["b2"].add_short_circuit("a", "b", "c")
>>> en.solve_load_flow()
(1, 6.572520305780927e-13)
>>> en.res_branches
```

| branch_id | phase | type |        current1 |        current2 |             power1 |              power2 |     potential1 |      potential2 |
| :-------- | :---- | :--- | --------------: | --------------: | -----------------: | ------------------: | -------------: | --------------: |
| line1     | a     | line |   364.42-152.4j | -364.45+152.64j | 84159.75+35195.32j | -62323.26-24107.78j |      230.94-0j |    169.06-4.66j |
| line1     | b     | line | -329.25-298.27j |   329.5+298.09j | 97671.94+31407.98j | -74421.29-19633.88j |   -115.47-200j |  -94.56-145.13j |
| line1     | c     | line |  -35.27+450.66j |   35.03-450.73j | 94203.88+44984.19j | -73584.22-31005.25j |   -115.47+200j |  -80.99+156.96j |
| line1     | n     | line |      0.11-0.01j |     -0.08-0.01j |                 0j |          -0.5+0.64j |             0j |      6.47-7.18j |
| line2     | a     | line |  364.45-152.64j | -364.48+152.85j | 62323.26+24107.78j |     3461.67-1626.3j |   169.06-4.66j | **-6.49+7.18j** |
| line2     | b     | line |  -329.5-298.09j |   329.7+297.94j | 74421.29+19633.88j |       1.41+4300.23j | -94.56-145.13j | **-6.49+7.18j** |
| line2     | c     | line |  -35.03+450.73j |   34.78-450.79j | 73584.22+31005.25j |   -3463.08-2673.93j | -80.99+156.96j | **-6.49+7.18j** |
| line2     | n     | line |      0.08+0.01j |             -0j |          0.5-0.64j |                 -0j |     6.47-7.18j |    19.44-21.56j |

Now the potentials of the three phases are equal and the currents and powers add up to zero at the bus where the
short-circuit is applied.

## Phase-to-ground

Phase-to-ground short-circuits are also possible. Let's remove the existing short-circuit and create a new one
between phase "a" and ground.

```pycon
>>> en = create_network()
>>> # ground MUST be passed as a keyword argument
... en.buses["b2"].add_short_circuit("a", ground=en.grounds["gnd"])
>>> en.solve_load_flow()
(1, 2.464140003155535e-13)
>>> en.res_branches
```

| branch_id | phase | type |      current1 |       current2 |             power1 |            power2 |      potential1 |      potential2 |
| :-------- | :---- | :--- | ------------: | -------------: | -----------------: | ----------------: | --------------: | --------------: |
| line1     | a     | line | 95.83-188.13j | -95.86+188.37j | 22130.38+43446.19j | -16871.5-29433.8j |       230.94+0j |    160.32-7.98j |
| line1     | b     | line |    0.96-0.74j |    -0.65+0.52j |      36.74-277.43j |    -10.48+232.63j |    -115.47-200j | -163.66-224.36j |
| line1     | c     | line |   -0.81-0.43j |     0.55+0.33j |       8.47-212.03j |    -29.32+150.27j |    -115.47+200j | -159.37+177.78j |
| line1     | n     | line |    0.24-0.25j |    -0.21+0.22j |                 0j |       4.52+15.58j |              0j |   -48.11-24.34j |
| line2     | a     | line | 95.86-188.37j | -95.99+188.69j |   16871.5+29433.8j |               -0j |    160.32-7.98j |          **0j** |
| line2     | b     | line |    0.65-0.52j |             0j |      10.48-232.63j |             -0-0j | -163.66-224.36j |  -265.1-275.72j |
| line2     | c     | line |   -0.55-0.33j |            -0j |      29.32-150.27j |             -0-0j | -159.37+177.78j | -252.37+130.63j |
| line2     | n     | line |    0.21-0.22j |            -0j |       -4.52-15.58j |             -0-0j |   -48.11-24.34j |  -149.45-75.72j |

```pycon
>>> en.res_grounds
```

| ground_id | potential |
| :-------- | --------: |
| gnd       |      0+0j |

Here the potential at phase "a" of bus `b2` is zero, equal to the ground potential. The sum of the currents in the
other phases is also zero indicating that the current of phase "a" went through the ground.

## Additional notes

The library will prevent the user from making mistakes, for example when trying to add a power load with the
short-circuit, or when forgetting parameters.

```pycon
>>> try:
...     load = rlf.PowerLoad("load", bus=en.buses["b2"], powers=[10, 10, 10])
... except RoseauLoadFlowException as e:
...     print(e)
The power load 'load' is connected on bus 'b2' that already has a short-circuit.
It makes the short-circuit calculation impossible. [bad_short_circuit]
```

```pycon
>>> try:
...     en.buses["b2"].add_short_circuit("a")
... except RoseauLoadFlowException as e:
...     print(e)
For the short-circuit on bus 'b2', expected at least two phases or a phase and a ground.
Only phase 'a' is given. [bad_phase]
```
