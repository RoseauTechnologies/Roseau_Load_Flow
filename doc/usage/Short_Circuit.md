---
myst:
  html_meta:
    description lang=en: |
      A detailed example of a short-circuit calculation with Roseau Load Flow. Easily simulate a phase-to-phase,
      multiphase or phase-to-ground fault.
    keywords lang=en: |
      simulation, distribution grid, short-circuit, phase-to-phase, multiphase, phase-to-ground, calculation
    # spellchecker:off
    description lang=fr: |
      Un exemple détaillé de calcul de court-circuit avec Roseau Load Flow. Simulez aisément un défaut entre phases,
      multiphasé ou entre phases et terre.
    keywords lang=fr: simulation, réseau, électrique, court-circuit, entre phases, multiphase, phase-terre
    # spellchecker:on
---

# Short-circuit calculations

Let's see how we can make a short-circuit calculation.

We will start by creating a simple network composed of two LV lines. As usual with short-circuit calculations, we won't
add any loads.

```{note}
While impedance loads could technically be added to the network, it is not possible to add a power or current load to
a short-circuited bus. This is because having `I = (S/U)*` with `U=0` cannot be solved.
```

```pycon
>>> import roseau.load_flow as rlf

>>> def create_network() -> rlf.ElectricalNetwork:
...     # Define the ground and make it the reference of potentials
...     ground = rlf.Ground(id="Gnd")
...     rlf.PotentialRef(id="PRef", element=ground)
...     # Create three LV buses
...     bus1 = rlf.Bus(id="Bus1", phases="abcn", nominal_voltage=400)
...     bus2 = rlf.Bus(id="Bus2", phases="abcn", nominal_voltage=400)
...     bus3 = rlf.Bus(id="Bus3", phases="abcn", nominal_voltage=400)
...     # Connect the neutral of the first bus to the ground
...     rlf.GroundConnection(ground=ground, element=bus1)
...     # Create a voltage source at the first bus
...     rlf.VoltageSource(id="Src", bus=bus1, voltages=400 / rlf.SQRT3)
...     # Add LV lines
...     lp1 = rlf.LineParameters.from_catalogue("U_AL_3x240+95")
...     lp2 = rlf.LineParameters.from_catalogue("U_AL_3x150+150")
...     rlf.Line(id="Line1", bus1=bus1, bus2=bus2, parameters=lp1, length=1.0, ground=ground)
...     rlf.Line(id="Line2", bus1=bus2, bus2=bus3, parameters=lp2, length=2.0, ground=ground)
...     # Create the network
...     en = rlf.ElectricalNetwork.from_element(bus1)
...     return en

>>> # Create the network
... en = create_network()
```

## Phase-to-phase

We can now add a short-circuit. Let's first create a phase-to-phase short-circuit:

```pycon
>>> en.buses["Bus3"].add_short_circuit("a", "b")
```

Let's run the load flow, and get the current results.

```{note}
If you get an error saying
`roseau.load_flow.RoseauLoadFlowException: The license is not valid. Please use the activate_license(key="...")`,
make sure you follow the instructions in [Solving a load flow](./Getting_Started.md#solving-a-load-flow).
```

```{note}
All the following tables are rounded to 2 decimals to be properly displayed.
```

```pycon
>>> en.solve_load_flow()
(1, 2.5934809855243657e-13)
>>> en.res_lines
```

