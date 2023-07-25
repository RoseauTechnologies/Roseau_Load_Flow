# Center-tapped transformer

```{note}
In this page, the pictures and the equations depicts a center-tapped transformer connected between phases $\mathrm{a}$
and $\mathrm{b}$. Center-tapped transformers can obviously be connected to other phases. Nevertheless, the
middle-position phase for the secondary part must be $\mathrm{n}$.
```

## Definition

The center-tapped transformer allows to convert a two phases primary winding into a split-phase secondary winding, with
the neutral at the center of the 2 phases. It is modelled as follows:

````{tab} European standards
```{image}  /_static/Transformer/European_Center_Tapped_Transformer.svg
:alt: Center-tapped transformer diagram
:width: 500px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Center_Tapped_Transformer.svg
:alt: Center-tapped transformer diagram
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
        \underline{U_{2,\mathrm{a}}^0} &= -\underline{U_{2,\mathrm{b}}^0} \\
        k \cdot \underline{U_{1,\mathrm{ab}}} &= \underline{U_{2,\mathrm{a}}^0} - \underline{U_{2,\mathrm
        {b}}^0} \\
        \underline{I_{1,\mathrm{a}}} - Y_{\mathrm{m}} \cdot \underline{U_{1,\mathrm{ab}}} &=
        -k \cdot \frac{\underline{I_{2,\mathrm{a}}} + \underline{I_{2,\mathrm{b}}}}{2} \\
        \underline{I_{1,\mathrm{a}}} &= -\underline{I_{1,\mathrm{n}}} \\
        \underline{I_{2,\mathrm{a}}} + \underline{I_{2,\mathrm{b}}} + \underline{I_{2,\mathrm{n}}} &= 0 \\
    \end{aligned}
  \right.
\end{equation}
```

with $\underline{Z_2}$ the series impedance, $\underline{Y_{\mathrm{m}}}$ the magnetizing admittance of the
transformer, and:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
        \underline{U_{2,\mathrm{a}}^0} &= \underline{U_{2,\mathrm{a}}} - \frac{Z_2}{2} \underline{I_{2,\mathrm{a}}} \\
        \underline{U_{2,\mathrm{b}}^0} &= \underline{U_{2,\mathrm{b}}} - \frac{Z_2}{2} \underline{I_{2,\mathrm{b}}}
        \end{aligned}
  \right.
\end{equation}
```


## Example

TODO
