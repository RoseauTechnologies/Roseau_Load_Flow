(models-flexible_load-feasible_domains)=

# Feasible domains

Depending on the mix of controls and projection used through the class `FlexibleParameter`, the feasible domains in
the $(P, Q)$ space changes.

```{note}
On this page, all the images are drawn for a producer so $P^{\text{th.}}\leqslant0$.
```

## Everything constant

If there is no control at all, i.e. the `flexible_params` argument is **not** given to the `PowerLoad` constructor or
`constant` control used for both active and reactive powers, the consumed (or produced) power will be the one
provided by the user, noted $\underline{S^{\mathrm{th.}}}=P^{\mathrm{th.}}+jQ^{\mathrm{th.}}$. The feasible domain
is reduced to a single point as depicted in the figure below.

```{image} /_static/Load/FlexibleLoad/Domain_Pconst_Qconst.svg
:width: 300
:align: center
```

Here is a small example of usage of the constant control for active and reactive powers.

```python
import numpy as np

from roseau.load_flow import (
    PowerLoad,
    Bus,
    Q_,
    FlexibleParameter,
    Control,
    Projection,
    VoltageSource,
    ElectricalNetwork,
    PotentialRef,
)

# A voltage source
bus = Bus(id="bus", phases="abcn")
un = 400 / np.sqrt(3)
voltages = Q_(un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3]), "V")
vs = VoltageSource(id="source", bus=bus, voltages=voltages)

# A potential ref
pref = PotentialRef("pref", element=bus, phase="n")

# No flexible params
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(np.array([1000, 1000, 1000]), "VA"),
)

# Build a network and solve a load flow
en = ElectricalNetwork.from_element(bus)
auth = ("username", "password")
en.solve_load_flow(auth=auth)

# The voltage source provided 1 kVA per phase for the load
vs.res_powers
# array(
#     [-1000.-0.00000000e+00j, -1000.+1.93045819e-14j, -1000.-1.93045819e-14j, 0.+0.00000000e+00j]
# ) <Unit('volt_ampere')>

# Disconnect the load
load.disconnect()

# Constant flexible params
# The projection is useless as there are only constant controls
# The s_max is useless as there are only constant controls
fp = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.constant(),
    projection=Projection(type="euclidean"),
    s_max=Q_(5, "kVA"),
)

# For each phase, the provided `powers` are lower than 5 kVA.
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(np.array([1000, 1000, 1000]), "VA"),
    flexible_params=[fp, fp, fp],
)
en.solve_load_flow(auth=auth)

# Again the voltage source provided 1 kVA per phase
vs.res_powers
# array(
#   [-1000.-0.00000000e+00j, -1000.+1.93045819e-14j, -1000.-1.93045819e-14j, 0.+0.00000000e+00j]
# ) <Unit('volt_ampere')>

# Disconnect the load
load.disconnect()

# For some phases, the provided `powers` are greater than 5 kVA. The projection is still useless.
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(np.array([6, 4.5, 6]), "kVA"),  # Above 5 kVA -> also OK!
    flexible_params=[fp, fp, fp],
)
en.solve_load_flow(auth=auth)

# The load provides exactly the power consumed by the load even if it is greater than s_max
vs.res_powers
# array(
#     [-6000.-0.00000000e+00j, -4500.-3.01980663e-14j, -6000.-2.18385501e-13j, 0.+0.00000000e+00j]
# ) <Unit('volt_ampere')>
```

## Active power control only

When the reactive power is constant, only the active power may be modulated by the local voltage. Thus, the active
power may vary between 0 and $P^{\mathrm{th.}}$ (if the load is a consumer i.e. $P^{\mathrm{th.}}\geqslant 0$) or
between $P^{\mathrm{th.}}$ and 0 (if the load is a producer i.e. $P^{\mathrm{th.}}\leqslant0$).

When a control is activated for a load, the theoretical power can not be outside the disc of radius $S^{\max}$. Here
is a small example of such error:

