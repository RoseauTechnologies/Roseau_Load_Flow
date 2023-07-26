# Flexible loads

They are a special case of power loads: instead of being constant, the power will depend on the
voltage measured at the load and the control applied to the load.

## Equations

The equations are the following (star loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{a,b,c}}} &= \left(\frac{
            \underline{S_{\mathrm{a,b,c}}}(\underline{V_{\mathrm{a,b,c}}}-\underline{V_{\mathrm{n}}})
        }{\underline{V_{\mathrm{a,b,c}}}-\underline{V_{\mathrm{n}}}}\right)^{\star} \\
        \underline{I_{\mathrm{n}}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}\underline{I_{p}}
    \end{aligned}
\right.
```

And the following (delta loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{ab}}} &= \left(\frac{\underline{S_{\mathrm{ab}}}(\underline{V_{\mathrm{a}}}-\underline
        {V_{\mathrm{b}}})}{\underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{b}}}}\right)^{\star} \\
        \underline{I_{\mathrm{bc}}} &= \left(\frac{\underline{S_{\mathrm{bc}}}(\underline{V_{\mathrm{b}}}-\underline
        {V_{\mathrm{c}}})}{\underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{c}}}}\right)^{\star} \\
        \underline{I_{\mathrm{ca}}} &= \left(\frac{\underline{S_{\mathrm{ca}}}(\underline{V_{\mathrm{c}}}-\underline
        {V_{\mathrm{a}}})}{\underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{a}}}}\right)^{\star}
    \end{aligned}
\right.
```

The expression $\underline{S}(U)$ depends on four parameters:
* The theoretical power $\underline{S^{\mathrm{th.}}}$ that the load would have if no control is applied.
* The maximal power $S^{\max}$ that can be injected/consumed by the load. For a PV installation, this is
  usually the rated power of the inverter.
* The type of control (see below).
* The type of projection (see below).

(models-flexible_load-controls)=
## Controls

There are four available types of control.

### Constant control

No control is applied, this is equivalent to a classical power load. The constant control can be
built like this:

```python
from roseau.load_flow import Control

# Use the constructor. Note that the voltages are not important in this case.
control = Control(type="constant", u_min=0.0, u_down=0.0, u_up=0.0, u_max=0.0)

# Or prefer using the shortcut
control = Control.constant()
```

(models-flexible_load-p_u_control)=
### P(U) control

Control the maximum active power of a load (often a PV inverter) based on the voltage $P^{\max}(U)$.

#### Production

With this control, the following soft clipping family of functions $s_{\alpha}(U)$ is used. The
default value of `alpha` is 1000.

```{image}   /_static/Control_PU_Prod.svg
:alt: P(U) production control
:width: 600
:align: center
```

The final $P$ is then $P(U) = \max(s(U) \times S^{\max}, P^{\mathrm{th.}})$

```python
from roseau.load_flow import Control, Q_

# Use the constructor. Note that u_min and u_down are useless with the production control
production_control = Control(
    type="p_max_u_production", u_min=0, u_down=0, u_up=Q_(240, "V"), u_max=Q_(250, "V")
)

# Or prefer the shortcut
production_control = Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V"))
```

#### Consumption

With this control, the following soft clipping family of functions $s_{\alpha}(U)$ is used. The
default value of `alpha` is 1000.

```{image}   /_static/Control_PU_Cons.svg
:alt: P(U) consumption control
:width: 600
:align: center
```

The final $P$ is then $P(U) = \min(s(U) \times S^{\max}, P^{\mathrm{th.}})$

```python
from roseau.load_flow import Control, Q_

# Use the constructor. Note that u_max and u_up are useless with the consumption control
consumption_control = Control(
    type="p_max_u_consumption", u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=0, u_max=0
)

# Or prefer the shortcut
consumption_control = Control.p_max_u_consumption(u_min=Q_(210, "V"), u_down=Q_(220, "V"))
```

(models-flexible_load-q_u_control)=
### Q(U) control

Control the reactive power based on the voltage $Q(U)$. With this control, the following soft
clipping family of functions $s_{\alpha}(U)$ is used. The default value of `alpha` is 1000.

```{image}   /_static/Control_QU.svg
:alt: Q(U) control
:width: 600
:align: center
```

