---
myst:
  html_meta:
    "description lang=en": |
      Explanation of the concept of the control domain of a flexible load as a function of the different types of P
      and Q controls applied.
    "description lang=fr": |
      Explications sur la notion de domaine de contrôle d'une charge flexible en fonction des différents types de
      contrôles P et Q appliqués.
    "keywords lang=fr": simulation, réseau, électrique, charge flexible, domaine de faisabilité, P, Q
    "keywords lang=en": simulation, distribution grid, flexible load, projection, P, Q
---

(models-flexible_load-feasible_domains)=

# Feasible domains

Depending on the mix of controls and projection used through the class `FlexibleParameter`, the feasible domain in
the $(P, Q)$ space changes.

```{note}
On this page, all the images are drawn for a producer so $P^{\text{th.}}\leqslant0$.
```

## Everything constant

If there is no control at all, i.e. the `flexible_params` argument is **not** given to the `PowerLoad` constructor or
`constant` control used for both active and reactive powers, the consumed (or produced) power will be the one
provided to the load, noted $\underline{S^{\mathrm{th.}}}=P^{\mathrm{th.}}+jQ^{\mathrm{th.}}$. The feasible domain
is reduced to a single point as depicted in the figure below.

```{image} /_static/Load/FlexibleLoad/Domain_Pconst_Qconst.svg
:width: 300
:align: center
```

Here is a small example of usage of the constant control for active and reactive powers.

```python
import numpy as np
import roseau.load_flow as rlf

# A voltage source
bus = rlf.Bus(id="bus", phases="abcn")
un = 400 / rlf.SQRT3
vs = rlf.VoltageSource(id="source", bus=bus, voltages=rlf.Q_(un, "V"))

# A potential ref
pref = rlf.PotentialRef("pref", element=bus)

# No flexible params: 1 kVA per phase
load = rlf.PowerLoad(id="load", bus=bus, powers=rlf.Q_(1000, "VA"))

# Build a network and solve a load flow
en = rlf.ElectricalNetwork.from_element(bus)
en.solve_load_flow()

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
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.constant(),
    projection=rlf.Projection(type="euclidean"),
    s_max=rlf.Q_(5, "kVA"),
)

# For each phase, the provided `powers` are lower than 5 kVA.
load = rlf.PowerLoad(
    id="load",
    bus=bus,
    powers=rlf.Q_(np.array([1000, 1000, 1000]), "VA"),
    flexible_params=[fp, fp, fp],
)
en.solve_load_flow()

# Again the voltage source provided 1 kVA per phase
vs.res_powers
# array(
#   [-1000.-0.00000000e+00j, -1000.+1.93045819e-14j, -1000.-1.93045819e-14j, 0.+0.00000000e+00j]
# ) <Unit('volt_ampere')>

# Disconnect the load
load.disconnect()

# For some phases, the provided `powers` are greater than 5 kVA. The projection is still useless.
load = rlf.PowerLoad(
    id="load",
    bus=bus,
    powers=rlf.Q_(np.array([6, 4.5, 6]), "kVA"),  # Above 5 kVA -> also OK!
    flexible_params=[fp, fp, fp],
)
en.solve_load_flow()

# The load provides exactly the power consumed by the load even if it is greater than s_max
vs.res_powers
# array(
#     [-6000.-0.00000000e+00j, -4500.-3.01980663e-14j, -6000.-2.18385501e-13j, 0.+0.00000000e+00j]
# ) <Unit('volt_ampere')>
```

## Active power control only

When the reactive power is constant, only the active power changes as a function of the local
voltage. Thus, the active power may vary between 0 and $P^{\mathrm{th.}}$.

When a control is activated, the load's "theoretical" power **must** always be inside the disc of
radius $S^{\max}$, otherwise an error is thrown:

```python
import numpy as np
import roseau.load_flow as rlf

bus = rlf.Bus(id="bus", phases="an")

# Flexible load
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.p_max_u_production(
        u_up=rlf.Q_(240, "V"), u_max=rlf.Q_(250, "V")
    ),
    control_q=rlf.Control.constant(),
    projection=rlf.Projection(type="keep_p"),
    s_max=rlf.Q_(5, "kVA"),
)

# Raises an error!
load = rlf.PowerLoad(
    id="load",
    bus=bus,
    powers=rlf.Q_(np.array([-5 + 5j], dtype=complex), "kVA"),  # > s_max
    flexible_params=[fp],
)
# RoseauLoadFlowException: The power is greater than the parameter s_max
# for flexible load "load" [bad_s_value]
```

