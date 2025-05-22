---
myst:
  html_meta:
    "description lang=en": |
      The different types of projection of the control of a flexible load onto the domain of technical feasibility:
      Euclidean, constant P or constant Q.
    "keywords lang=en": simulation, distribution grid, flexible load, projection, euclidean, constant P, constant Q
    # spellchecker:off
    "description lang=fr": |
      Les différents types de projection du contrôle d'une charge flexible sur le domaine de faisabilités technique:
      euclidienne, P constant ou Q constant.
    "keywords lang=fr": |
      simulation, réseau, électrique, charge flexible, domaine de faisabilité, projection, euclidienne, P constant,
      Q constant

# spellchecker:on
---

(models-flexible_load-projections)=

# Projections

When the control algorithm is trying to find the best control for given voltage constraints, it
could find a solution that is not "feasible" by the load. This means that the active and reactive
powers $P$ and $Q$ that constitute the solution lie outside the feasible domain defined by a part
of the disc of radius $S^{\max}$ in the $(P, Q)$ space. In these cases, the solution has to be
projected into the feasible domain. We can choose how the projection is performed using three
available projection types:
the _Euclidean_ projection, the projection at _Constant $P$_ and the projection at _Constant $Q$_.

The projection accepts two approximation parameters: `alpha` and `epsilon`.

- `alpha` is used to compute soft sign function and soft projection function. The higher `alpha`
  is, the better the approximations are.
- `epsilon` is used to approximate a smooth square root function:
  ```{math}
  \sqrt{S} \approx \sqrt{\varepsilon \times \exp\left(\frac{-{|S|}^2}{\varepsilon}\right) + {|S|}^2}
  ```
  The lower `epsilon` is, the better the approximations are.

```{important}
Please note that no projection is performed if the final $\underline{S(U)}$ point lies in the disc of radius $S^{\max}$.
```

## Euclidean projection

A Euclidean projection on the feasible domain. This is the default value for projections when it is
not specified.

```{image} /_static/Load/FlexibleLoad/Euclidean_Projection.svg
:width: 300
:align: center
```

```python
import roseau.load_flow as rlf

projection = rlf.Projection(type="euclidean")  # alpha and epsilon can be provided
```

```{important}
Please note that using the Euclidean projection may reduce the provided $P^{\mathrm{th.}}$ and $Q^{\mathrm{th.}}$ of
the load. See the [Feasible Domain page](models-flexible_load-feasible_domains) for more details.
```

## Constant $P$

Keep the value of $P$ computed by the control and project $Q$ on the feasible domain.

```{image} /_static/Load/FlexibleLoad/Constant_P_Projection.svg
:width: 300
:align: center
```

```python
import roseau.load_flow as rlf

projection = rlf.Projection(type="keep_p")  # alpha and epsilon can be provided
```

```{important}
Please note that using the _Constant $P$_ projection may reduce the provided $Q^{\mathrm{th.}}$ of the load. See the
[Feasible Domain page](models-flexible_load-feasible_domains) for more details.
```

## Constant $Q$

Keep the value of $Q$ computed by the control and project $P$ on the feasible domain.

```{image} /_static/Load/FlexibleLoad/Constant_Q_Projection.svg
:width: 300
:align: center
```

```python
import roseau.load_flow as rlf

projection = rlf.Projection(type="keep_q")  # alpha and epsilon can be provided
```

```{important}
Please note that using the _Constant $Q$_ projection may reduce the provided $P^{\mathrm{th.}}$ of
the load. See the [Feasible Domain page](models-flexible_load-feasible_domains) for more details.
```
