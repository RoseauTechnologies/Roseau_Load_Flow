# Flexible loads

They are a special case of power loads: instead of being constant, the power will depend on the voltage measured
at the load.

## Equations

The equations are the following (star loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{abc}}} &= \left(\frac{\underline{S_{\mathrm{abc}}}(\underline{V_{\mathrm{abc}}}-\underline{V_
        {\mathrm{n}}})}{\underline{V_{\mathrm{abc}}}-\underline{V_{\mathrm{n}}}}\right)^{\star} \\
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

The expression $\underline{S}(U)$ depends on forth elements:
* The theoretical power $\underline{S^{\mathrm{th.}}}$ that the load would have if no control is applied.
* The maximal power $S^{\max}$ that can be injected on the network. It usually depends on the size of the power
  inverter associated with the load.
* A type of control.
* A type of projection.

## Controls

There are four possible types of control.

### Constant control

#### Definition

No control is applied, this is equivalent to a classical power load. The constant control can be built like this:

#### Example

```python
from roseau.load_flow import Control

# Use the constructor. Note that the voltages are not important in this case.
control = Control(type="constant", u_min=0.0, u_down=0.0, u_up=0.0, u_max=0.0)

# Or use the class method
control = Control.constant()
```

### P(U) control

Control the maximum active power of the load (inverter) based on the voltage $P^{\max}(U)$. With this control, the
following soft clipping functions $s(U)$ are used (depending on the `alpha` parameter value), for production and
consumption.

#### Production

```{image}   /_static/Control_PU_Prod.svg
:alt: P(U) production control
:width: 600
:align: center
```

The final $P$ is then $P(U) = \max(s(U) \times S^{\max}, P^{\mathrm{th.}})$

#### Consumption

```{image}   /_static/Control_PU_Cons.svg
:alt: P(U) consumption control
:width: 600
:align: center
```

The final $P$ is then $P(U) = \min(s(U) \times S^{\max}, P^{\mathrm{th.}})$

#### Example

```python
from roseau.load_flow import Control, Q_

# Use the constructor. Note that u_min and u_down are useless with the production control
production_control = Control(
    type="p_max_u_production", u_min=0, u_down=0, u_up=Q_(240, "V"), u_max=Q_(250, "V")
)

# Or use the class method
production_control = Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V"))

# Use the constructor. Note that u_min and u_down are useless with the production control
consumption_control = Control(
    type="p_max_u_consumption", u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=0, u_max=0
)

# Or use the class method
consumption_control = Control.p_max_u_consumption(u_min=Q_(210, "V"), u_down=Q_(220, "V"))
```

### Q(U) control

#### Definition

Control the reactive power based on the voltage $Q(U)$. With this control, the following soft clipping function $s$
is used. It depends on the `alpha` parameter value. Its default value is 1000.

```{image}   /_static/Control_QU.svg
:alt: Q(U) control
:width: 600
:align: center
```

The final $Q$ is then $Q(U) = s(U) \times S^{max}$

#### Example

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

# Or use the class method
control = Control.q_u(
    u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
)
```

## Projection

Once the $P(U)$ and $Q(U)$ have been computed, they can lead to unacceptable solutions if they are out of the
$S^{\max}$ circle. That's why we need a projection in the acceptable domain. The three possible projection types are
the Euclidean projection, the projection at constant $P$ and the projection at constant $Q$.

The projection accepts two approximation parameters: `alpha` and `epsilon`.
* `alpha` is used to compute soft sign function and soft projection function. The higher, the better the
  approximations are.
* `epsilon` is used to approximate a smooth square root function:
  ```{math}
  \sqrt{S} = \sqrt{\varepsilon \times \exp\left(\frac{-{|S|}^2}{\varepsilon}\right) + {|S|}^2}
  ```
  The lower, the better the approximations are.

### Euclidean

#### Definition

A Euclidean projection on the feasible space. This is the default value for projections when it is not specified.

```{image} /_static/Euclidean_Projection.svg
:width: 300
:align: center
```

#### Example

```python
from roseau.load_flow import Projection

projection = Projection(type="euclidean")  # alpha and epsilon can be provided
```

### Constant $P$

#### Definition

We maintain a constant $P$.

```{image} /_static/Constant_P_Projection.svg
:width: 300
:align: center
```

#### Example

```python
from roseau.load_flow import Projection

projection = Projection(type="keep_p")  # alpha and epsilon can be provided
```


### Constant $Q$

#### Definition

We maintain a constant $Q$.

```{image} /_static/Constant_Q_Projection.svg
:width: 300
:align: center
```

#### Example

```python
from roseau.load_flow import Projection

projection = Projection(type="keep_q")  # alpha and epsilon can be provided
```


## Flexible parameters

### Definition

A flexible parameter is a combination of a control on the active power, a control on the reactive power, a
projection and a maximal apparent power for a single phase.

### Example

Here, we define a flexible parameter with a constant control on $P$ (meaning, no control), a control $Q(U)$ on $Q$,
a projection which keeps $P$ constant and a $S^{\max}$ of 5 kVA.

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

The flexible parameter can then be used in a `PowerLoad` constructor to make it flexible.

#### First example

Let's use the same flexible parameter for the three phases of a load.

```python
import numpy as np

from roseau.load_flow import FlexibleParameter, Control, Projection, Q_, PowerLoad, Bus

bus = Bus(id="bus", phases="abcn")

# Create a flexible parameter
fp = FlexibleParameter(
    control_p=Control.constant(),
    control_q=Control.q_u(
        u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V")
    ),
    projection=Projection(type="keep_p"),
    s_max=Q_(5, "kVA"),
)

# Use it in a load
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(np.array([1000, 1000, 1000]) * (1 - 0.3j), "VA"),
    flexible_params=[fp, fp, fp],
)
```

The created load is a three-phase star-connected load as the phases of the bus have been used (`"abcn"`). We
provided 3 theoretical powers using the `powers` argument. The load is flexible on its three phases and used the
same flexible parameter to control its consumption.

#### Second example

In this second example, we create a load with only two phases (+neutral) connected to a three-phase (+neutral) bus.
Two different control are applied by the load.

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

The first component of the load is connected between the phase "a" and "n" of the bus. Its control is a $Q(U)$
control with a projection at constant $P$ and a $S^{\max}$ of 5 kVA.

The second component of the load is connected between the phase "b" and "n" of the bus. Its control is a $P(U)$
control with an Euclidean projection and a $S^{\max}$ of 3 kVA.

#### Third example: PQ(U) control together

Finally, it is possible to combine $P(U)$ and $Q(U)$ controls, for example by using all the reactive power
before reducing the active power in order to limit the impact for the client.

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

# Use it in a load
load = PowerLoad(
    id="load",
    bus=bus,
    powers=Q_(-np.array([1000, 1000, 1000]), "VA"),
    flexible_params=[fp, fp, fp],
)
```

In this example, the same flexible parameter is used to control each phase of the three-phase delta-connected load.
In the flexible parameter, one can remark that the control on $Q(U)$ (production part) starts at 240 V and is
completely activated at 245 V. The $P(U)$ control starts at 245 V and is completely activated at 250 V.

Using this configuration, a *sequential PQ(U) control* has been created for this load. A *simultaneous PQ(U)
control* could have been defined by modifying the voltage thresholds of each control.

## Feasible domains

Depending on the mix of controls and projection used through this class, the feasible domains in the $(P, Q)$
space changes. Here is an illustration with a theoretical power depicting a production (negative $P^{\mathrm{th.}}$).

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