The active power control algorithm produces a factor between 0 and 1 that gets multiplied by $S^{\max}$.
The resulting flexible power is the minimum absolute value between this result and $P^{\mathrm{th.}}$.
As a consequence, the resulting power lies on the horizontal segment between the points
$(0, Q^{\text{th.}})$ and $(P^{\text{th.}}, Q^{\text{th.}})$.

```{important}
The projection is useless when only active power control is applied as no point can lie outside the disc of radius
$S^{\max}$.
```

This domain of feasible points is depicted in the figure below:

```{image} /_static/Load/FlexibleLoad/Domain_PmaxU_Qconst.svg
:width: 300
:align: center
```

The `FlexibleParameter` class has a method {meth}`~roseau.load_flow.FlexibleParameter.compute_powers`
that allows to compute the resulting powers of the control at different voltage levels for a given
theoretical power.

In the following example, we define a flexible parameter with a $P(U)$ control, a constant $P$
projection, and a 5 kVA maximum power. We want to know what would the control produce for all
voltages between 205 V and 255 V if given a theoretical power of $-2.5 + 1j$ kVA.

```python
import numpy as np
import roseau.load_flow as rlf

# A flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.p_max_u_production(
        u_up=rlf.Q_(240, "V"), u_max=rlf.Q_(250, "V")
    ),
    control_q=rlf.Control.constant(),
    projection=rlf.Projection(type="keep_p"),  # <----- No consequence
    s_max=rlf.Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5 + 1j, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

Plotting the control curve $P(U)$ using the variables `voltages` and `res_flexible_powers` of the
example above produces the following plot:

```{image} /_static/Load/FlexibleLoad/PmaxU_Qconst_Control_Curve_Example.svg
:width: 700
:align: center
```

The non-smooth theoretical control function is the control function applied to $S^{\max}$. The
"Actual power" plotted is the power actually produced by the load for each voltage. Below 240 V,
there is no variation in the produced power which is expected. Between 240 V and approximately
245 V, there is no reduction of the produced power because the curtailment
factor (computed from the voltage) times $S^{\max}$ is lower than $P^{\mathrm{th.}}$. As a consequence,
$P^{\mathrm{th.}}$ is produced. Starting at approximately 245 V, the comparison changes and the
actually produced power starts to decrease until it reaches 0 W at 250 V.

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax, res_flexible_powers = fp.plot_control_p(voltages=voltages, power=power)
plt.show()
```

The method returns a 2-tuple with the _matplotlib axis_ of the plot and the computed powers.

`````{tip}
To install _matplotlib_ along side _roseau-load-flow_, you can use the `plot` extra:

````{tab}  Linux/MacOS
```console
$ python -m pip install "roseau-load-flow[plot]"
```
````

````{tab} Windows
```doscon
C:> py -m pip install "roseau-load-flow[plot]"
```
````

Matplotlib is always installed when `conda` is used.
`````

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/PmaxU_Qconst_Trajectory_Example.svg
:width: 700
:align: center
```

All the points have been plotted (1 per volt between 205 V and 255 V). Many points overlap.

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
    voltages_labels_mask=np.isin(voltages, [240, 250]),
    ax=ax,
)
plt.show()
```

## Reactive power control only

When the active power is constant (no $P$ control), only the reactive power changes as a function
of the local voltage. Thus, the reactive power may vary between $-S^{\max}$ and $+S^{\max}$. When
$P^{\mathrm{th.}}\neq 0$, the point $(P, Q)$ produced by the control might lie outside the disc of
radius $S^{\max}$ (when $P^{\mathrm{th.}}\neq 0$). Those points are projected on the circle of
radius $S^{\max}$ and depending on the projection, the feasible domains change.

### Constant $P$

If the _constant $P$_ (`keep_p`) projection is chosen, the feasible domain is limited to a vertical
segment as shown below.

```{image} /_static/Load/FlexibleLoad/Domain_Pconst_QU_P.svg
:width: 300
:align: center
```

Here is an example of a flexible parameter with a reactive power control and without active power
control:

```python
import numpy as np
import roseau.load_flow as rlf

# Flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(250, "V"),
    ),
    projection=rlf.Projection(type="keep_p"),  # <---- Keep P
    s_max=rlf.Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

The variable `res_flexible_powers` contains the powers that have been actually produced by
the flexible load for the voltages stored in the variable named `voltages`.

Plotting the control curve $Q(U)$ gives:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_P_Control_Curve_Example.svg
:width: 700
:align: center
```