```python
import numpy as np

from roseau.load_flow import PowerLoad, Bus, Q_, FlexibleParameter, Control, Projection

bus = Bus(id="bus", phases="an")

# Flexible load
fp = FlexibleParameter(
    control_p=Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V")),
    control_q=Control.constant(),
    projection=Projection(type="keep_p"),
    s_max=Q_(5, "kVA"),
)

# Raises an error!
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(
        np.array([-5 + 5j], dtype=complex), "kVA"
    ),  # Point outside the circle of radius s_max
    flexible_params=[fp],
)
# RoseauLoadFlowException: The power is greater than the parameter s_max
# for flexible load "load" [bad_s_value]
```

Thus, the given $\underline{S^{\text{th.}}}=P^{\text{th.}}+jQ^{\text{th.}}$ lies in the disk of radius $S^{\max}$.
The resulting flexible power is the minimum absolute value between, on the one hand, the active power control function
(which takes values between 0 and 1) multiplied by $S^{\max}$ and, on the other hand, $P^{\mathrm{th.}}$.
As a consequence, the resulting power lies in the segment between the points $(0, Q^{\text{th.}})$ and
$(P^{\text{th.}}, Q^{\text{th.}})$.

```{important}
The projection is useless when there is only an active power control as no point can lie outside the disc of radius
$S^{\max}$.
```

This domain of feasible points is depicted in the figure below:

```{image} /_static/Load/FlexibleLoad/Domain_PmaxU_Qconst.svg
:width: 300
:align: center
```

In the `FlexibleParameter` class, there is a method `compute_powers` which allows to compute the resulting voltages
powers

```python
import numpy as np

from roseau.load_flow import Q_, FlexibleParameter, Control, Projection

# A flexible parameter
fp = FlexibleParameter(
    control_p=Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V")),
    control_q=Control.constant(),
    projection=Projection(type="keep_p"),  # <----- No consequence
    s_max=Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.array(range(205, 256, 1), dtype=float)

# and when the theoretical power is the following
power = Q_(-2.5 + 1j, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
auth = ("username", "password")
res_flexible_powers = fp.compute_powers(auth=auth, voltages=voltages, power=power)
```

Plotting the control curve $P(U)$ using the variables `voltages` and `res_flexible_powers` of the script above leads to
the following plot:

```{image} /_static/Load/FlexibleLoad/PmaxU_Qconst_Control_Curve_Example.svg
:width: 700
:align: center
```

The non-smooth theoretical control function is the control function applied to $S^{\max}$. The effective power has been
plotted using the powers really produced by the load. Below 240 V, there is no variation in the produced power which is
expected. Between 240 V and approximately 245 V, there is no reduction of the produced power because the curtailment
factor (computed from the voltage) times $S^{\max}$ is lower than $P^{\mathrm{th.}}$. As a consequence,
$P^{\mathrm{th.}}$ is produced. Starting at approximately 245 V, the comparison changes and the really produced
power starts to decrease. It reaches 0 W above 250 V.

The same plot can be obtained using the following command:

```python
from matplotlib import pyplot as plt

ax, res_flexible_powers = fp.plot_control_p(
    auth=auth, voltages=voltages, power=power, res_flexible_powers=res_flexible_powers
)
plt.show()
```

In the above example, `res_flexible_powers` is provided as input. It could have been forgotten, and the flexible
powers would have been computed by requesting the server. The computed values are retrieved with the axis on which
the plot was drawn.

`````{tip}
To install matplotlib along side with roseau-load-flow, you can type

````{tab}  Linux
```console
$ python -m pip install roseau-load-flow[plot]
```
````

````{tab} Windows
Matplotlib is always installed when `conda` is used.
````

`````

If now, we plot the trajectory of the control in the $(P, Q)$ space, the following result is obtained:

```{image} /_static/Load/FlexibleLoad/PmaxU_Qconst_Trajectory_Example.svg
:width: 700
:align: center
```

All the points have been plotted (1 per volt between 205 V and 255 V). A lot of points are overlapping.

