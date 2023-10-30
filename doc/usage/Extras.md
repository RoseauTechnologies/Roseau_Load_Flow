# Extras

`roseau-load-flow` comes with some extra features that can be useful for some users.

## Graph theory

{meth}`ElectricalNetwork.to_graph() <roseau.load_flow.ElectricalNetwork.to_graph>` can be used to
get a {class}`networkx.Graph` object from the electrical network.

The graph contains the geometries of the buses in the nodes data and the geometries and branch
types in the edges data.

```{note}
This method requires *networkx* which is not installed by default in pip managed installs. You can
install it with the `"graph"` extra if you are using pip: `pip install "roseau-load-flow[graph]"`.
```

In addition, you can use the property
{meth}`ElectricalNetwork.buses_clusters <roseau.load_flow.ElectricalNetwork.buses_clusters>` to
get a list of sets of IDs of buses connected by a line or a switch. For example, with a network
with a MV feeder, this property returns a list containing a set of MV buses IDs and all sets of
LV subnetworks buses IDs. If you want to get the cluster of only one bus, you can use
{meth}`Bus.find_neighbors <roseau.load_flow.models.Bus.find_neighbors>`

If we take the example network from the [Getting Started page](gs-creating-network):

```pycon
>>> set(source_bus.find_neighbors())
{'sb', 'lb'}
>>> set(load_bus.find_neighbors())
{'sb', 'lb'}
>>> en.buses_clusters
[{'sb', 'lb'}]
```

As there are no transformers between the two buses, they all belong to the same cluster.

## Conversion to symmetrical components

{mod}`roseau.load_flow.converters` contains helpers to convert between phasor and symmetrical
components. For example, to convert a phasor voltage to symmetrical components:

```pycon
>>> import numpy as np
>>> from roseau.load_flow.converters import phasor_to_sym, sym_to_phasor
>>> v = 230 * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
>>> v
array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j])
>>> v_sym = phasor_to_sym(v)
>>> v_sym
array([[ 8.52651283e-14-1.42108547e-14j],
       [ 2.30000000e+02+4.19109192e-14j],
       [-7.10542736e-14-2.84217094e-14j]])
```

As you can see, for this positive-sequence balanced voltage, only the positive-sequence component
is non-zero. Converting back to phasor, you get the original voltage values back:

```pycon
>>> sym_to_phasor(v_sym)
array([[ 230.-7.21644966e-16j],
       [-115.-1.99185843e+02j],
       [-115.+1.99185843e+02j]])
```

You can also convert pandas Series to symmetrical components. If we take the example network of the
[Getting Started](Getting_Started.md) page:

```pycon
>>> from roseau.load_flow.converters import series_phasor_to_sym
>>> series_phasor_to_sym(en.res_buses_voltages["voltage"])
bus_id  sequence
lb      zero        8.526513e-14-1.421085e-14j
        pos         2.219282e+02+4.167975e-14j
        neg        -5.684342e-14-2.842171e-14j
sb      zero        9.947598e-14-1.421085e-14j
        pos         2.309401e+02+3.483159e-14j
        neg        -4.263256e-14-2.842171e-14j
Name: voltage, dtype: complex128
```

## Potentials to voltages conversion

{mod}`roseau.load_flow.converters` also contains helpers to convert a vector of potentials to a
vector of voltages. Example:

```pycon
>>> import numpy as np
>>> from roseau.load_flow.converters import calculate_voltages, calculate_voltage_phases
>>> potentials = 230 * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3), 0])
>>> potentials
array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j,
          0.  +0.j        ])
>>> phases = "abcn"
>>> calculate_voltages(potentials, phases)
array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j])
```

Because the phases include the neutral, the voltages calculated are phase-to-neutral voltages.
You can also calculate phase-to-phase voltages by omitting the neutral:

```pycon
>>> calculate_voltages(potentials[:-1], phases[:-1])
array([ 345.+199.18584287j,    0.-398.37168574j, -345.+199.18584287j])
```

To get the phases of the voltage, you can use `calculate_voltage_phases`:

```pycon
>>> calculate_voltage_phases(phases)
['an', 'bn', 'cn']
```

Of course these functions work with arbitrary phases:

```pycon
>>> calculate_voltages(potentials[:2], phases[:2])
array([345.+199.18584287j])
>>> calculate_voltage_phases(phases[:2])
['ab']
>>> calculate_voltage_phases("abc")
['ab', 'bc', 'ca']
>>> calculate_voltage_phases("bc")
['bc']
>>> calculate_voltage_phases("bcn")
['bn', 'cn']
```

## Constants

{mod}`roseau.load_flow.utils.constants` contains some common constants like the resistivity
and permeability of common conductor types in addition to other useful constants. Please refer to
the module documentation for more details.

An enumeration of available conductor types can be found in the {mod}`roseau.load_flow.utils.types`
module.
