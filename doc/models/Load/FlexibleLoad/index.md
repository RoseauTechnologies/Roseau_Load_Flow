---
myst:
  html_meta:
    description lang=en: |
      Flexible load models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    keywords lang=en: simulation, distribution grid, flexible load, load, model
    # spellchecker:off
    description lang=fr: |
      Les modèles de charge flexibles dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré
      dans une API Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, charge flexible, bus, roseau load flow, modèle
# spellchecker:on
---

# Flexible loads

They are a special type of power loads: instead of being constant, the power will depend on the voltage measured at the
load and the control applied to the load.

## Equations

The equations are the following (star loads):

```{math}
\left\{
    \begin{aligned}
        \underline{I_{\mathrm{abc}}} &= \left(\frac{
            \underline{S_{\mathrm{abc}}}(\underline{V_{\mathrm{abc}}}-\underline{V_{\mathrm{n}}})
        }{\underline{V_{\mathrm{abc}}}-\underline{V_{\mathrm{n}}}}\right)^{\star} \\
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

- The theoretical power $\underline{S^{\mathrm{th.}}}$ that the load would have if no control is applied.
- The maximal power $S^{\max}$ that can be injected/consumed by the load. For a PV installation, this is usually the
  rated power of the inverter.
- The type of control (see [here](models-flexible_load-controls)).
- The type of projection (see [here](models-flexible_load-projections)).

## Detailed pages

All these elements are detailed in the following sections:

```{toctree}
---
maxdepth: 2
caption: Flexible loads
---
Control
Projection
FlexibleParameter
FeasibleDomain
```

## Available Results

In addition to the results available for all loads, as described [here](../index.md#available-results), the following
results are available for flexible loads:

| Result Accessor       | Default Unit | Type          | Description                                    |
| --------------------- | ------------ | ------------- | ---------------------------------------------- |
| `res_flexible_powers` | $V\!A$       | complex array | The powers in the inner components of the load |

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.Control
   :members:
   :show-inheritance:
   :no-index:
.. autoapiclass:: roseau.load_flow.models.Projection
   :members:
   :show-inheritance:
   :no-index:
.. autoapiclass:: roseau.load_flow.models.FlexibleParameter
    :members:
    :show-inheritance:
    :no-index:
```
