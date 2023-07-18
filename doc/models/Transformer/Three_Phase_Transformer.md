(three-phase-transformer)=
# Three-phase transformer

## Definition

Three-phase transformers can be modeled with 3 transformers, connected to the primary side (generally the high voltage
side) with the primary windings and to the secondary side (generally the low voltage side) with the secondary windings.

````{tab} European standards
```{image}  /_static/Transformer/European_Three_Phase_Transformer.svg
:alt: Three-phase transformer diagram
:width: 700px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Three_Phase_Transformer.svg
:alt: Three-phase transformer diagram
:width: 700px
:align: center
```
````

As non-ideal models are used in *Roseau Load Flow*, we can see the addition of $\underline{Z_2}$ the series impedances
and $\underline{Y_{\mathrm{m}}}$ the magnetizing admittances.

For example, the windings $Dyn11$ are represented by the following diagram:

````{tab} European standards
```{image}  /_static/Transformer/European_Dyn11.svg
:alt: Dyn11 windings diagram
:width: 700px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Dyn11.svg
:alt: Dyn11 windings diagram
:width: 700px
:align: center
```
````

## Windings

There are multiple ways to connect the transformers, which are represented in the following windings diagrams

### Phase displacement of 0

```{image}  /_static/Transformer/Windings_Dd0.svg
:alt: Windings Dd0 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Yy0.svg
:alt: Windings Yy0 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Dz0.svg
:alt: Windings Dz0 diagram
:width: 400px
:align: center
```

### Phase displacement of 6

```{image}  /_static/Transformer/Windings_Dd6.svg
:alt: Windings Dd6 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Yy6.svg
:alt: Windings Yy6 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Dz6.svg
:alt: Windings Dz6 diagram
:width: 400px
:align: center
```

### Phase displacement of 11

```{image}  /_static/Transformer/Windings_Dy11.svg
:alt: Windings Dy11 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Yd11.svg
:alt: Windings Yd11 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Yz11.svg
:alt: Windings Yz11 diagram
:width: 400px
:align: center
```

### Phase displacement of 5

```{image}  /_static/Transformer/Windings_Dy5.svg
:alt: Windings Dy5 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Yd5.svg
:alt: Windings Yd5 diagram
:width: 400px
:align: center
```
<br/>

```{image}  /_static/Transformer/Windings_Yz5.svg
:alt: Windings Yz5 diagram
:width: 400px
:align: center
```

## Matrices

For all the windings, different matrices are associated:

### Transformation matrices

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 1
:align: center

* - Winding
  - $M_{\mathrm{TV}}$
  - $M_{\mathrm{TI}}$

* - Dd, Yy, Dy and Yd
  - $\dfrac{n_2}{n_1}\begin{pmatrix}
    1 & 0 & 0\\
    0 & 1 & 0\\
    0 & 0 & 1
    \end{pmatrix}$
  - $\dfrac{n_2}{n_1}\begin{pmatrix}
    -1 & 0 & 0\\
    0 & -1 & 0\\
    0 & 0 & -1
    \end{pmatrix}$

* - Dz et Yz
  - $\dfrac{n_2}{n_1}\begin{pmatrix}
    1 & 0 & 0\\
    0 & 1 & 0\\
    0 & 0 & 1
    \end{pmatrix}$
  - $\dfrac{n_2}{n_1}\begin{pmatrix}
    -1 & 1 & 0\\
    0 & -1 & 1\\
    1 & 0 & -1
    \end{pmatrix}$
```

### Primary winding matrices

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 1
:align: center

* - Winding
  - $K_{\mathrm{VABC}}$
  - $K_{\mathrm{UXYZ}}$
  - $K_{\mathrm{IABC}}$
  - $K_{\mathrm{IXYZ}}$
  - $K_{\mathrm{N}}$

* - Dx
  - $\begin{pmatrix}
        1 & -1 & 0\\
        0 & 1 & -1\\
        -1 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & -1\\
        -1 & 1 & 0\\
        0 & -1 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        0\\
        0\\
        0
    \end{pmatrix}$

* - Yx
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1\\
        1\\
        1
    \end{pmatrix}$

* - Zx
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & -1\\
        -1 & 1 & 0\\
        0 & -1 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1\\
        1\\
        1
    \end{pmatrix}$
```

### Secondary windings matrices

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 1
:align: center

* - Winding
  - $K_{\mathrm{Vabc}}$
  - $K_{\mathrm{Uxyz}}$
  - $K_{\mathrm{Iabc}}$
  - $K_{\mathrm{Ixyz}}$
  - $K_{\mathrm{n}}$
* - Dd0
  - $\begin{pmatrix}
        1 & -1 & 0\\
        0 & 1 & -1\\
        -1 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & -1\\
        -1 & 1 & 0\\
        0 & -1 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        0\\
        0\\
        0
    \end{pmatrix}$

* - Yd11
  - $\begin{pmatrix}
        1 & 0 & -1\\
        -1 & 1 & 0\\
        0 & -1 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & -1 & 0\\
        0 & 1 & -1\\
        -1 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        0\\
        0\\
        0
    \end{pmatrix}$

* - Yy0 and Dy11
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1\\
        1\\
        1
    \end{pmatrix}$

* - Dz0
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & -1\\
        -1 & 1 & 0\\
        0 & -1 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1\\
        1\\
        1
    \end{pmatrix}$

* - Yz11
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & -1 & 0\\
        0 & 1 & -1\\
        -1 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1 & 0 & 0\\
        0 & 1 & 0\\
        0 & 0 & 1
    \end{pmatrix}$
  - $\begin{pmatrix}
        1\\
        1\\
        1
    \end{pmatrix}$
```

## Equations

The following equations are used for the 3-phase transformers:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
        K_{\mathrm{UXYZ}} \cdot \underline{U_{\mathrm{XYZ}}}
        &= K_{\mathrm{VABC}} \cdot \underline{V_{\mathrm{ABC}}} - K_{\mathrm{N}} \cdot \underline{V_{\mathrm{N}}} \\
        K_{\mathrm{Uxyz}} \cdot \left( M_{\mathrm{TV}}\cdot \underline{U_{\mathrm{XYZ}}} + \underline{Z_2} \cdot
        \underline{I_{\mathrm{xyz}}} \right)
            &= K_{\mathrm{Vabc}} \cdot \underline{V_{\mathrm{abc}}} - K_{\mathrm{n}} \cdot \underline{V_{\mathrm{n}}} \\
        K_{\mathrm{IABC}} \cdot \underline{I_{\mathrm{ABC}}} &= K_{\mathrm{IXYZ}} \cdot
            \left( \underline{Y_{\mathrm{m}}} \cdot \underline{U_{\mathrm{XYZ}}} + M_{\mathrm{TI}} \cdot
            \underline{I_{\mathrm{xyz}}} \right)\\
        K_{\mathrm{Iabc}} \cdot \underline{I_{\mathrm{abc}}} &= K_{\mathrm{Ixyz}} \cdot \underline{I_{\mathrm{xyz}}} \\
        \underline{I_{\mathrm{N}}} &= - K_{\mathrm{N}}^\top \cdot \underline{I_{\mathrm{ABC}}} \\
        \underline{I_{\mathrm{n}}} &= - K_{\mathrm{n}}^\top \cdot \underline{I_{\mathrm{abc}}}
    \end{aligned}
  \right.
\end{equation}
```

with $\underline{Z_2}$ the series impedance and $\underline{Y_{\mathrm{m}}}$ the magnetizing admittance of the
transformer.

## Example

TODO
