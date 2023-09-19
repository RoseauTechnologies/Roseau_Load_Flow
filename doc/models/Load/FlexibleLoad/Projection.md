(models-flexible_load-projections)=

# Projections

The different controls may produce values for $P$ and $Q$ that are not feasible. The feasibility
domain in the $(P, Q)$ space is a part of the disc of radius $S^{\max}$. In these cases, the
solution found by the control algorithm has to be projected on the feasible domain. That's why we
need to define how the projection is done. There are three available projection types: the
_Euclidean_ projection, the projection at _Constant $P$_ and the projection at _Constant $Q$_.

The projection accepts two approximation parameters: `alpha` and `epsilon`.

- `alpha` is used to compute soft sign function and soft projection function. The higher `alpha`
  is, the better the approximations are.
- `epsilon` is used to approximate a smooth square root function:
  ```{math}
  \sqrt{S} \approx \sqrt{\varepsilon \times \exp\left(\frac{-{|S|}^2}{\varepsilon}\right) + {|S|}^2}
  ```
  The lower `epsilon` is, the better the approximations are.

```{important}
Please note that no projection is performed in the final $\underline{S(U)}$ point lies in the disc of radius $S^{\max}$.
```

## Euclidean projection

A Euclidean projection on the feasible domain. This is the default value for projections when it is
not specified.

```{image} /_static/Load/FlexibleLoad/Euclidean_Projection.svg
:width: 300
:align: center
```

```python
from roseau.load_flow import Projection

projection = Projection(type="euclidean")  # alpha and epsilon can be provided
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
from roseau.load_flow import Projection

projection = Projection(type="keep_p")  # alpha and epsilon can be provided
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
from roseau.load_flow import Projection

projection = Projection(type="keep_q")  # alpha and epsilon can be provided
```

```{important}
Please note that using the _Constant $Q$_ may reduce the provided $P^{\mathrm{th.}}$ of the load. See the [Feasible
Domain page](models-flexible_load-feasible_domains) for more details.
```