Notice that, even with a voltage lower than $U^{\min}$ or greater than $U^{\max}$, the available reactive
power (by default taken in the interval $[-S^{\max}, S^{\max}]$) was never fully used because of the choice of the
projection.

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_control_q(voltages=voltages, power=power, ax=ax)
plt.show()
```

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_P_Trajectory_Example.svg
:width: 700
:align: center
```

As in the previous plot, there is one point per volt from 205 V to 255 V. Several remarks on this plot:

1. All the points are aligned on the straight line $P=-2.5$ kVA because it was the power provided to the flexible
   load and because the projection used was at _Constant P_.
2. Several points are overlapping for low and high voltages. For these extremities, the
   theoretical control curves would have forced the point of operation to be outside the disc of radius $S^{\max}$ (5
   kVA in this example).

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
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
Note that using this projection with a constant active power may result in a final active power
lower than the one provided (could reach 0 W in the worst-case)!
```

Here is an example the creation of such control with a constant $Q$ projection:

```python
import numpy as np
import roseau.load_flow as rlf

# Flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(250, "V"),
    ),
    projection=rlf.Projection(type="keep_q"),  # <---- Keep Q
    s_max=rlf.Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

The variable `res_flexible_powers` contains the powers that have been actually produced by
the flexible load for the voltages stored in the variable named `voltages`.

Plotting the control curve $Q(U)$ gives:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Q_Control_Curve_Example.svg
:width: 700
:align: center
```

Here, the complete possible range of reactive power is used. When the control finds an infeasible
solution, it reduces the active power because the projection type is _Constant Q_.

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_control_q(voltages=voltages, power=power, ax=ax)
plt.show()
```

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Q_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

Notice that when the voltages were too low or too high, the projection at constant $Q$ forces the
reduction of the produced active power to ensure a feasible solution. Like before, there is one
point per volt. Several points overlap at the extremities near the coordinates (0,5 kVA) and
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

```python
import numpy as np
import roseau.load_flow as rlf

# Flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(250, "V"),
    ),
    projection=rlf.Projection(type="euclidean"),  # <---- Euclidean
    s_max=rlf.Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

The variable `res_flexible_powers` contains the powers that have been actually produced by
the flexible load for the voltages stored in the variable named `voltages`.

Plotting the control curve $Q(U)$ gives:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Eucl_Control_Curve_Example.svg
:width: 700
:align: center
```

Here, again the complete reactive power range is not fully used.

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_control_q(voltages=voltages, power=power, ax=ax)
plt.show()
```

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Eucl_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

Notice that when the voltages were too low or too high, the Euclidean projection forces the
reduction of the produced active power and the (produced and consumed) reactive power to ensure a
feasible solution. Like before, there is one point per volt and several points overlap.

### $Q^{\min}$ and $Q^{\max}$ limits

It is also possible to define a minimum and maximum reactive power values. In that case, the feasible domain is
constrained between those two values.

```{image} /_static/Load/FlexibleLoad/Domain_Pconst_QU_Qmin_Qmax.svg
:width: 300
:align: center
```

```python
import numpy as np
import roseau.load_flow as rlf

# Flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(250, "V"),
    ),
    projection=rlf.Projection(type="euclidean"),
    s_max=rlf.Q_(5, "kVA"),
    q_min=rlf.Q_(-3, "kVAr"),  # <---- set Q_min >= -S_max
    q_max=rlf.Q_(4, "kVAr"),  # <---- set Q_max <= S_max
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

The variable `res_flexible_powers` contains the powers that have been actually produced by
the flexible load for the voltages stored in the variable named `voltages`.

Plotting the control curve $Q(U)$ gives:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Qmin_Qmax_Control_Curve_Example.svg
:width: 700
:align: center
```

Here, again the complete reactive power range is not fully used as it is constrained between the $Q^{\min}$ and
$Q^{\max}$ values defined.

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_control_q(voltages=voltages, power=power, ax=ax)
plt.show()
```

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/Pconst_QU_Qmin_Qmax_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

## Both active and reactive powers control

When both active and reactive power controls are activated, the feasible domain is the following:

```{image} /_static/Load/FlexibleLoad/Domain_PmaxU_QU.svg
:width: 300
:align: center
```

Every point whose abscissa is between $P^{\mathrm{th.}}$ and 0, whose ordinate is between $-S^{\max}$
and $+S^{\max}$ and which lies in the disc of radius $S^{\max}$ (blue shaded area) is reachable.
Let's look at two examples: in the first one, the controls are activated sequentially (reactive power
first and then active power) and, in the other example, they are used together.

