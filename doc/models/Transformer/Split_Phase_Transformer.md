# Split-phase transformer

## Definition

The split-phase transformer allows to convert a two phases primary winding into a split-phase secondary winding, with
the neutral at the center of the 2 phases. It is modelled as follows:

````{tab} European standards
```{image}  /_static/Transformer/European_Split_Phase_Transformer.svg
:alt: Split-phase transformer diagram
:width: 500px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Split_Phase_Transformer.svg
:alt: Split-phase transformer diagram
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
        \underline{U_{a2, 0}} &= -\underline{U_{b2, 0}} \\
        \dfrac{n_2}{n_1} \underline{U_{ab1}} &= \underline{U_{a2,0}} - \underline{U_{b2,0}} \\
        \underline{I_{a1}} - Y_m \cdot \underline{U_{ab1}} &=
        -\dfrac{n_2}{n_1} \cdot \frac{\underline{I_{a2}} + \underline{I_{b2}}}{2} \\
        \underline{I_{a1}} &= -\underline{I_{n1}} \\
        \underline{I_{a2}} + \underline{I_{b2}} + \underline{I_{n2}} &= 0 \\
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
        \underline{U_{a2, 0}} &= \underline{U_{a2}} - \frac{Z_2}{2} \underline{I_{a2}} \\
        \underline{U_{b2, 0}} &= \underline{U_{b2}} - \frac{Z_2}{2} \underline{I_{b2}}
    \end{aligned}
  \right.
\end{equation}
```


## Example

TODO
