# Short-Circuit

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
... from roseau.load_flow import *

>>> def create_network():
...     # Create three buses
...     source_bus = Bus(id="sb", phases="abcn")
...     bus1 = Bus(id="b1", phases="abcn")
...     bus2 = Bus(id="b2", phases="abcn")
...     # Define the reference of potentials
...     ground = Ground(id="gnd")
...     pref = PotentialRef(id="pref", element=ground)
...     ground.connect(bus=source_bus)
...     # Create a LV source at the first bus
...     un = 400 / np.sqrt(3)
...     source_voltages = [un, un * np.exp(-2j * np.pi / 3), un * np.exp(2j * np.pi / 3)]
...     vs = VoltageSource(id="vs", bus=source_bus, phases="abcn", voltages=source_voltages)
...     # Add LV lines
...     lp1 = LineParameters.from_geometry(
...         "U_AL_240",
...         line_type=LineType.UNDERGROUND,
...         conductor_type=ConductorType.AL,
...         insulator_type=InsulatorType.PVC,
...         section=240,
...         section_neutral=240,
...         height=Q_(-1.5, "m"),
...         external_diameter=Q_(40, "mm"),
...     )
...     line1 = Line(
...         id="line1", bus1=source_bus, bus2=bus1, parameters=lp1, length=1.0, ground=ground
...     )
...     lp2 = LineParameters.from_geometry(
...         "U_AL_150",
...         line_type=LineType.UNDERGROUND,
...         conductor_type=ConductorType.AL,
...         insulator_type=InsulatorType.PVC,
...         section=150,
...         section_neutral=150,
...         height=Q_(-1.5, "m"),
...         external_diameter=Q_(40, "mm"),
...     )
...     line2 = Line(
...         id="line2", bus1=bus1, bus2=bus2, parameters=lp2, length=2.0, ground=ground
...     )
...     # Create network
...     en = ElectricalNetwork.from_element(source_bus)
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
(1, 1.235686457464e-07)
>>> en.res_branches
```

| branch_id | phase | branch_type |           current1 |       current2 |             power1 |                  power2 |      potential1 |        potential2 |
| :-------- | :---- | :---------- | -----------------: | -------------: | -----------------: | ----------------------: | --------------: | ----------------: |
| line1     | a     | line        |      376.73+75.27j | -376.51-75.17j | 87001.28-17383.79j |     -69627.19+24139.31j |       230.94-0j |     190.15-26.15j |
| line1     | b     | line        |     -376.14-74.96j |  376.12+74.96j |  58424.2+66571.89j |     -41140.23-59809.99j |    -115.47-200j |    -74.72-173.91j |
| line1     | c     | line        |        -0.49-0.42j |     0.49+0.21j |      -26.77-147.2j |          -14.92+126.89j |    -115.47+200j |   -117.06+208.26j |
| line1     | n     | line        |          -0.1+0.1j |        -0.1-0j |                 0j |             -0.15+0.85j |              0j |         1.63-8.2j |
| line2     | a     | line        |  **376.51+75.17j** | -376.45-74.93j | 69627.19-24139.31j | **-14217.87+41992.82j** |   190.15-26.15j | **57.69-100.07j** |
| line2     | b     | line        | **-376.12-74.96j** |  376.45+74.93j | 41140.23+59809.99j |  **14217.87-41992.82j** |  -74.72-173.91j | **57.69-100.07j** |
| line2     | c     | line        |        -0.49-0.21j |          -0+0j |      14.92-126.89j |                     -0j | -117.06+208.26j |   -120.25+224.73j |
| line2     | n     | line        |             0.1+0j |          -0+0j |         0.15-0.85j |                   -0+0j |       1.63-8.2j |        4.88-24.6j |

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
(1, 1.23437343475878e-07)
>>> en.res_branches
```