### Sequentially activated controls

Let's define different voltage thresholds for each control so that one triggers before the other.

#### Reactive power control first

Here, the reactive power control is activated at 230 V and fully used above 240 V. Then, at 245 V, the
active power control starts and is fully used at 250 V:

```python
import numpy as np
import roseau.load_flow as rlf

# Flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.p_max_u_production(
        u_up=rlf.Q_(245, "V"), u_max=rlf.Q_(250, "V")  # <----
    ),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(230, "V"),  # <---- lower than U_up of the P(U) control
        u_max=rlf.Q_(240, "V"),  # <---- lower than U_up of the P(U) control
    ),
    projection=rlf.Projection(type="euclidean"),  # <---- Euclidean
    s_max=rlf.Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Sequential_1_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

When the voltage is low, only the reactive power control is activated (vertical segment at
$P^{\mathrm{th.}}$); similar to what we saw in the $Q(U)$ control section.

When the voltage is high, there are two stages:

1. Between 230 V and 240 V, only the reactive power changes: It increases on the vertical segment
   to reach the perimeter of the disk.
2. Between 245 V and 250 V, the active power control starts reducing the active power until it
   reaches 0 W at 250 V.

#### Active power control first

Here, the active power control is activated at 240 V and fully used above 245 V. Then, at 245 V, the
reactive power control starts and is fully activated at 250 V.

```python
import numpy as np
import roseau.load_flow as rlf

# Flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.p_max_u_production(
        u_up=rlf.Q_(230, "V"), u_max=rlf.Q_(240, "V")  # <----
    ),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(245, "V"),  # <---- higher than U_max of the P(U) control
        u_max=rlf.Q_(250, "V"),  # <---- higher than U_max of the P(U) control
    ),
    projection=rlf.Projection(type="euclidean"),  # <---- Euclidean
    s_max=rlf.Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Sequential_2_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

When the voltage is low, only the reactive power control is activated (vertical segment at
$P^{\mathrm{th.}}$); similar to what we saw in the $Q(U)$ control section.

When the voltage is high, there are two stages:

1. Between 230 V and 240 V, only the active power changes. It decreases to about 0 W.
2. Between 245 V and 250 V, the reactive power control increases the reactive power until it
   reaches $S^{max}$ at 250 V.

### Simultaneously activated controls

Here, the active and the reactive powers controls are both activated at 240 V and reach their full
effect at 250 V.

```python
import numpy as np
import roseau.load_flow as rlf

# Flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.p_max_u_production(
        u_up=rlf.Q_(240, "V"), u_max=rlf.Q_(250, "V")  # <----
    ),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),  # <---- same as U_up of the P(U) control
        u_max=rlf.Q_(250, "V"),  # <---- same as U_max of the P(U) control
    ),
    projection=rlf.Projection(type="euclidean"),  # <---- Euclidean
    s_max=rlf.Q_(5, "kVA"),
)

# We want to get the res_flexible_powers for a set of voltages norms
voltages = np.arange(205, 256, dtype=float)

# and when the theoretical power is the following
power = rlf.Q_(-2.5, "kVA")

# Get the resulting flexible powers for the given theoretical power and voltages list.
res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
```

If we plot the trajectory of the control in the $(P, Q)$ space, we get:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Simultaneous_Trajectory_Example.svg
:width: 700
:align: center
```

The same plot can be obtained with:

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=power,
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

When the voltage is low, only the reactive power control is activated (vertical segment at
$P^{\mathrm{th.}}$); similar to what we saw in the $Q(U)$ control section.

When the voltage is high, there are two stages:

1. Between 240 V and 245 V, the active power control does not modify the produced active power
   while the reactive power control starts to increase the reactive power.
2. Between 245 V and 250 V, the active power control starts decreasing the active power while the
   reactive power continues to increase.
3. Above 250 V, active power is reduced to 0 W and the reactive power is set to $S^{max}$.

If we change the theoretical power to 4 kVA.

```python
from matplotlib import pyplot as plt

ax = plt.subplot()  # New axes
ax, res_flexible_powers = fp.plot_pq(
    voltages=voltages,
    power=rlf.Q_(-4, "kVA"),  # <------ New power
    voltages_labels_mask=np.isin(voltages, [210, 215, 230, 245, 250]),
    ax=ax,
)
plt.show()
```

Now we get a different result:

```{image} /_static/Load/FlexibleLoad/PmaxU_QU_Simultaneous_2_Trajectory_Example.svg
:width: 700
:align: center
```
