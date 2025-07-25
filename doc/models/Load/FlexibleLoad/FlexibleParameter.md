---
myst:
  html_meta:
    description lang=en: |
      Flexible load parameters in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    keywords lang=en: simulation, distribution grid, flexible load, load, parameters
    # spellchecker:off
    description lang=fr: |
      Paramètres des charges flexibles dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré
      dans une API Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, charge flexible, bus, roseau load flow, paramètres
# spellchecker:on
---

(models-flexible_load-flexible_parameters)=

# Flexible parameters

A flexible parameter is a combination of a control on the active power, a control on the reactive power, a projection
and a maximal apparent power for one phase.

## Example

Here, we define a flexible parameter with:

- a constant control on $P$ (meaning, no control),
- a control $Q(U)$ on $Q$,
- a projection which keeps $P$ constant,
- an $S^{\max}$ of 5 kVA.

```python
import roseau.load_flow as rlf

fp = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(250, "V"),
    ),
    projection=rlf.Projection(type="keep_p"),
    s_max=rlf.Q_(5, "kVA"),
)
```

## Usage

To create a flexible load, create a `PowerLoad` passing it one or more `FlexibleParameter` objects using the
`flexible_params` parameter, one for each phase of the load.

### Scenario 1: Same $Q(U)$ control on all phases

In this scenario, we apply the same $Q(U)$ control on the three phases of a load. We define a flexible parameter with
constant $P$ control and use it in the load constructor.

```python
import numpy as np
import roseau.load_flow as rlf

bus = rlf.Bus(id="bus", phases="abcn")

# Create a flexible parameter object
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(250, "V"),
    ),
    projection=rlf.Projection(type="keep_p"),
    s_max=rlf.Q_(5, "kVA"),
)

# Use it for the three phases of the load
load = rlf.PowerLoad(
    id="load",
    bus=bus,
    powers=rlf.Q_(np.array([1000, 1000, 1000]) * (1 - 0.3j), "VA"),
    flexible_params=fp,  # <- this makes the load "flexible"
)
```

The created load is a three-phase star-connected load as the phases inherited from the bus include `"n"`. The `powers`
parameter of the `PowerLoad` constructor represents the theoretical powers of the three phases of the load. The load is
flexible on its three phases with the same flexible parameters.

### Scenario 2: Different controls on different phases

In this scenario, we create a load with only two phases and a neutral connected to a three-phase bus with a neutral. Two
different controls are applied by the load on the two phases.

```python
import numpy as np
import roseau.load_flow as rlf

bus = rlf.Bus(id="bus", phases="abcn")

# Create a first flexible parameter (Q(U) control)
fp1 = rlf.FlexibleParameter(
    control_p=rlf.Control.constant(),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(250, "V"),
    ),
    projection=rlf.Projection(type="keep_p"),
    s_max=rlf.Q_(5, "kVA"),
)

# Create a second flexible parameter (P(U) control)
fp2 = rlf.FlexibleParameter(
    control_p=rlf.Control.p_max_u_consumption(
        u_min=rlf.Q_(210, "V"), u_down=rlf.Q_(220, "V")
    ),
    control_q=rlf.Control.constant(),
    projection=rlf.Projection(type="euclidean"),
    s_max=rlf.Q_(3, "kVA"),
)

# Use them in a load
load = rlf.PowerLoad(
    id="load",
    bus=bus,
    phases="abn",
    powers=rlf.Q_(np.array([1000, 1000]) * (1 - 0.3j), "VA"),
    flexible_params=[fp1, fp2],  # <- one for each phase of the load
)
```

The first element of the load is connected between phase "a" and "n" of the bus. Its control is a $Q(U)$ control with a
projection at constant $P$ and an $S^{\max}$ of 5 kVA.

The second element of the load is connected between phase "b" and "n" of the bus. Its control is a $P(U)$ control with a
Euclidean projection and an $S^{\max}$ of 3 kVA.

### Scenario 3: $PQ(U)$ control

Finally, it is possible to combine $P(U)$ and $Q(U)$ controls, for example by first using all available reactive power
before reducing the active power in order to limit the impact for the client.

```python
import numpy as np
import roseau.load_flow as rlf

bus = rlf.Bus(id="bus", phases="abc")

# Create a flexible parameter
fp = rlf.FlexibleParameter(
    control_p=rlf.Control.p_max_u_production(
        u_up=rlf.Q_(245, "V"), u_max=rlf.Q_(250, "V")
    ),
    control_q=rlf.Control.q_u(
        u_min=rlf.Q_(210, "V"),
        u_down=rlf.Q_(220, "V"),
        u_up=rlf.Q_(240, "V"),
        u_max=rlf.Q_(245, "V"),
    ),
    projection=rlf.Projection(type="euclidean"),
    s_max=rlf.Q_(5, "kVA"),
)

# Or using the shortcut
fp = rlf.FlexibleParameter.pq_u_production(
    up_up=rlf.Q_(245, "V"),
    up_max=rlf.Q_(250, "V"),
    uq_min=rlf.Q_(210, "V"),
    uq_down=rlf.Q_(220, "V"),
    uq_up=rlf.Q_(240, "V"),
    uq_max=rlf.Q_(245, "V"),
    s_max=rlf.Q_(5, "kVA"),
)

# Use it in a load
load = rlf.PowerLoad(
    id="load",
    bus=bus,
    powers=rlf.Q_(-np.array([1000, 1000, 1000]), "VA"),  # <- negative powers (generator)
    flexible_params=fp,
)
```

In this example, the same flexible parameter is used to control all phases of the three-phase delta-connected load. In
the flexible parameter, one can remark that the $Q(U)$ control on high voltages triggers at 240 V (production) and
reaches its maximum at 245 V. The $P(U)$ control however triggers at 245 V and is maxed out at 250 V.

Using this configuration, a _sequential $PQ(U)$ control_ has been created for this load. A _simultaneous $PQ(U)$
control_ could have been defined by using the same voltage thresholds for both controls.
