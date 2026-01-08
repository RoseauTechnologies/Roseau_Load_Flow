---
myst:
  html_meta:
    description lang=en: |
      Additional Roseau Load Flow features: graph theory, conversions to symmetrical components, constants, etc.
    keywords lang=en: simulation, distribution grid, symmetrical components, conversion
    # spellchecker:off
    description lang=fr: |
      Fonctionnalités supplémentaires de Roseau Load Flow: affichage du graphe, conversions vers des composantes
      symétriques, constantes, etc.
    keywords lang=fr: simulation, réseau, électrique, composantes symétriques, conversions
    # spellchecker:on
---

# Extra features

`roseau-load-flow` comes with some extra features that can be useful for some users.

## Graph theory

{meth}`ElectricalNetwork.to_graph() <roseau.load_flow.ElectricalNetwork.to_graph>` can be used to get a
{class}`networkx.MultiGraph` object from the electrical network.

The graph contains the geometries of the buses in the nodes data and the geometries and branch types in the edges data.

```{note}
This method requires *networkx* which is not installed by default in pip managed installs. You can
install it with the `"graph"` extra if you are using pip: `pip install "roseau-load-flow[graph]"`.
```

In addition, you can use the property
{meth}`ElectricalNetwork.buses_clusters <roseau.load_flow.ElectricalNetwork.buses_clusters>` to get a list of sets of
IDs of buses in galvanically isolated sections of the network. In other terms, to get groups of buses connected by one
or more lines or a switches, stopping at transformers. For example, for a network with a MV feeder, this property
returns a list containing a set of MV buses IDs and all sets of LV subnetworks buses IDs. If you want to get the cluster
of only one bus, you can use {meth}`Bus.get_connected_buses <roseau.load_flow.models.Bus.get_connected_buses>`