| line_id | phase |       current1 |           current2 |           power1 |                power2 |      potential1 |        potential2 |    series_losses | series_current | violated | loading | max_loading | ampacity |
| :------ | :---- | -------------: | -----------------: | ---------------: | --------------------: | --------------: | ----------------: | ---------------: | -------------: | :------- | ------: | ----------: | -------: |
| Line1   | a     |  338.25+35.15j |      -338.25-35.1j |    78115.2-8117j |     -63659.5+17359.1j |       230.94-0j |     191.47-31.45j | 14455.7+9251.67j |  338.25+35.12j | False    |    0.88 |           1 |      388 |
| Line1   | b     | -338.13-35.08j |      338.17+35.06j | 46059.1+63575.1j |     -31612.4-54338.4j |    -115.47-200j |    -76.01-168.56j | 14446.8+9245.92j | -338.15-35.07j | False    |    0.88 |           1 |      388 |
| Line1   | c     |    -0.12-0.07j |         0.08+0.05j |         0-32.34j |             -0+21.11j |    -115.47+200j |   -115.46+200.02j |             0+0j |     -0.1-0.06j | False    |       0 |           1 |      388 |
| Line1   | n     |           0+0j |               0+0j |             0+0j |                  0+0j |            0+0j |              0+0j |             0+0j |           0+0j | False    |       0 |           1 |      388 |
| Line2   | a     |   338.25+35.1j | **-338.22-35.05j** | 63659.5-17359.1j | **-16017.7+35850.7j** |   191.47-31.45j | **57.72-100.02j** | 47641.8+18501.7j |  338.24+35.07j | True     |    1.13 |           1 |      300 |
| Line2   | b     | -338.17-35.06j |  **338.22+35.05j** | 31612.4+54338.4j |  **16017.7-35850.7j** |  -76.01-168.56j | **57.72-100.02j** | 47630.1+18497.1j |  -338.2-35.04j | True     |    1.13 |           1 |      300 |
| Line2   | c     |    -0.08-0.05j |               0+0j |         0-21.11j |                  0+0j | -115.46+200.02j |   -115.45+200.03j |             0+0j |    -0.04-0.02j | False    |       0 |           1 |      300 |
| Line2   | n     |           0+0j |               0+0j |             0+0j |                  0+0j |            0+0j |              0+0j |             0+0j |           0+0j | False    |       0 |           1 |      300 |

Looking at the line results of the second bus of the line `Line2`, which is `Bus3` where we added the short-circuit, one
can notice that:

- the potentials of phases "a" and "b" are equal;
- the currents and powers in phases "a" and "b" are equal with opposite signs, i.e. the sum of the currents is zero;
- the currents and powers in these two phases are very high;

which is expected from a short-circuit.

## Multi-phase

It is also possible to create short-circuits between more than two phases. Let's create a short-circuit between phases
"a", "b", and "c".

```pycon
>>> en = create_network()
>>> en.buses["Bus3"].add_short_circuit("a", "b", "c")
>>> en.solve_load_flow()
(1, 3.979039320256561e-13)
>>> en.res_lines
```

| line_id | phase |        current1 |            current2 |           power1 |            power2 |     potential1 |     potential2 |    series_losses |  series_current | violated | loading | max_loading | ampacity |
| :------ | :---- | --------------: | ------------------: | ---------------: | ----------------: | -------------: | -------------: | ---------------: | --------------: | :------- | ------: | ----------: | -------: |
| Line1   | a     |  358.46-160.14j |     -358.46+160.18j | 82782.9+36982.8j | -63514.6-24659.9j |      230.94-0j |   173.32-8.66j | 19268.3+12331.7j |  358.46-160.16j | True     |    1.01 |           1 |      388 |
| Line1   | b     | -317.92-230.37j |      317.95+230.34j | 82782.9+36982.8j | -63514.6-24659.9j |   -115.47-200j | -94.16-145.77j | 19268.3+12331.7j | -317.94-230.35j | True     |    1.01 |           1 |      388 |
| Line1   | c     |  -40.54+390.51j |       40.51-390.53j | 82782.9+36982.8j | -63514.6-24659.9j |   -115.47+200j | -79.16+154.43j | 19268.3+12331.7j |  -40.52+390.52j | True     |    1.01 |           1 |      388 |
| Line1   | n     |            0+0j |                0+0j |             0+0j |              0+0j |           0+0j |           0+0j |             0+0j |            0+0j | False    |       0 |           1 |      388 |
| Line2   | a     |  358.46-160.18j | **-358.46+160.22j** | 63514.6+24659.9j |          **0-0j** |   173.32-8.66j |      **-0+0j** | 63514.6+24665.8j |  358.46-160.22j | True     |    1.31 |           1 |      300 |
| Line2   | b     | -317.95-230.34j |  **317.98+230.32j** | 63514.6+24659.9j |          **0+0j** | -94.16-145.77j |      **-0+0j** | 63514.6+24665.8j | -317.98-230.32j | True     |    1.31 |           1 |      300 |
| Line2   | c     |  -40.51+390.53j |   **40.48-390.54j** | 63514.6+24659.9j |         **-0-0j** | -79.16+154.43j |      **-0+0j** | 63514.6+24665.8j |  -40.48+390.54j | True     |    1.31 |           1 |      300 |
| Line2   | n     |            0+0j |                0+0j |             0+0j |              0+0j |           0+0j |           0+0j |             0+0j |            0+0j | False    |       0 |           1 |      300 |

