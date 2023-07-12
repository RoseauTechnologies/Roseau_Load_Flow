# Potential Reference

As the electrical potentials of the elements of the network are defined as a difference from a reference point, we
need to define this reference point. The potential reference element set the potential of the element it is connected
to $0$ Volt.

A representation of this element could be:

```{image}  /_static/PotentialRef.svg
:alt: Potential reference diagram
:width: 100px
:align: center
```

Usually, the potential reference is attached to the ground to set the potential of the ground to $0$. In
*Roseau Load Flow*, the ground element doesn't add any potential reference equation. If you want to do so, please
use the following code:

```python
from roseau.load_flow.models import Ground, PotentialRef

g = Ground(id="ground")
p_ref = PotentialRef(id="pref", element=g)
```

With this code, you have defined the following element:

```{image}  /_static/PotentialRef_With_Ground.svg
:alt: Potential reference with a ground diagram
:width: 100px
:align: center
```


Yet, it is completely possible to set the reference of the potentials to a phase of any bus. As an example, you can
define the potential of the phase "a" of a bus to 0V with the following code.

```python
from roseau.load_flow.models import Bus, PotentialRef

bus = Bus(id="bus", phases="abcn")
p_ref = PotentialRef(id="pref", element=bus, phase="a")
```

```{note}
Only one potential reference per galvanically isolated section of the network can be set.
```
