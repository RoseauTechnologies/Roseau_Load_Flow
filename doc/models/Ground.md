# Ground

The ground element can be used to connect several elements. It is notably necessary to connect the shunt admittances
of a line. Its representation is:

```{image}  /_static/Ground.svg
:alt: Ground diagram
:width: 100px
:align: center
```

This element add the equation $I_{\mathrm{g}} = 0$.

```{warning}
In electrical engineering, it is common to also add the equation $V_{\mathrm{g}}=0$ when defining a ground element.
If you want to do so, you must add a `PotentialRef` element as defined in <project:./PotentialRef.md>.
```

In *Roseau Load Flow*, several grounds can be defined leading to grounds elements with a non-zero potential. Here is
an example:

```python
import numpy as np

from roseau.load_flow.models import Bus, Ground, Line, LineParameters, PotentialRef
from roseau.load_flow.units import Q_

# Define two grounds elements
g1 = Ground(id="g1")
g2 = Ground(id="g2")

# Define three buses
bus1 = Bus(id="bus1", phases="abcn")
bus2 = Bus(id="bus2", phases="abcn")
bus3 = Bus(id="bus3", phases="abcn")

# Define a line between bus1 and bus2 (using g1 in the shunt line)
parameters = LineParameters(id="parameters", z_line=np.eye(4), y_shunt=np.eye(4))
line1 = Line(
    id="line1", bus1=bus1, bus2=bus2, parameters=parameters, length=Q_(1, "km"), ground=g1
)

# Define a line between bus2 and bus3 (using g2 in the shunt line)
line2 = Line(
    id="line2", bus1=bus2, bus2=bus3, parameters=parameters, length=Q_(1, "km"), ground=g2
)

# Set the potential of the ground element g1 to 0V
pref = PotentialRef(id="pref", element=g1)
```

After solving this load flow (a voltage source must be added and an electrical network must be built), the following
assertions will be verified:
* The potential of the ground `g1` will be 0V as defined by the potential reference `pref`.
* There is no reason for the potential of `g2` to be zero too. It can be accessed with `g2.res_potential`
* The sum of currents flowing through the shunt admittance of the first line will be zero as they are all connected
  to the ground `g1`.
* The sum of currents flowing through the shunt admittance of the second line will be zero as they are all connected
  to the ground `g2`.
