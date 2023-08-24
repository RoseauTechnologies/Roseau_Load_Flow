# Line Parameters

The line parameters are briefly described [here](models-line_parameters). In this page, the alternative constructors
of `LineParameters` objects are detailed.

## Symmetric model

### Definition

The `LineParameters` class has a static method called `from_sym` which converts zero and direct sequences of
impedance and admittance into a line parameters instance. This method requires the following data:

- The zero sequence of the impedance (in $\Omega/km$), noted $\underline{Z_0}$ and `z0` in the code.
- The direct sequence of the impedance (in $\Omega/km$), noted $\underline{Z_1}$ and `z1` in the code.
- The zero sequence of the admittance (in $S/km$), noted $\underline{Y_0}$ and `y0` in the code.
- The direct sequence of the admittance (in $S/km$), noted $\underline{Y_1}$ and `y1` in the code.

Then, it combines them in order to build the series impedance matrix $\underline{Z}$ and the shunt admittance matrix
$\underline{Y}$ using the following equations:

```{math}
\begin{aligned}
    \underline{Z} &= \begin{pmatrix}
        \underline{Z_{\mathrm{s}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{m}}} \\
        \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{s}}} & \underline{Z_{\mathrm{m}}} \\
        \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{s}}} \\
    \end{pmatrix}\\
    \underline{Y} &=
    \begin{pmatrix}
        \underline{Y_{\mathrm{s}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{m}}} \\
        \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{s}}} & \underline{Y_{\mathrm{m}}} \\
        \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{s}}} \\
    \end{pmatrix}
\end{aligned}
```

with $\underline{Z_{\mathrm{s}}}$ the series impedance, $\underline{Z_{\mathrm{m}}}$ the mutual impedance,
$\underline{Y_{\mathrm{s}}}$ the series shunt admittance and $\underline{Y_{\mathrm{m}}}$ the mutual shunt admittance
defined by:

```{math}
\begin{aligned}
    \underline{Z_{\mathrm{s}}} &= \dfrac{\underline{Z_0} + 2\underline{Z_1}}{3} \\
    \underline{Z_{\mathrm{m}}} &= \dfrac{\underline{Z_0} - \underline{Z_1}}{3} \\
    \underline{Y_{\mathrm{s}}} &= \dfrac{\underline{Y_0} + 2\underline{Y_1}}{3} \\
    \underline{Y_{\mathrm{m}}} &= \dfrac{\underline{Y_0} - \underline{Y_1}}{3} \\
\end{aligned}
```

This class method also takes optional parameters which are used to add a neutral wire to the previously seen
three-phase matrices. These optional parameters are:

- The neutral impedance (in $\Omega/km$), noted $\underline{Z_{\mathrm{n}}}$ and `zn` in the code.
- The phase-to-neutral reactance (in $\Omega/km$), noted $\underline{X_{p\mathrm{n}}}$ and `xpn` in the code.
- The neutral susceptance (in $S/km$), noted $\underline{B_{\mathrm{n}}}$ and `bn` in the code.
- The phase-to-neutral susceptance (in $S/km$), noted $\underline{B_{p\mathrm{n}}}$ and `bpn` in the code.

```{note}
If any of those parameters is omitted, the neutral wire is omitted and a 3 phase line parameters is built.
If $\underline{Z_{\mathrm{n}}}$ and $\underline{X_{p\mathrm{n}}}$ are zeros, the same happens.
```

In this case, the following matrices are built:

```{math}
\begin{aligned}
    \underline{Z} &= \begin{pmatrix}
        \underline{Z_{\mathrm{s}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{p\mathrm{n}}}\\
        \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{s}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{p\mathrm{n}}}\\
        \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{s}}} & \underline{Z_{p\mathrm{n}}}\\
        \underline{Z_{p\mathrm{n}}} & \underline{Z_{p\mathrm{n}}} & \underline{Z_{p\mathrm{n}}} & \underline{Z_{\mathrm{n}}}\\
    \end{pmatrix}\\
    \underline{Y} &=
    \begin{pmatrix}
        \underline{Y_{\mathrm{s}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{p\mathrm{n}}} \\
        \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{s}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{p\mathrm{n}}} \\
        \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{s}}} & \underline{Y_{p\mathrm{n}}} \\
        \underline{Y_{p\mathrm{n}}} & \underline{Y_{p\mathrm{n}}} & \underline{Y_{p\mathrm{n}}} & \underline{Y_{\mathrm{n}}} \\
    \end{pmatrix}
\end{aligned}
```

with the same $\underline{Z_{\mathrm{s}}}$, $\underline{Z_{\mathrm{m}}}$, $\underline{Y_{\mathrm{s}}}$ and
$\underline{Y_{\mathrm{m}}}$ as before and:

```{math}
\begin{aligned}
    \underline{Z_{p\mathrm{n}}} &= j\underline{X_{p\mathrm{n}}} \\
    \underline{Y_{\mathrm{n}}} &= j\underline{B_{\mathrm{n}}} \\
    \underline{Y_{p\mathrm{n}}} &= j\underline{B_{p\mathrm{n}}}
\end{aligned}
```

