---
myst:
  html_meta:
    "description lang=en": |
      Quickly create a new electrical model by assembling sources, constant or flexible loads and lines, or load one
      of the many existing models.
    "description lang=fr": |
      Créez rapidement un nouveau modèle électrique en assemblant des sources, des charges et des lignes, ou
      chargez un des nombreux modèles existants.
    "keywords lang=fr": |
      Roseau, load flow, python, écoulement de charge, écoulement de puissance, réseau de distribution, modèle
    "keywords lang=en": Roseau, Load flow, python, power flow, distribution grid, three-phase, model
---

(usage-modifying-network)=

# Creating and editing a network

## Creating a network

Let's take the electrical network of the [Getting started page](usage-getting-started) as an example.

```pycon
>>> import numpy as np
... import roseau.load_flow as rlf

>>> source_bus = rlf.Bus(id="sb", phases="abcn")
... load_bus = rlf.Bus(id="lb", phases="abcn")

>>> ground = rlf.Ground(id="gnd")
... pref = rlf.PotentialRef(id="pref", element=ground)
... ground.connect(source_bus, phase="n")

>>> un = 400 / np.sqrt(3)
... source_voltages = [un, un * np.exp(-2j * np.pi / 3), un * np.exp(2j * np.pi / 3)]
... vs = rlf.VoltageSource(id="vs", bus=source_bus, voltages=source_voltages)

>>> load = rlf.PowerLoad(id="load", bus=load_bus, powers=[10e3 + 0j, 10e3, 10e3])  # VA

>>> lp = rlf.LineParameters("lp", z_line=(0.1 + 0.0j) * np.eye(4))
... line = rlf.Line(
...     id="line", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=2.0
... )
```

At this point, all the elements are connected, but they do not belong to a network:

```pycon
>>> load.network
None
```

Then, creating an electrical network populates all the `network` fields of elements belonging to this network:

```pycon
>>> en = rlf.ElectricalNetwork.from_element(source_bus)
>>> load.network
<ElectricalNetwork: 2 buses, 1 branch, 1 load, 1 source, 1 ground, 1 potential ref>
```

Obviously, an element can only belong to a single network:

```pycon
>>> rlf.ElectricalNetwork.from_element(load)
roseau.load_flow.exceptions.RoseauLoadFlowException: The Bus 'lb' is already assigned to another network. [several_networks]
```

The load flow can be solved:

```pycon
>>> en.solve_load_flow()
(2, 1.8595619621919468e-07)
```

## Disconnecting an element

In order to disconnect an element from the network, the `disconnect` method is available.

```{note}
The `disconnect` method is only available for loads and for voltage sources.
```

```pycon
>>> load.disconnect()
```

Now, the loads no longer belongs to the network `en`. Symmetrically, the network doesn't have this load anymore:

```pycon
>>> load.network
None
>>> en
<ElectricalNetwork: 2 buses, 1 branch, 0 loads, 1 source, 1 ground, 1 potential ref>
```

When accessing a result, a warning is emitted because the results are now outdated:

```pycon
>>> line.res_powers
UserWarning: The results of this element may be outdated. Please re-run a load flow to ensure the validity of results.
(array([10406.073858+0.00000000e+00j, 10406.073858+3.79778686e-12j,
        10406.073858-3.79778686e-12j,     0.      -0.00000000e+00j]) <Unit('volt_ampere')>,
 array([-9.99999996e+03+0.00000000e+00j, -9.99999996e+03-4.11872388e-12j,
        -9.99999996e+03+4.11872388e-12j,  3.48949926e-29+0.00000000e+00j]) <Unit('volt_ampere')>)
```

```{danger}
The load element `load` doesn't belong to a network and a some of its results are not accessible
anymore. Accessing `res_` properties may raise errors.
```

## Connecting an element

Let's extend the network with a new line and add a load at its end. First, we create a new bus and
the new load.

```pycon
>>> new_bus = rlf.Bus(id="new_bus", phases="abcn")
>>> new_load = rlf.PowerLoad(id="new_load", bus=new_bus, phases="an", powers=[6e3]) # W
```

At this point, they don't belong to any network:

```pycon
>>> new_bus.network
None
>>> new_load.network
None
```

Creating a line connecting the `load_bus` (belonging to the network `en`) and our new bus `new_bus` (which doesn't
belong to a network) will propagate the network to the new elements.

