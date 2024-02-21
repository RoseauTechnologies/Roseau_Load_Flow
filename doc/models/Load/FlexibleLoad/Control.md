---
myst:
  html_meta:
    "description lang=en": |
      Flexible load controls in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    "description lang=fr": |
      Les contrôles des charge flexibles dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et
      déséquilibré dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, charge flexible, bus, roseau load flow, modèle, contrôles
    "keywords lang=en": simulation, distribution grid, flexible load, load, model, controls
---

(models-flexible_load-controls)=

# Controls

There are four available types of control.

## Constant control

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

## $P(U)$ control

Control the maximum active power of a load (often a PV inverter) based on the voltage $P^{\max}(U)$.

```{note}
The functions $s_{\alpha}$ used for the $P(U)$ controls are derived from the *soft clipping function* of
{cite:p}`Klimek_2020`.
```

### Production

With this control, the following soft clipping family of functions $s_{\alpha}(U)$ is used. The default value of
`alpha` is 1000.

```{image} /_static/Load/FlexibleLoad/Control_PU_Prod.svg
:alt: P(U) production control
:width: 600
:align: center
```

The final $P$ is then $P(U) = \max(s_{\alpha}(U) \times S^{\max}, P^{\mathrm{th.}})$. Note that this final
$\underline{S(U)}$ point may lie outside the disc of radius $S^{\max}$ in the $(P, Q)$ plane. See the
[Projection page](models-flexible_load-projections) for more details about this case.

```python
from roseau.load_flow import Control, Q_

# Use the constructor. Note that u_min and u_down are useless with the production control
production_control = Control(
    type="p_max_u_production", u_min=0, u_down=0, u_up=Q_(240, "V"), u_max=Q_(250, "V")
)

# Or prefer the shortcut
production_control = Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V"))
```

### Consumption

With this control, the following soft clipping family of functions $s_{\alpha}(U)$ is used. The default value of
`alpha` is 1000.

```{image} /_static/Load/FlexibleLoad/Control_PU_Cons.svg
:alt: P(U) consumption control
:width: 600
:align: center
```

The final $P$ is then $P(U) = \min(s_{\alpha}(U) \times S^{\max}, P^{\mathrm{th.}})$. Note that this final
$\underline{S(U)}$ point may lie outside the disc of radius $S^{\max}$ in the $(P, Q)$ plane. See the
[Projection page](models-flexible_load-projections) for more details about this case.

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

## $Q(U)$ control

Control the reactive power based on the voltage $Q(U)$. With this control, the following soft clipping family of
functions $s_{\alpha}(U)$ is used. The default value of `alpha` is 1000.

```{image} /_static/Load/FlexibleLoad/Control_QU.svg
:alt: Q(U) control
:width: 600
:align: center
```

The final $Q$ is then $Q(U) = s_{\alpha}(U) \times S^{\max}$. Note that this final $\underline{S(U)}$ point
may lie outside the disc of radius $S^{\max}$ in the $(P, Q)$ plane. See the
[Projection page](models-flexible_load-projections) for more details about this case.

```{note}
The function $s_{\alpha}$ used for the $Q(U)$ control is derived from the *soft clipping function* of
{cite:p}`Klimek_2020`.
```

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

## Bibliography

```{bibliography}
:filter: docname in docnames
```