The same plot could have been obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    voltages_labels_mask=np.isin(voltages, [240, 250]),
    ax=ax,
)
plt.show()
```

## Reactive power control only

When the active power is constant, only the reactive power may be modulated by the local voltage. Thus, the reactive
power may vary between $-S^{\max}$ and $+S^{\max}$. In this segment, there are points outside the disc of radius
$S^{\max}$ (when $P^{\mathrm{th.}}\neq 0$). Those points are projected on the circle of radius $S^{\max}$ and
depending on the projection, the feasible domains change.

### Constant $P$

If the _constant $P$_ (`keep_p`) projection is chosen, the feasible domain is limited to a segment as defined below.

```{image} /_static/Load/FlexibleLoad/Domain_Pconst_QU_P.svg
:width: 300
:align: center
```

Here is an example of a reactive power control (without active power control) flexible parameter creation:

```python
import numpy as np

from roseau.load_flow import Q_, FlexibleParameter, Control, Projection

# Flexible parameter
fp = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
    ),
    projection=Projection(type="keep_p"),  # <---- Keep P
    s_max=Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.array(range(205, 256, 1), dtype=float)

# and when the theoretical power is the following
power = Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
auth = ("username", "password")
res_flexible_powers = fp.compute_powers(auth=auth, voltages=voltages, power=power)
```

At the end of the script, the variable `res_flexible_powers` contains the powers that has been really produced by
the flexible load for the voltages stored in the variable named `voltages`.

Plotting the control curve $Q(U)$ lead to the following plot:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_P_Control_Curve_Example.svg
:width: 700
:align: center
```

One can remark that, even with a voltage lower than $U^{\min}$ or greater than $U^{\max}$ the available reactive
power (by default taken in the interval $[-S^{\max}, S^{\max}]$) was never totally used because of the choice of the
projection.

The same plot can be obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_control_q(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    ax=ax,
)
plt.show()
```

If now, we plot the trajectory of the control in the $(P, Q)$ space, the following result is obtained:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_P_Trajectory_Example.svg
:width: 700
:align: center
```

As in the previous plot, there is one point per volt from 205 V to 255 V. Several remarks on this plot:

1. All the points are aligned on the straight line $P=-2.5$ kVA because it was the power provided to the flexible
   load and because the projection used was at _Constant P_.
2. One can remark that several points are overlapping for low and high voltages. For these extremities, the
   theoretical control curves would have forced the point of operation to be outside the disc of radius $S^{\max}$ (5
   kVA in the example).

The same plot could have been obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

### Constant $Q$

If the _constant $Q$_ (`keep_q`) projection is chosen, the feasible domain is limited to a segment with two arcs as
defined below.

```{image} /_static/Load/FlexibleLoad/Domain_Pconst_QU_Q.svg
:width: 300
:align: center
```

```{warning}
Note that using this projection with a constant active power may result in a final active power lower than the one
provided (even 0 W in the worst cases)!
```

Here is an example the creattion of such control with a constant $Q$ projection:

```python
import numpy as np

from roseau.load_flow import Q_, FlexibleParameter, Control, Projection

# Flexible parameter
fp = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
    ),
    projection=Projection(type="keep_q"),  # <---- Keep Q
    s_max=Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.array(range(205, 256, 1), dtype=float)

# and when the theoretical power is the following
power = Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
auth = ("username", "password")
res_flexible_powers = fp.compute_powers(auth=auth, voltages=voltages, power=power)
```

At the end of the script, the variable `res_flexible_powers` contains the powers that has been really produced by
the flexible load for the voltages stored in the variable named `voltages`.

Plotting the control curve $Q(U)$ leads to the following plot:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Q_Control_Curve_Example.svg
:width: 700
:align: center
```

Here, the complete possible range of reactive power was used. Nevertheless, it was achieved with some active power
reduction because of the projection.

The same plot can be obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_control_q(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    ax=ax,
)
plt.show()
```

If now, we plot the trajectory of the control in the $(P, Q)$ space, the following result is obtained:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Q_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot could have been obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

