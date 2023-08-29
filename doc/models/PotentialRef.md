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

It is common to consider the earth as the reference of potentials $0V$. In _Roseau Load Flow_, the
ground element which represents an earth connection does not add any potential reference equation,
i.e. its potential is not fixed at $0V$. If you want to set its potential to $0V$, you must attach
a potential reference element explicitly:

```python
from roseau.load_flow.models import Ground, PotentialRef

g = Ground(id="ground")
p_ref = PotentialRef(id="pref", element=g)
```

With this code snippet, you have defined the following element:

```{image} /_static/PotentialRef_With_Ground.svg
:alt: A diagram of a potential reference connected to a ground element
:width: 100px
:align: center
```

It is also possible to set the reference of potentials to any phase of any bus in the network.
For example, to fix the potential of phase "a" of some bus to $0V$:

```python
from roseau.load_flow.models import Bus, PotentialRef

bus = Bus(id="bus", phases="abcn")
p_ref = PotentialRef(id="pref", element=bus, phase="a")
```
