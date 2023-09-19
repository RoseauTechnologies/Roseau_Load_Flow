# (Dis)Connecting elements

## Creating a network

Let's take the electrical network of the [Getting started page](usage-getting-started).

```pycon
>>> import numpy as np
... from roseau.load_flow import *

>>> source_bus = Bus(id="sb", phases="abcn")
... load_bus = Bus(id="lb", phases="abcn")

>>> ground = Ground(id="gnd")
... pref = PotentialRef(id="pref", element=ground)
... ground.connect(source_bus, phase="n")

>>> un = 400 / np.sqrt(3)
... source_voltages = [un, un * np.exp(-2j * np.pi / 3), un * np.exp(2j * np.pi / 3)]
... vs = VoltageSource(id="vs", bus=source_bus, voltages=source_voltages)

>>> load = PowerLoad(id="load", bus=load_bus, powers=[10e3 + 0j, 10e3, 10e3])  # VA

>>> lp = LineParameters("lp", z_line=(0.1 + 0.0j) * np.eye(4, dtype=complex))
... line = Line(
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
>>> en = ElectricalNetwork.from_element(source_bus)
>>> load.network
<ElectricalNetwork: 2 buses, 1 branch, 1 load, 1 source, 1 ground, 1 potential ref>
```

Obviously, an element can only belong to a single network:

```pycon
>>> ElectricalNetwork.from_element(load)
roseau.load_flow.exceptions.RoseauLoadFlowException: The Bus 'lb' is already assigned to another network. [several_networks]
```

The load flow can be solved:

```pycon
>>> auth = ("username", "password")
>>> en.solve_load_flow(auth=auth)
2
```

## Disconnecting an element

In order to disconnect an element from the network, the `disconnect` method is available.

```{note}
The `disconnect` method is only available for loads and for voltage sources.
```

```pycon
>>> load.disconnect()
```

Now, the load does not belong anymore to the network `en`. Symmetrically, the network doesn't have this load anymore:

```pycon
>>> load.network
None
>>> en
<ElectricalNetwork: 2 buses, 1 branch, 0 loads, 1 source, 1 ground, 1 potential ref>
```

When accessing to a result, a warning is emitted because the results are now outdated:

```pycon
>>> line.res_powers
UserWarning: The results of this element may be outdated. Please re-run a load flow to ensure the validity of results.
(array([10406.073858+0.00000000e+00j, 10406.073858+3.79778686e-12j,
        10406.073858-3.79778686e-12j,     0.      -0.00000000e+00j]) <Unit('volt_ampere')>,
 array([-9.99999996e+03+0.00000000e+00j, -9.99999996e+03-4.11872388e-12j,
        -9.99999996e+03+4.11872388e-12j,  3.48949926e-29+0.00000000e+00j]) <Unit('volt_ampere')>)
```

```{danger}
The load element `load` doesn't belong to a network and a part of its results is not accessible any more. `res_`
methods may raise errors.
```

## Connecting an element

Let's create a new line and a new load at the end of this line.

The new bus and the new load are created first.

```pycon
>>> new_bus = Bus(id="new_bus", phases="abcn")
>>> new_load = PowerLoad(id="new_load", bus=new_bus, phases="an", powers=[6e3]) # W
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
>>> lp_u_al_240 = LineParameters.from_name_lv("U_AL_240")
>>> new_line = Line(
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
>>> en.solve_load_flow(auth=auth)
3
>>> abs(new_load.res_voltages)
array([216.54956226]) <Unit('volt')>
```