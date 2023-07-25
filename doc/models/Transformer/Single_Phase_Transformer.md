# Single-phase transformer

```{note}
In this page, the pictures and the equations depicts a single-phase transformer connected between phases $\mathrm{a}$
and $\mathrm{n}$. Single-phase transformers can obviously be connected to other phases.
```

## Definition

The single-phase transformers are modelled as follows:

````{tab} European standards
```{image}  /_static/Transformer/European_Single_Phase_Transformer.svg
:alt: Single-phase transformer diagram
:width: 500px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Single_Phase_Transformer.svg
:alt: Single-phase transformer diagram
:width: 500px
:align: center
```
````

As non-ideal models are used in *Roseau Load Flow*, we can see the addition of $\underline{Z_2}$ the series impedances
and $\underline{Y_{\mathrm{m}}}$ the magnetizing admittances.

## Equations

The following equations are used:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
        k \cdot \underline{U_{1,\mathrm{a}}} &= \underline{U_{2,\mathrm{a}}} - Z_2 \cdot \underline{I_{2,\mathrm{a}}} \\
        \underline{I_{1,\mathrm{a}}} - Y_{\mathrm{m}} \cdot \underline{U_{1,\mathrm{a}}} &= -k \cdot \underline{I_{2,\mathrm{a}}} \\
        \underline{I_{1,\mathrm{a}}} &= -\underline{I_{1,\mathrm{n}}} \\
        \underline{I_{2,\mathrm{a}}} &= -\underline{I_{2,\mathrm{n}}} \\
    \end{aligned}
  \right.
\end{equation}
```

with $\underline{Z_2}$ the series impedance, $\underline{Y_{\mathrm{m}}}$ the magnetizing admittance of the
transformer, and $k$ the transformation ratio.

## Example

TODO
