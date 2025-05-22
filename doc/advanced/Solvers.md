---
myst:
  html_meta:
    "description lang=en": |
      With Roseau Load Flow you can choose between two methods: Newton-Raphson and Goldstein and Price - Three-phase
      unbalanced load flow solver in a Python API by Roseau Technologies.
    "keywords lang=en": simulation, distribution grid, Goldstein and Price, Newton-Raphson, solver
    # spellchecker:off
    "description lang=fr": |
      Avec Roseau Load Flow choisissez entre deux méthodes: Newton-Raphson et Goldstein and Price. Solveur
      d'écoulement de charge triphasé et déséquilibré dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, Goldstein and Price, Newton-Raphson, solveur
    # spellchecker:on
---

(solvers)=

# Solvers

## General information

The goal is to compute the voltages at each bus and the currents and powers flow in each branch of
the network. The computation must respect the Kirchhoff's laws and the constraints of the network.

More formally, this is done by solving a system of $n$ nonlinear equations with $n$ variables:

```{math}
F: \mathbb{R}^n \to \mathbb{R}^n
```

The goal is then to find $x$ such that:

```{math}
F(x) = 0
```

Computationally, this translates to finding a solution $x$ such that:

```{math}
||F(x)||_{\infty} < \varepsilon
```

With $\varepsilon$ being a small _tolerance_.
In code, $\varepsilon$ can be set with `en.solve_load_flow(tolerance=...)` (by default `1e-6`).

There are several solvers to solve this kind of problems. In _Roseau Load Flow_, the following
solvers are available:

## Newton-Raphson

This is the classical [_Newton-Raphson_ method](https://en.wikipedia.org/wiki/Newton%27s_method).

First, an initial solution $x_0$ is chosen by initializing the voltages either by propagating the
voltage of the sources or by re-using the results from the last successful run. The choice of
either option depends on the `warm_start` argument to the `en.solve_load_flow()` method.

Then, multiple iterations are made with:

```{math}
:label: step
x_{k+1} = x_k - J_F^{-1}(x_k)F(x_k)
```

with $J_F$ being the jacobian of $F$.

The algorithm stops when it finds a solution $x_k$ such that $||F(x_k)||_{\infty} < \varepsilon$
within a maximum number of iterations (modify with `en.solve_load_flow(max_iterations=...)`). If
the maximum number of iterations is exceeded, the solver did not converge and the execution
fails.

### Parameters

The _Newton-Raphson_ solver doesn't accept any parameter.

## Goldstein and Price

This is a variant of the classical _Newton-Raphson_ solver with a linear search.

At each iteration, $x_{k+1}$ is calculated using:

```{math}
:label: linear_search_step
x_{k+1} = x_k + t d(x_k)
```

with $d = -J_F^{-1}F$

For the classical _Newton-Raphson_ solver, $t=1$ is chosen for the next iterate.
The idea of the linear searches, in this case the _Goldstein and Price_ variant, is to find a
"better" $t$ that improves the convergence of the solver.

Let $g$ be a function to be minimized:

```{math}
g &: \mathbb{R}^n \to \mathbb{R} \\
g(x) &:= \frac{1}{2} ||F(x)||_2
```

Let $q$ be the function $g$ in the direction $d$:

```{math}
q &: \mathbb{R} \to \mathbb{R} \\
q(t) &:= g(x_k + t d(x_k))
```

A search is made to find $t$ such that:

```{math}
:label: goldstein_and_price
m_2q'(0) \leqslant \frac{q(t) - q(0)}{t} \leqslant m_1q'(0)
```

```{image} /_static/Advanced/Goldstein_And_Price.svg
:alt: Goldstein and Price conditions
:width: 500px
:align: center
```

In the figure above, any $t$ such that $a < t < b$ is satisfactory.

This $t$ is found by dichotomy with multiple iterations, but in most cases only one iteration is
needed. This is especially true when there are no flexible loads in the network.

$t$ is then used to compute $x_{k+1} = x_k + t d(x_k)$

The _Goldstein and Price_ variant is thus as fast as the classical _Newton-Raphson_ while being
more robust.

### Parameters

The _Goldstein and Price_ solver accepts the following parameters:

- `"m1"` the first constant of the _Goldstein and Price_ variant. By default: `0.1`.
- `"m2"` the second constant of the _Goldstein and Price_ variant. By default: `0.9`.
  Note that the constraint $m_1 < m_2$ must be met.

## Backward-Forward

This is an implementation of the backward-forward sweep method, which offers an efficient alternative to traditional
Newton-Raphson algorithms.

### Advantages

- **Faster Execution Time**: The backward-forward sweep method generally executes more quickly than Newton-Raphson-based
  approaches.

### Limitations

- **Modeling Restrictions**:
  - The network cannot contain loops.
  - Floating neutrals are not allowed for loads and sources.
- **Convergence**: This method may exhibit weaker convergence properties, particularly in scenarios involving
  flexible loads.

### Important Note

This solver is still in the **experimental** stage. Users should be aware that certain edge cases may not be handled
correctly when utilizing the backward-forward sweep method. If you face any issues with this solver, please let
us know by filing a GitHub issue

### Parameters

The _Backward-Forward_ solver doesn't accept any parameter.
