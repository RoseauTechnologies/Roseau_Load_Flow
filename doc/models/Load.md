# Loads

The load element can be used to model consumption loads (with positive active power) as well as generation loads
(with negative active power). Two types of connections can be made:
* star-connected loads using a `phases` constructor argument containing a `"n"`


```{image}  /_static/European_Star_Load.svg
:alt: Star load diagram
:width: 300px
:align: center
```

* delta-connected loads using a `phases` constructor argument which doesn't contain `"n"`

```{image}  /_static/European_Delta_Load.svg
:alt: Delta load diagram
:width: 300px
:align: center
```

## Power loads

They represent loads for which the power is considered constant. The equations are the following (star loads):

```{math}
I_{\mathrm{abc}} &= \left(\frac{S_{\mathrm{abc}}}{V_{\mathrm{abc}}-V_{\mathrm{n}}}\right)^{\star} \\
I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}
```

And the following (delta loads):

```{math}
I_{\mathrm{ab}} &= \left(\frac{S_{\mathrm{ab}}}{V_{\mathrm{a}}-V_{\mathrm{b}}}\right)^{\star} \\
I_{\mathrm{bc}} &= \left(\frac{S_{\mathrm{bc}}}{V_{\mathrm{b}}-V_{\mathrm{c}}}\right)^{\star} \\
I_{\mathrm{ca}} &= \left(\frac{S_{\mathrm{ca}}}{V_{\mathrm{c}}-V_{\mathrm{a}}}\right)^{\star}
```

## Impedance loads

They represent loads for which the impedance is considered constant. The equations are the following (star loads):

```{math}
I_{\mathrm{abc}} &= \frac{\left(V_{\mathrm{abc}}-V_{\mathrm{n}}\right)}{Z_{\mathrm{abc}}} \\
I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}
```

And the following (delta loads):

```{math}
I_{\mathrm{ab}} &= \frac{\left(V_{\mathrm{a}}-V_{\mathrm{b}}\right)}{Z_{\mathrm{ab}}} \\
I_{\mathrm{bc}} &= \frac{\left(V_{\mathrm{b}}-V_{\mathrm{c}}\right)}{Z_{\mathrm{bc}}} \\
I_{\mathrm{ca}} &= \frac{\left(V_{\mathrm{c}}-V_{\mathrm{a}}\right)}{Z_{\mathrm{ca}}}
```


## Current loads

They represent loads for which the current is considered constant. The equations are the following (star loads):

```{math}
I_{\mathrm{abc}} &= \mathrm{constant} \\
I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}
```

And the following (delta loads):

```{math}
I_{\mathrm{ab}} &= \mathrm{constant} \\
I_{\mathrm{bc}} &= \mathrm{constant} \\
I_{\mathrm{ca}} &= \mathrm{constant}
```

## Flexible loads

They are a special case of power loads: instead of being constant, the power will depend on the voltage measured
at the load. The equations are the following (star loads):

```{math}
I_{\mathrm{abc}} &= \left(\frac{S_{\mathrm{abc}}(U_{abc})}{V_{\mathrm{abc}}-V_{\mathrm{n}}}\right)^{\star} \\
I_{\mathrm{n}} &= -\sum_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}I_{p}
```

And the following (delta loads):

```{math}
I_{\mathrm{ab}} &= \left(\frac{S_{\mathrm{ab}}(U_{ab})}{V_{\mathrm{a}}-V_{\mathrm{b}}}\right)^{\star} \\
I_{\mathrm{bc}} &= \left(\frac{S_{\mathrm{bc}}(U_{bc})}{V_{\mathrm{b}}-V_{\mathrm{c}}}\right)^{\star} \\
I_{\mathrm{ca}} &= \left(\frac{S_{\mathrm{ca}}(U_{ca})}{V_{\mathrm{c}}-V_{\mathrm{a}}}\right)^{\star}
```

The expression $S(U)$ depends on forth elements:
* The theoretical power $S^{th}$ that the load would have if no control is applied.
* The maximal power $S^{max}$ that can be injected on the network. It usually depends on the size
of the power inverter associated with the load.
* A type of control.
* A type of projection.

### Controls

There are four possible types of control:

#### Constant control

No control is applied, this is equivalent to a classical power load.

#### P(U) control

Control the maximum active power of the load (inverter) based on the
voltage $P^{\max}(U)$. With this control, the following soft clipping functions $s(U)$ are used
(depending on the $alpha$ parameter value), for production and consumption.

* Production

```{image}   /_static/Control_PU_Prod.svg
:alt: P(U) production control
:width: 600
:align: center
```

The final $P$ is then $P(U) = max(s(U) \times S^{max}, P^{th})$

* Consumption

```{image}   /_static/Control_PU_Cons.svg
:alt: P(U) consumption control
:width: 600
:align: center
```

The final $P$ is then $P(U) = min(s(U) \times S^{max}, P^{th})$

#### Q(U) control

Control the reactive power based on the voltage $Q(U)$. With this control, the following soft clipping
function $s$ is used  (depending on the $alpha$ parameter value).

```{image}   /_static/Control_QU.svg
:alt: Q(U) control
:width: 600
:align: center
```

The final $Q$ is then $Q(U) = s(U) \times S^{max}$

#### PQ(U) control

Finally, it is possible to combine $P(U)$ and $Q(U)$ controls, for example by using all the reactive power
before reducing the active power in order to limit the impact for the client.

### Projection

Once the $P(U)$ and $Q(U)$ have been computed, they can lead to unacceptable solutions if they are out of
the $S^{max}$ circle. That's why we need a projection in the acceptable domain. The three possible
projection types are:

* ``"euclidean"`` for a Euclidean projection on the feasible space

```{image} /_static/Euclidean_Projection.svg
:width: 300
:align: center
```

* ``"keep_p"``: for maintaining a constant P

```{image} /_static/Constant_P_Projection.svg
:width: 300
:align: center
```

* ``"keep_q"``: for maintaining a constant Q

```{image} /_static/Constant_Q_Projection.svg
:width: 300
:align: center
```

```{note}
For all the projections, a square root function is used. It is approximated by a smooth sqrt function:
$\sqrt{S} = \sqrt{\varepsilon \times \exp\left(\frac{-{|S|}^2}{\varepsilon}\right) + {|S|}^2}$
```

### Feasible domains

Depending on the mix of controls and projection used through this class, the feasible domains in the $(P, Q)$
space changes. Here is an illustration with a theoretical power depicting a production (negative $P^{\mathrm{theo.}}$).

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
