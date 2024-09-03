---
myst:
  html_meta:
    "description lang=en": |
      Learn how to define the potential reference point of your medium-voltage or low-voltage network for a load flow
      calculation with Roseau Load Flow.
    "description lang=fr": |
      Apprenez à définir le point de référence des potentiels de votre réseau électrique pour un calcul d'écoulement
      de charge avec Roseau Load Flow.
    "keywords lang=fr": simulation, réseau, électrique,  potentiel, référence
    "keywords lang=en": simulation, distribution grid, potentials, reference
---

# Potential Reference

## Definition

As the electrical potentials of the elements of the network are defined as a difference from a
reference point, we need to define this reference point. The potential reference element sets the
potential of the point where it is connected to $0$ Volt. The symbol of a potential reference is:

```{image} /_static/PotentialRef.svg
:alt: A diagram of a potential reference element
:width: 100px
:align: center
```

```{note}
One and only one potential reference per galvanically isolated section of the network can be set.
```

## Usage

It is common to consider the earth as the reference of potentials (i.e $V_{earth} = 0V$). In
_Roseau Load Flow_, the ground element which represents an earth connection does not add any potential
reference equation, i.e. its potential is not fixed at $0V$. If you want to set its potential to $0V$,
you must attach a potential reference element explicitly:

```python
import roseau.load_flow as rlf

ground = rlf.Ground(id="ground")
p_ref = rlf.PotentialRef(id="pref", element=ground)
ground.res_potential  # 0V (after the load flow calculation)
```

With this code snippet, you have defined the following element:

```{image} /_static/PotentialRef_With_Ground.svg
:alt: A diagram of a potential reference connected to a ground element
:width: 100px
:align: center
```

It is also possible to define the reference of potentials on a bus. Defining the potential reference
on a bus with a neutral phase sets its potential to $0V$. For buses without a neutral phase, the
potential reference is defined by setting the sum of the potentials of the phases to $0V$.

```python
# Define on a bus with a neutral phase: Vn = 0V
bus1 = rlf.Bus(id="bus1", phases="abcn")
rlf.PotentialRef(id="pref1", element=bus1).phases  # "n"
bus1.res_potentials[3]  # 0V (after the load flow calculation)

# Define on a bus without a neutral phase: Va + Vb + Vc = 0V
bus2 = rlf.Bus(id="bus2", phases="abc")
rlf.PotentialRef(id="pref2", element=bus2).phases  # "abc"
bus2.res_potentials.sum()  # 0V (after the load flow calculation)
```

It is highly recommended to not specify the phases of the bus when defining the potential reference
and to rely on the default behavior of the potential reference element. If needed though, it is
possible to specify the phases of the bus whose potentials must sum to $0V$ for the potential
reference definition.

```python
# Define the potential reference using the equation: Va + Vb = 0V
bus3 = rlf.Bus(id="bus3", phases="abcn")
rlf.PotentialRef(id="pref3", element=bus3, phases="ab").phases  # "ab"
bus3.res_potentials[:2].sum()  # 0V (after the load flow calculation)
```

For more information on the potential references, refer to their [dedicated page](advanced-pref)
in the advanced section of the documentation.

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.PotentialRef
   :members:
   :show-inheritance:
   :no-index:
```