One can remark that when the voltages were too low or too high, the projection at constant $Q$ forces us to reduce
the produced active power to ensure a feasible point i.e. a point which is in the disc of radius $S^{\max}$. As
before, there is one point per volt. Several points of operation are overlapping near the coordinates (0,5 kVA) and
(0, -5 kVA).

### Euclidean projection

If the _Euclidean_ (`euclidean`) projection is chosen, the feasible domain is limited to a segment with two
small arcs as defined below.

```{image} /_static/Load/FlexibleLoad/Domain_Pconst_QU_Eucl.svg
:width: 300
:align: center
```

```{warning}
Note that using this projection with a constant active power may result in a final active power lower than the one
provided!
```

Here is an example of this usage with a single phase network limited to a single bus:

```python
import numpy as np

from roseau.load_flow import Q_, FlexibleParameter, Control, Projection

# Flexible parameter
fp = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
    ),
    projection=Projection(type="euclidean"),  # <---- Euclidean
    s_max=Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.array(range(205, 256, 1), dtype=float)

# and when the theoretical power is the following
power = Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
auth = ("username", "password")
res_flexible_powers = fp.compute_powers(auth=auth, voltages=voltages, power=power)
```

At the end of the script, the variable `res_flexible_powers` contains the powers that has been really produced by
the flexible load for the voltages stored in the variable named `voltages`.

Plotting the control curve $Q(U)$ lead to the following plot:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Eucl_Control_Curve_Example.svg
:width: 700
:align: center
```

Here, again the complete reactive power range is not fully used.

The same plot can be obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_control_q(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    ax=ax,
)
plt.show()
```

If now, we plot the trajectory of the control in the $(P, Q)$ space, the following result is obtained:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Eucl_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot could have been obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

One can remark that when the voltages were too low or too high, the Euclidean projection forces us to
reduce the produced active power and the (produced and consumed) reactive power to ensure a feasible point i.e. a point
which is in the disc of radius $S^{\max}$. As before, there is one point per volt thus one can remark that several
points of operation are overlapping.

## Both active and reactive powers control

When both active and reactive powers are activated, the feasible domains is the following:

```{image} /_static/Load/FlexibleLoad/Domain_PmaxU_QU.svg
:width: 300
:align: center
```

Every point whose abscissa is between $P^{\mathrm{th.}}$ and 0, whose ordinate is between $-S^{\max}$ and $+S^{\max}$
and which lies in the disc of radius $S^{\max}$ is reachable. Let's look at two examples: in the first one, the
controls are activated sequentially (reactive power first and then active power) and, in the other example, there
are used together.

### Sequentially activated controls

Let's play with the voltage thresholds of the control in order to fully activate a first control and then starts to
activate the second.

#### Reactive power control first

In this section, the reactive power control is activated at 230 V and fully used above 240 V. Then, at 245 V, the
active control power starts and is fully activated at 250 V.

In the following script such control is used on a network with a single-phase load connected to a single bus:

```python
import numpy as np

from roseau.load_flow import Q_, FlexibleParameter, Control, Projection

# Flexible parameter
fp = FlexibleParameter(
    control_p=Control.p_max_u_production(u_up=Q_(245, "V"), u_max=Q_(250, "V")),  # <----
    control_q=Control.q_u(
        u_min=Q_(210, "V"),
        u_down=Q_(220, "V"),
        u_up=Q_(230, "V"),  # <----
        u_max=Q_(240, "V"),  # <----
    ),
    projection=Projection(type="euclidean"),  # <---- Euclidean
    s_max=Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.array(range(205, 256, 1), dtype=float)

# and when the theoretical power is the following
power = Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
auth = ("username", "password")
res_flexible_powers = fp.compute_powers(auth=auth, voltages=voltages, power=power)
```

If we plot the trajectory of the control in the $(P, Q)$ space, the following result is obtained:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Sequential_1_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot could have been obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