Now the potentials of the three phases are equal and the currents and powers add up to zero at the bus where the
short-circuit is applied.

## Phase-to-ground

Phase-to-ground short-circuits are also possible. Let's remove the existing short-circuit and create a new one between
phase "a" and ground.

```pycon
>>> en = create_network()
>>> # The ground MUST be passed as a keyword argument
... gnd = en.grounds["Gnd"]
... en.buses["Bus3"].add_short_circuit("a", ground=gnd)
>>> en.solve_load_flow()
(1, 4.985456492079265e-13)
>>> en.res_lines
```

| line_id | phase |       current1 |        current2 |           power1 |            power2 |      potential1 |      potential2 |    series_losses | series_current | violated | loading | max_loading | ampacity |
| :------ | :---- | -------------: | --------------: | ---------------: | ----------------: | --------------: | --------------: | ---------------: | -------------: | :------- | ------: | ----------: | -------: |
| Line1   | a     | 358.46-160.14j | -358.46+160.18j | 82782.9+36982.8j | -63514.6-24659.9j |       230.94+0j |    173.32-8.66j | 19268.3+12331.7j | 358.46-160.16j | True     |    1.01 |           1 |      388 |
| Line1   | b     |     0.12-0.07j |     -0.08+0.05j |         0-32.34j |         -0+21.11j |    -115.47-200j |    -115.49-200j |             0+0j |      0.1-0.06j | False    |       0 |           1 |      388 |
| Line1   | c     |    -0.12-0.07j |      0.08+0.05j |         0-32.34j |         -0+21.11j |    -115.47+200j | -115.46+200.02j |             0+0j |     -0.1-0.06j | False    |       0 |           1 |      388 |
| Line1   | n     |           0+0j |            0+0j |             0+0j |              0+0j |            0+0j |            0+0j |             0+0j |           0+0j | False    |       0 |           1 |      388 |
| Line2   | a     | 358.46-160.18j | -358.46+160.22j | 63514.6+24659.9j |              0-0j |    173.32-8.66j |        **0+0j** | 63514.6+24665.8j | 358.46-160.22j | True     |    1.31 |           1 |      300 |
| Line2   | b     |     0.08-0.05j |       **-0-0j** |         0-21.11j |              0+0j |    -115.49-200j |    -115.51-200j |             0+0j |     0.04-0.02j | False    |       0 |           1 |      300 |
| Line2   | c     |    -0.08-0.05j |        **0+0j** |         0-21.11j |              0+0j | -115.46+200.02j | -115.45+200.03j |             0+0j |    -0.04-0.02j | False    |       0 |           1 |      300 |
| Line2   | n     |           0+0j |        **0+0j** |             0+0j |              0+0j |            0+0j |            0+0j |             0+0j |           0+0j | False    |       0 |           1 |      300 |

```pycon
>>> en.res_grounds
```

| ground_id | potential |
| :-------- | --------: |
| Gnd       |      0+0j |

Here the potential at phase "a" of bus `Bus3` is zero, equal to the ground potential. The currents in the other phases
are also zero indicating that the current of phase "a" went through the ground.

## Additional notes

The library will prevent the user from making mistakes, for example when trying to add a voltage source, a
constant-power, or a constant-current load on a short-circuited bus:

```pycon
>>> try:
...     load = rlf.PowerLoad("Load", bus=en.buses["Bus3"], powers=[10, 10, 10])
... except RoseauLoadFlowException as e:
...     print(e)
Cannot create power load 'Load' on short-circuited bus 'Bus3'. [bad_short_circuit]
```

At least two phases or a phase and a ground must be given when creating a short-circuit:

```pycon
>>> try:
...     en.buses["Bus3"].add_short_circuit("a")
... except RoseauLoadFlowException as e:
...     print(e)
For the short-circuit on bus 'Bus3', expected at least two phases or a phase and a ground.
Only phase 'a' is given. [bad_phase]
```