```pycon
>>> lp_u_al_240 = rlf.LineParameters.from_catalogue("U_AL_240", nb_phases=4)
>>> new_line = rlf.Line(
...     id="new_line",
...     bus1=load_bus,
...     bus2=new_bus,
...     phases="abcn",
...     ground=ground,
...     parameters=lp_u_al_240,
...     length=0.5,
... )
>>> new_line.network
<ElectricalNetwork: 3 buses, 2 branches, 1 load, 1 source, 1 ground, 1 potential ref>
>>> new_bus.network
<ElectricalNetwork: 3 buses, 2 branches, 1 load, 1 source, 1 ground, 1 potential ref>
>>> new_load.network
<ElectricalNetwork: 3 buses, 2 branches, 1 load, 1 source, 1 ground, 1 potential ref>
>>> en
<ElectricalNetwork: 3 buses, 2 branches, 1 load, 1 source, 1 ground, 1 potential ref>
```

If you look at the network elements, you can see the new bus, line and load are added.

```pycon
>>> en.buses["new_bus"]
Bus(id='new_bus', phases='abcn')
>>> en.loads["new_load"]
PowerLoad(id='new_load', phases='an', bus='new_bus')
>>> en.branches["new_line"]
Line(id='new_line', phases1='abcn', phases2='abcn', bus1='lb', bus2='new_bus')
```

And now if you run the load flow, you can see that the new elements are taken into account.

```pycon
>>> en.solve_load_flow()
(3, 3.5349501104064984e-13)
>>> abs(new_load.res_voltages)
array([216.36821144]) <Unit('volt')>
```

## Modifying an element

Some properties of an element cannot be modified once the element is created. For example the phases
of an element, the buses of a branch / load / source, the winding of a transformer, and the shunt
connection of a line cannot be modified. Some other properties can be modified, like the voltage of
a voltage source.

### Modifying a voltage source

You can change the voltage of the voltage source using the `voltages` attribute:

```pycon
>>> vs.voltages
array([ 230.94010768  +0.j, -115.47005384-200.j, -115.47005384+200.j]) <Unit('volt')>
>>> vs.voltages = vs.voltages * 1.1
>>> vs.voltages
array([ 254.03411844  +0.j, -127.01705922-220.j, -127.01705922+220.j]) <Unit('volt')>
```

### Modifying a load

Similarly, you can change the powers of a "constant power load", the currents of a "constant current
load", and the impedances of a "constant impedance load".

```pycon
>>> new_load.powers
array([6000.+0.j]) <Unit('volt_ampere')>
>>> new_load.powers = [3e3 + 1e3j]
>>> new_load.powers
array([3000.+1000.j]) <Unit('volt_ampere')>
```

### Modifying a branch

You can change a branch parameters by setting a new `parameters` attribute. Note that the new
parameters have to be compatible with the existing branch. This means that the number of phases
must match, and for a transformer, the windings must match.

```pycon
>>> line.z_line
array([[0.2+0.j, 0. +0.j, 0. +0.j, 0. +0.j],
       [0. +0.j, 0.2+0.j, 0. +0.j, 0. +0.j],
       [0. +0.j, 0. +0.j, 0.2+0.j, 0. +0.j],
       [0. +0.j, 0. +0.j, 0. +0.j, 0.2+0.j]]) <Unit('ohm')>
>>> line.parameters = rlf.LineParameters("lp_modified", z_line=(0.5 + 0.1j) * np.eye(4))
>>> line.z_line
array([[1.+0.2j, 0.+0.j , 0.+0.j , 0.+0.j ],
       [0.+0.j , 1.+0.2j, 0.+0.j , 0.+0.j ],
       [0.+0.j , 0.+0.j , 1.+0.2j, 0.+0.j ],
       [0.+0.j , 0.+0.j , 0.+0.j , 1.+0.2j]]) <Unit('ohm')>
```

For a line, you can also change the length:

```pycon
>>> line.length
2.0 <Unit('kilometer')>
>>> line.length = 1.0  # <-- shorten the line by half
>>> line.length
1.0 <Unit('kilometer')>
>>> line.z_line  # <-- the impedance gets divided by 2
array([[0.5+0.1j, 0. +0.j , 0. +0.j , 0. +0.j ],
       [0. +0.j , 0.5+0.1j, 0. +0.j , 0. +0.j ],
       [0. +0.j , 0. +0.j , 0.5+0.1j, 0. +0.j ],
       [0. +0.j , 0. +0.j , 0. +0.j , 0.5+0.1j]]) <Unit('ohm')>
```

Modifying the parameters of a transformer is similar, assign a new `parameters` attribute. For a
transformer, you can also change the tap position by assigning a new `tap` attribute.