respectively the phase-to-neutral series impedance (in $\Omega/km$), the neutral shunt admittance (in $S/km$) and
the phase-to-neutral shunt admittance (in $S/km$).

````{note}
The computed impedance matrix may be non-invertible. In this case, the `from_sym` class method builds impedance and
shunt admittance matrices using the following definitions:

```{math}
\begin{aligned}
    \underline{Z_{\mathrm{s}}} &= \underline{Z_1} \\
    \underline{Z_{\mathrm{m}}} &= 0 \\
    \underline{Y_{\mathrm{s}}} &= \underline{Y_1} \\
    \underline{Y_{\mathrm{m}}} &= 0 \\
\end{aligned}
```
It means that we try to define $\underline{Z_0}=\underline{Z_1}$ and $\underline{Y_0}=\underline{Y_1}$. If this
"degraded" model also leads to a non-invertible impedance matrix, an error is raised.
````

### Examples

```pycon
>>> import numpy as np
... from roseau.load_flow import LineParameters, Q_

>>> # A basic example when z0=z1
... line_parameters = LineParameters.from_sym(
...     "sym_line_example", z0=0.2 + 0.1j, z1=0.2 + 0.1j, y0=0.00014106j, y1=0.00014106j
... )

>>> line_parameters.z_line
array(
    [[ 0.2+0.1j, 0. +0.j , 0. +0.j  ],
     [ 0. +0.j , 0.2+0.1j, 0. +0.j  ],
     [ 0. +0.j , 0. +0.j , 0.2+0.1j ]]
) <Unit('ohm / kilometer')>

>>> line_parameters.y_shunt
array(
    [[ 0.+0.00014106j, 0.+0.j        , 0.+0.j         ],
     [ 0.+0.j        , 0.+0.00014106j, 0.+0.j         ],
     [ 0.+0.j        , 0.+0.j        , 0.+0.00014106j ]]
) <Unit('siemens / kilometer')>


>>> # Simple example in "downgraded" model
... line_parameters = LineParameters.from_sym(
...     "NKBA NOR  25.00 kV", z0=0.0j, z1=1.0 + 1.0j, y0=0.0j, y1=1e-06j
... )
The symmetric model data provided for line type 'NKBA NOR  25.00 kV' produces invalid line impedance matrix... It is
often the case with line models coming from PowerFactory. Trying to handle the data in a 'degraded' line model.

>>> line_parameters.z_line
array(
    [[1.+1.j, 0.+0.j, 0.+0.j],
     [0.+0.j, 1.+1.j, 0.+0.j],
     [0.+0.j, 0.+0.j, 1.+1.j]]
) <Unit('ohm / kilometer')>

>>> line_parameters.y_shunt
array(
    [[0.+1.e-06j, 0.+0.e+00j, 0.+0.e+00j],
     [0.+0.e+00j, 0.+1.e-06j, 0.+0.e+00j],
     [0.+0.e+00j, 0.+0.e+00j, 0.+1.e-06j]]
) <Unit('siemens / kilometer')>


>>> # 4x4 matrix
... line_parameters = LineParameters.from_sym(
...     "sym_neutral_underground_line_example",
...     z0=0.188 + 0.8224j,
...     z1=0.188 + 0.0812j,
...     zn=0.4029 + 0.3522j,
...     xpn=0.2471,
...     y0=0.000010462 + 0.000063134j,
...     y1=0.000010462 + 0.00022999j,
...     bn=0.00011407,
...     bpn=-0.000031502,
... )

>>> line_parameters.z_line
array(
    [[0.188 +0.32826667j, 0.    +0.24706667j, 0.    +0.24706667j, 0.    +0.2471j    ],
     [0.    +0.24706667j, 0.188 +0.32826667j, 0.    +0.24706667j, 0.    +0.2471j    ],
     [0.    +0.24706667j, 0.    +0.24706667j, 0.188 +0.32826667j, 0.    +0.2471j    ],
     [0.    +0.2471j    , 0.    +0.2471j    , 0.    +0.2471j    , 0.4029+0.3522j    ]]
) <Unit('ohm / kilometer')>

>>> line_parameters.y_shunt
array(
    [[ 1.0462e-05+1.74371333e-04j,  0.0000e+00-5.56186667e-05j, 0.0000e+00-5.56186667e-05j, -0.0000e+00-3.15020000e-05j],
     [ 0.0000e+00-5.56186667e-05j,  1.0462e-05+1.74371333e-04j, 0.0000e+00-5.56186667e-05j, -0.0000e+00-3.15020000e-05j],
     [ 0.0000e+00-5.56186667e-05j,  0.0000e+00-5.56186667e-05j, 1.0462e-05+1.74371333e-04j, -0.0000e+00-3.15020000e-05j],
     [-0.0000e+00-3.15020000e-05j, -0.0000e+00-3.15020000e-05j, -0.0000e+00-3.15020000e-05j, 0.0000e+00+1.14070000e-04j]]
) <Unit('siemens / kilometer')>
```