If we take the example network from the [Getting Started page](./Getting_Started.md#creating-a-network):

```pycon
>>> set(source_bus.get_connected_buses())
{'sb', 'lb'}
>>> set(load_bus.get_connected_buses())
{'sb', 'lb'}
>>> en.buses_clusters
[{'sb', 'lb'}]
```

As there are no transformers between the two buses, they all belong to the same cluster.

## Symmetrical components

{mod}`roseau.load_flow.sym` contains helpers to work with symmetrical components. For example, to convert a phasor
voltage to symmetrical components:

```pycon
>>> import numpy as np
>>> import roseau.load_flow as rlf
>>> v = 230 * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
>>> v
array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j])
>>> v_sym = rlf.sym.phasor_to_sym(v)
>>> v_sym
array([[ 8.52651283e-14-1.42108547e-14j],
       [ 2.30000000e+02+4.19109192e-14j],
       [-7.10542736e-14-2.84217094e-14j]])
```

As you can see, for this positive-sequence balanced voltage, only the positive-sequence component is non-zero.
Converting back to phasor, you get the original voltage values back:

```pycon
>>> sym_to_phasor(v_sym)
array([[ 230.-7.21644966e-16j],
       [-115.-1.99185843e+02j],
       [-115.+1.99185843e+02j]])
```

You can also convert pandas Series to symmetrical components. If we take the example network of the
[Getting Started](Getting_Started.md) page:

```pycon
>>> rlf.sym.series_phasor_to_sym(en.res_buses_voltages["voltage"])
bus_id  sequence
lb      zero        8.526513e-14-1.421085e-14j
        pos         2.219282e+02+4.167975e-14j
        neg        -5.684342e-14-2.842171e-14j
sb      zero        9.947598e-14-1.421085e-14j
        pos         2.309401e+02+3.483159e-14j
        neg        -4.263256e-14-2.842171e-14j
Name: voltage, dtype: complex128
```

The `rlf.sym` module also provides useful helpers to create three-phase balanced quantities by only providing the
magnitude of the quantities. For example, to create a three-phase balanced positive sequence voltage:

```pycon
>>> import numpy as np
>>> import roseau.load_flow as rlf
>>> V = 230 * rlf.sym.PositiveSequence
>>> V
array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j])
>>> np.abs(V)
array([230., 230., 230.])
>>> np.angle(V, deg=True)
array([   0., -120.,  120.])
```

Similarly, you can use `rlf.sym.NegativeSequence` and `rlf.sym.ZeroSequence` to create negative-sequence and
zero-sequence quantities respectively. Because these are so common, you can also access them directly from the top-level
module as `rlf.PositiveSequence`, etc.

## Potentials to voltages conversion

{mod}`roseau.load_flow.converters` contains helpers to convert a vector of potentials to a vector of voltages. Example:

```pycon
>>> import numpy as np
>>> import roseau.load_flow as rlf
>>> potentials = 230 * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3), 0])
>>> potentials
array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j,
          0.  +0.j        ])
>>> phases = "abcn"
>>> rlf.converters.calculate_voltages(potentials, phases)
array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j]) <Unit('volt')>
```

Because the phases include the neutral, the voltages calculated are phase-to-neutral voltages. You can also calculate
phase-to-phase voltages by omitting the neutral:

```pycon
>>> rlf.converters.calculate_voltages(potentials[:-1], phases[:-1])
array([ 345.+199.18584287j,    0.-398.37168574j, -345.+199.18584287j]) <Unit('volt')>
```

To get the phases of the voltage, you can use `calculate_voltage_phases`:

```pycon
>>> rlf.converters.calculate_voltage_phases(phases)
['an', 'bn', 'cn']
```

Of course these functions work with arbitrary phases:

```pycon
>>> rlf.converters.calculate_voltages(potentials[:2], phases[:2])
array([345.+199.18584287j]) <Unit('volt')>
>>> rlf.converters.calculate_voltage_phases(phases[:2])
['ab']
>>> rlf.converters.calculate_voltage_phases("abc")
['ab', 'bc', 'ca']
>>> rlf.converters.calculate_voltage_phases("bc")
['bc']
>>> rlf.converters.calculate_voltage_phases("bcn")
['bn', 'cn']
```

## Kron's reduction

Kron's reduction is a method to reduce the size of an admittance or impedance matrix by eliminating nodes that are not
of interest, typically the neutral conductor in power systems. You can use the function
{func}`roseau.load_flow.converters.kron_reduction` to perform Kron's reduction on any square matrix of real or complex
numbers. Example:

```pycon
>>> import numpy as np
... import roseau.load_flow as rlf
>>> matrix_4x4 = np.array(
...     [
...         [4, 1, 2, 0],
...         [1, 3, 0, 1],
...         [2, 0, 3, 1],
...         [0, 1, 1, 2],
...     ],
...     dtype=np.float64,
... )
... rlf.converters.kron_reduction(matrix_4x4)
array([[ 4. ,  1. ,  2. ],
       [ 1. ,  2.5, -0.5],
       [ 2. , -0.5,  2.5]])
```

## Constants

{mod}`roseau.load_flow.constants` contains some common mathematical and physical constants like the resistivity and
permeability of common materials in addition to other useful constants. Please refer to the module documentation for
more details. An enumeration of available materials can be found in the {mod}`roseau.load_flow.types` module.

Some commonly used constants can be accessed directly from the top-level module for convenience. Notable top-level
constants:

- `rlf.SQRT3`: the square root of 3. Useful for converting between phase-to-phase and phase-to-neutral voltages.
- `rlf.ALPHA`: the alpha constant. Rotates a complex number by 120°.
- `rlf.ALPHA2`: the alpha constant squared. Rotates a complex number by 240° (or -120°).

## Voltage unbalance

It is possible to calculate the voltage unbalance due to asymmetric operation. There are many definitions of voltage
unbalance (see {cite:p}`Girigoudar_2019`). In `roseau-load-flow`, you can use the
{meth}`~roseau.load_flow.models.Bus.res_voltage_unbalance` method on a 3-phase bus to get the Voltage Unbalance Factor
(VUF) as per the IEC definition:

```{math}
VUF = \frac{|V_{\mathrm{n}}|}{|V_{\mathrm{p}}|} \times 100 (\%)
```

Where $V_{\mathrm{n}}$ is the negative-sequence voltage and $V_{\mathrm{p}}$ is the positive-sequence voltage.

```{note}
Other definitions of voltage unbalance could be added in the future. If you need a specific
definition, please open an issue on the GitHub repository.
```

## Bibliography

```{bibliography}
---
filter: docname in docnames
---
```