| branch_id | phase | branch_type |        current1 |        current2 |             power1 |              power2 |     potential1 |      potential2 |
| :-------- | :---- | :---------- | --------------: | --------------: | -----------------: | ------------------: | -------------: | --------------: |
| line1     | a     | line        |   371.74-146.3j | -371.55+146.39j | 85849.21+33785.73j | -63525.86-24647.04j |      230.94-0j |    170.63-0.89j |
| line1     | b     | line        | -325.13-309.42j |  325.11+309.42j | 99425.42+29296.79j | -75755.18-20038.43j |   -115.47-200j |  -91.49-148.71j |
| line1     | c     | line        |  -46.49+455.59j |    46.51-455.8j | 96487.73+43308.59j | -75409.94-31858.46j |   -115.47+200j |  -85.88+156.68j |
| line1     | n     | line        |     -0.12+0.12j |     -0.07-0.01j |                 0j |          -0.4+0.53j |             0j |      6.74-7.09j |
| line2     | a     | line        |  371.55-146.39j | -371.59+146.56j | 63525.86+24647.04j |    3541.55-1646.58j |   170.63-0.89j | **-6.74+7.09j** |
| line2     | b     | line        | -325.11-309.42j |   325.28+309.3j | 75755.18+20038.43j |       1.42+4388.76j | -91.49-148.71j | **-6.74+7.09j** |
| line2     | c     | line        |   -46.51+455.8j |   46.31-455.86j | 75409.94+31858.46j |   -3542.97-2742.18j | -85.88+156.68j | **-6.74+7.09j** |
| line2     | n     | line        |      0.07+0.01j |           -0-0j |          0.4-0.53j |                  0j |     6.74-7.09j |    20.21-21.26j |

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
(2, 1.68697431436484e-07)
>>> en.res_branches
```

| branch_id | phase | branch_type |      current1 |      current2 |             power1 |              power2 |      potential1 |      potential2 |
| :-------- | :---- | :---------- | ------------: | ------------: | -----------------: | ------------------: | --------------: | --------------: |
| line1     | a     | line        | 96.01-188.55j | -95.8+188.65j | 22173.11+43543.54j | -16858.62-29476.54j |       230.94+0j |     160.3-7.97j |
| line1     | b     | line        |    0.53-0.42j |   -0.55+0.42j |          22.6-154j |       -3.39+192.42j |    -115.47-200j | -166.27-225.68j |
| line1     | c     | line        |   -0.41-0.51j |    0.43+0.28j |      -54.5-141.67j |      -21.22+121.92j |    -115.47+200j | -162.05+176.44j |
| line1     | n     | line        |   -0.04-0.07j |   -0.17+0.18j |                 0j |          4.2+13.63j |              0j |   -50.72-25.69j |
| line2     | a     | line        |  95.8-188.65j | -95.91+188.9j | 16858.62+29476.54j |                  0j |     160.3-7.97j |          **0j** |
| line2     | b     | line        |    0.55-0.42j |            0j |       3.39-192.42j |               -0+0j | -166.27-225.68j | -267.74-277.02j |
| line2     | c     | line        |   -0.43-0.28j |         -0+0j |      21.22-121.92j |                  0j | -162.05+176.44j | -255.11+129.31j |
| line2     | n     | line        |    0.17-0.18j |            0j |        -4.2-13.63j |               -0+0j |   -50.72-25.69j |  -152.11-77.03j |

```pycon
>>> en.res_grounds
```

| ground_id | potential |
| :-------- | --------: |
| gnd       |        0j |

Here the potential at phase "a" of bus `b2` is zero, equal to the ground potential. The sum of the currents in the
other phases is also zero indicating that the current of phase "a" went through the ground.

## Additional notes

The library will prevent the user from making mistakes, for example when trying to add a power load with the
short-circuit, or when forgetting parameters.

```pycon
>>> try:
...     load = PowerLoad("load", bus=en.buses["b2"], powers=[10, 10, 10])
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