The final $Q$ is then $Q(U) = s(U) \times S^{max}$

```python
from roseau.load_flow import Control, Q_

# Use the constructor. Note that all the voltages are important.
control = Control(
    type="q_u",
    u_min=Q_(210, "V"),
    u_down=Q_(220, "V"),
    u_up=Q_(240, "V"),
    u_max=Q_(250, "V"),
)

# Or prefer the shortcut
control = Control.q_u(
    u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
)
```

(models-flexible_load-projection)=
## Projection

The different controls may produce values for $P$ and $Q$ that are not feasible. The feasibility
domain in the $(P, Q)$ space is a part of the circle of radius $S^{\max}$. In these cases, the
solution found by the control algorithm has to be projected on the feasible domain. That's why we
need to define how the projection is done. There are three available projection types: the
*Euclidean* projection, the projection at *Constant $P$* and the projection at *Constant $Q$*.

The projection accepts two approximation parameters: `alpha` and `epsilon`.
* `alpha` is used to compute soft sign function and soft projection function. The higher `alpha`
  is, the better the approximations are.
* `epsilon` is used to approximate a smooth square root function:
  ```{math}
  \sqrt{S} = \sqrt{\varepsilon \times \exp\left(\frac{-{|S|}^2}{\varepsilon}\right) + {|S|}^2}
  ```
  The lower `epsilon` is, the better the approximations are.

### Euclidean projection

A Euclidean projection on the feasible domain. This is the default value for projections when it is
not specified.

```{image} /_static/Euclidean_Projection.svg
:width: 300
:align: center
```

```python
from roseau.load_flow import Projection

projection = Projection(type="euclidean")  # alpha and epsilon can be provided
```

### Constant $P$

Keep the value of $P$ computed by the control and project $Q$ on the feasible domain.

```{image} /_static/Constant_P_Projection.svg
:width: 300
:align: center
```

```python
from roseau.load_flow import Projection

projection = Projection(type="keep_p")  # alpha and epsilon can be provided
```

### Constant $Q$

Keep the value of $Q$ computed by the control and project $P$ on the feasible domain.

```{image} /_static/Constant_Q_Projection.svg
:width: 300
:align: center
```

```python
from roseau.load_flow import Projection

projection = Projection(type="keep_q")  # alpha and epsilon can be provided
```

(models-flexible_load-flexible_parameters)=
## Flexible parameters

A flexible parameter is a combination of a control on the active power, a control on the reactive
power, a projection and a maximal apparent power for one phase.

### Example

Here, we define a flexible parameter with:
* a constant control on $P$ (meaning, no control),
* a control $Q(U)$ on $Q$,
* a projection which keeps $P$ constant,
* an $S^{\max}$ of 5 kVA.

```python
from roseau.load_flow import FlexibleParameter, Control, Projection, Q_

fp = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
    ),
    projection=Projection(type="keep_p"),
    s_max=Q_(5, "kVA"),
)
```

### Usage

To create a flexible load, create a `PowerLoad` passing it a list of `FlexibleParameter` objects
using the `flexible_params` parameter, one for each phase of the load.

#### Scenario 1: Same $Q(U)$ control on all phases

In this scenario, we apply the same $Q(U)$ control on the three phases of a load. We define a
flexible parameter with constant $P$ control and use it three times in the load constructor.

```python
import numpy as np

from roseau.load_flow import FlexibleParameter, Control, Projection, Q_, PowerLoad, Bus

bus = Bus(id="bus", phases="abcn")

# Create a flexible parameter object
fp = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
    ),
    projection=Projection(type="keep_p"),
    s_max=Q_(5, "kVA"),
)

# Use it for the three phases of the load
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(np.array([1000, 1000, 1000]) * (1 - 0.3j), "VA"),
    flexible_params=[fp, fp, fp],  # <- this makes the load "flexible"
)
```

The created load is a three-phase star-connected load as the phases inherited from the bus include
`"n"`. The `powers` parameter of the `PowerLoad` constructor represents the theoretical powers of
the three phases of the load. The load is flexible on its three phases with the same flexible
parameters.

#### Scenario 2: Different controls on different phases