When the voltage is low, there is only a reactive power control which is activated. Thus, everything works as
depicted in the previous dedicated section and the choice of the projection may change the operation points for the
lowest voltages.

When the voltage is high, there are two phases:

1. Between 230 V and 240 V, only the reactive power decreases to reach the symmetrical point (with respect to the
   x-axis) of the 205 V operation point.
2. Between 245 V and 250 V, the active power control reduces the active power to reach 0 W above 250 V.

#### Active power control first

In this section, the active power control is activated at 240 V and fully used above 245 V. Then, at 245 V, the
reactive control power starts and is fully activated at 250 V.

In the following script such control is used on a network with a single-phase load connected to a single bus:

```python
import numpy as np

from roseau.load_flow import Q_, FlexibleParameter, Control, Projection


# Flexible parameter
fp = FlexibleParameter(
    control_p=Control.p_max_u_production(u_up=Q_(230, "V"), u_max=Q_(240, "V")),  # <----
    control_q=Control.q_u(
        u_min=Q_(210, "V"),
        u_down=Q_(220, "V"),
        u_up=Q_(245, "V"),  # <----
        u_max=Q_(250, "V"),  # <----
    ),
    projection=Projection(type="euclidean"),  # <---- Euclidean
    s_max=Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.array(range(205, 256, 1), dtype=float)

# and when the theoretical power is the following
power = Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
auth = ("username", "password")
res_flexible_powers = fp.compute_powers(auth=auth, voltages=voltages, power=power)
```

If we plot the trajectory of the control in the $(P, Q)$ space, the following result is obtained:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Sequential_2_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot could have been obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

When the voltage is low, there is only a reactive power control which is activated. Thus, everything works as
depicted in the previous dedicated section and the choice of the projection may change the operation points for the
lowest voltages.

When the voltage is high, there are two phases:

1. Between 230 V and 240 V, only the active power decreases to reach a production of nearly 0 W.
2. Between 245 V and 250 V, the reactive power control increased the consumed the reactive power at 250 V.

### Simultaneously activated controls

In this second subsection, the active and the reactive powers controls are activated at 240 V and reach their full
effect at 250 V.

Here is a small single phase network limited to a single bus to model the behaviour of the flexible load:

```python
import numpy as np

from roseau.load_flow import Q_, FlexibleParameter, Control, Projection

# Flexible parameter
fp = FlexibleParameter(
    control_p=Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V")),  # <----
    control_q=Control.q_u(
        u_min=Q_(210, "V"),
        u_down=Q_(220, "V"),
        u_up=Q_(240, "V"),  # <----
        u_max=Q_(250, "V"),  # <----
    ),
    projection=Projection(type="euclidean"),  # <---- Euclidean
    s_max=Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.array(range(205, 256, 1), dtype=float)

# and when the theoretical power is the following
power = Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
auth = ("username", "password")
res_flexible_powers = fp.compute_powers(auth=auth, voltages=voltages, power=power)
```

If we plot the trajectory of the control in the $(P, Q)$ space, the following result is obtained:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Simultaneous_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot could have been obtained using the following command:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=power,
    res_flexible_powers=res_flexible_powers,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

When the voltage is low, there is only a reactive power control which is activated. Thus, everything works as
depicted in the previous dedicated section and the choice of the projection may change the operation points for the
lowest voltages.

When the voltage is high, there are two phases:

1. Between 240 V and 245 V, the active power control doesn't modify the value of the produced active power while the
   reactive power control starts to increase the consumed reactive power.
2. Between 245 V and 250 V, the active power control starts to have effects on the produced active power. The
   consumed reactive power continues to increase.
3. Above 250 V, no active power is produced.

If now, the theoretical power is changed to 4 kVA of production.

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    auth=auth,
    voltages=voltages,
    power=Q_(-4, "kVA"),  # <------ New power
    # res_flexible_powers=res_flexible_powers, # Must be computed again!
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

The following result is obtained:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Simultaneous_2_Trajectory_Example.svg
:width: 700
:align: center
```
