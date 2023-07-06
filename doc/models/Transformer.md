# Transformers

## Three-phase Transformer

Three-phase transformers can be modeled with 3 transformers, connected to the primary side (generally the high voltage
side) with the primary windings and to the secondary side (generally the low voltage side) with the secondary windings.

```{image}  /_static/Transformer.png
:alt: Transformer diagram
:width: 700px
:align: center
```

As non-ideal models are used in Roseau Load Flow, we can see the addition of $Z_2$ the series impedances
and $Y_m$ the magnetizing admittances.

### Windings

There are multiple ways to connect the transformers, which are represented in the following windings diagram:

```{image}  /_static/Windings.png
:alt: Windings diagram
:width: 700px
:align: center
```

For example, the windings $Dyn11$ are represented by the following diagram:

```{image}  /_static/Dyn11.png
:alt: Dyn11 windings diagram
:width: 600px
:align: center
```

For all the windings, different matrices are associated:

- The transformation matrices:

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 1
:align: center

* - Winding
  - $M_{TV}$
  - $M_{TI}$

* - Dd, Yy, Dy and Yd
  - $\frac{n_2}{n_1}\begin{pmatrix}
    1 & 0 & 0\\
    0 & 1 & 0\\
    0 & 0 & 1
    \end{pmatrix}$
  - $\frac{n_2}{n_1}\begin{pmatrix}
    -1 & 0 & 0\\
    0 & -1 & 0\\
    0 & 0 & -1
    \end{pmatrix}$

* - Dz et Yz
  - $\frac{n_2}{n_1}\begin{pmatrix}
    1 & 0 & 0\\
    0 & 1 & 0\\
    0 & 0 & 1
    \end{pmatrix}$
  - $\frac{n_2}{n_1}\begin{pmatrix}
    -1 & 1 & 0\\
    0 & -1 & 1\\
    1 & 0 & -1
    \end{pmatrix}$
```

with $k = \frac{n_2}{n_1}$ the transformation ratio.

- The primary winding matrices:

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 1
:align: center

* - Winding
  - $K_{VABC}$
  - $K_{UXYZ}$
  - $K_{IABC}$
  - $K_{IXYZ}$
  - $K_{N}$

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

- The secondary windings matrices:

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 1
:align: center

* - Winding
  - $K_{Vabc}$
  - $K_{Uxyz}$
  - $K_{Iabc}$
  - $K_{Ixyz}$
  - $K_{n}$
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

### Equations

The following equations are used for the 3-phase transformers:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
      K_{UXYZ} \cdot U_{XYZ}
      &= K_{VABC} \cdot V_{ABC} - K_{N} \cdot V_{N} \\
      K_{Uxyz} \cdot \left( M_{TV}\cdot U_{XYZ} + Z_2
      \cdot I_{xyz} \right)
      &= K_{Vabc} \cdot V_{abc} - K_{n} \cdot V_{n} \\
      K_{IABC} \cdot I_{ABC} &= K_{IXYZ} \cdot
                                     \left( Y_{m} \cdot U_{XYZ} + M_{TI} \cdot
                                     I_{xyz} \right)\\
      K_{Iabc} \cdot I_{abc} &= K_{Ixyz} \cdot I_{xyz} \\
      I_{N} &= - K_{N}^\top \cdot I_{ABC} \\
      I_{n} &= - K_{n}^\top \cdot I_{abc}
    \end{aligned}
  \right.
\end{equation}
```

with $Z_2$ the series impedance, $Y_m$ the magnetizing admittance of the transformer and $k$ the transformation ratio.

The first two values are computed from the nominal power $S_n$, the losses during off-load test $P_0$, the current during
off-load test $i_0$, the losses during short circuit test $P_{sc}$ and the voltages on LV side during short circuit
test $V_{sc}$.