In this scenario, we create a load with only two phases and a neutral connected to a three-phase
bus with a neutral. Two different controls are applied by the load on the two phases.

```python
import numpy as np

from roseau.load_flow import FlexibleParameter, Control, Projection, Q_, PowerLoad, Bus

bus = Bus(id="bus", phases="abcn")

# Create a first flexible parameter (Q(U) control)
fp1 = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
    ),
    projection=Projection(type="keep_p"),
    s_max=Q_(5, "kVA"),
)

# Create a second flexible parameter (P(U) control)
fp2 = FlexibleParameter(
    control_p=Control.p_max_u_consumption(u_min=Q_(210, "V"), u_down=Q_(220, "V")),
    control_q=Control.constant(),
    projection=Projection(type="euclidean"),
    s_max=Q_(3, "kVA"),
)

# Use them in a load
load = PowerLoad(
    id="load",
    bus=bus,
    phases="abn",
    powers=Q_(np.array([1000, 1000]) * (1 - 0.3j), "VA"),
    flexible_params=[fp1, fp2],
)
```

The first element of the load is connected between phase "a" and "n" of the bus. Its control is a
$Q(U)$ control with a projection at constant $P$ and an $S^{\max}$ of 5 kVA.

The second element of the load is connected between phase "b" and "n" of the bus. Its control is a
$P(U)$ control with an Euclidean projection and an $S^{\max}$ of 3 kVA.

#### Scenario 3: PQ(U) control

Finally, it is possible to combine $P(U)$ and $Q(U)$ controls, for example by first using all
available reactive power before reducing the active power in order to limit the impact for the
client.

```python
import numpy as np

from roseau.load_flow import FlexibleParameter, Control, Projection, Q_, PowerLoad, Bus

bus = Bus(id="bus", phases="abc")

# Create a flexible parameter
fp = FlexibleParameter(
    control_p=Control.p_max_u_production(u_up=Q_(245, "V"), u_max=Q_(250, "V")),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(245, "V")
    ),
    projection=Projection(type="euclidean"),
    s_max=Q_(5, "kVA"),
)

# Or using the shortcut
fp = FlexibleParameter.pq_u_production(
    up_up=Q_(245, "V"),
    up_max=Q_(250, "V"),
    uq_min=Q_(210, "V"),
    uq_down=Q_(220, "V"),
    uq_up=Q_(240, "V"),
    uq_max=Q_(245, "V"),
    s_max=Q_(5, "kVA"),
)

# Use it in a load
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(-np.array([1000, 1000, 1000]), "VA"),
    flexible_params=[fp, fp, fp],
)
```

In this example, the same flexible parameter is used to control all phases of the three-phase
delta-connected load. In the flexible parameter, one can remark that the $Q(U)$ control on high
voltages triggers at 240 V (production) and reaches its maximum at 245 V. The $P(U)$ control
however triggers at 245 V and is maxed out at 250 V.

Using this configuration, a *sequential PQ(U) control* has been created for this load. A
*simultaneous PQ(U) control* could have been defined by using the same voltage thresholds for both
controls.

## Feasible domains

Depending on the mix of controls and projection used through this class, the feasible domains in
the $(P, Q)$ space changes. Here is an illustration with a theoretical production power
($P^{\mathrm{th.}} < 0$).

```{list-table}
:class: borderless
:header-rows: 1
:widths: 20 20 20 20 20

* -
  - $Q^{\mathrm{const.}}$
  - $Q(U)$ with an Euclidean projection
  - $Q(U)$ with a constant P projection
  - $Q(U)$ with a constant Q projection
* - $P^{\mathrm{const.}}$
  - ![image](/_static/Domain_Pconst_Qconst.svg)
  - ![image](/_static/Domain_Pconst_QU_Eucl.svg)
  - ![image](/_static/Domain_Pconst_QU_P.svg)
  - ![image](/_static/Domain_Pconst_QU_Q.svg)
* - $P^{\max}(U)$
  - ![image](/_static/Domain_PmaxU_Qconst.svg)
  - ![image](/_static/Domain_PmaxU_QU.svg)
  - ![image](/_static/Domain_PmaxU_QU.svg)
  - ![image](/_static/Domain_PmaxU_QU.svg)
```
