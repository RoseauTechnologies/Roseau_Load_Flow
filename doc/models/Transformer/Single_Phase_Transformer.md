# Single-phase transformer

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
        \dfrac{n_2}{n_1} \underline{U_{a1}} &= \underline{U_{a2}} - Z_2 \cdot \underline{I_{a2}} \\
        \underline{I_{a1}} - Y_m \cdot \underline{U_{a1}} &= -\dfrac{n_2}{n_1} \underline{I_{a2}} \\
        \underline{I_{a1}} &= -\underline{I_{n1}} \\
        \underline{I_{a2}} &= -\underline{I_{n2}} \\
    \end{aligned}
  \right.
\end{equation}
```

with $\underline{Z_2}$ the series impedance and $\underline{Y_{\mathrm{m}}}$ the magnetizing admittance of the
transformer.

## Example

TODO
