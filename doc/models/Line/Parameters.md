---
myst:
  html_meta:
    "description lang=en": |
      Parameters of line models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by
      Roseau Technologies.
    "description lang=fr": |
      Les paramètres des modèles de ligne dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et
      déséquilibré dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, lignes, modèle
    "keywords lang=en": simulation, distribution grid, switch, lines, model
---

(models-line_parameters-alternative_constructors)=

# Parameters

As described [in the previous page](models-line_parameters), a line parameters object contains the
impedance and shunt admittance matrices representing the line model. Sometimes you do not have
these matrices available but you have other data such as symmetric components or geometric
configurations and material types.

This page describes how to build the impedance and shunt admittance matrices and thus the line
parameters object using these alternative data. This is achieved via the alternative constructors
of the `LineParameters` class. Note that only 3-phase lines are supported by the alternative
constructors.

(models-line_parameters-alternative_constructors-symmetric)=

## Symmetric model

### Definition

Line parameters can be built from a symmetric model of the line using the `LineParameters.from_sym`
class method. This method takes the following data:

- The zero sequence of the impedance (in $\Omega$/km), noted $\underline{Z_0}$ and `z0` in the code.
- The direct sequence of the impedance (in $\Omega$/km), noted $\underline{Z_1}$ and `z1` in the code.
- The zero sequence of the admittance (in S/km), noted $\underline{Y_0}$ and `y0` in the code.
- The direct sequence of the admittance (in S/km), noted $\underline{Y_1}$ and `y1` in the code.

The symmetric componenets are then used to build the series impedance matrix $\underline{Z}$ and
the shunt admittance matrix $\underline{Y}$ using the following equations:

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
defined as:

```{math}
\begin{aligned}
    \underline{Z_{\mathrm{s}}} &= \dfrac{\underline{Z_0} + 2\underline{Z_1}}{3} \\
    \underline{Z_{\mathrm{m}}} &= \dfrac{\underline{Z_0} - \underline{Z_1}}{3} \\
    \underline{Y_{\mathrm{s}}} &= \dfrac{\underline{Y_0} + 2\underline{Y_1}}{3} \\
    \underline{Y_{\mathrm{m}}} &= \dfrac{\underline{Y_0} - \underline{Y_1}}{3} \\
\end{aligned}
```

For lines with a neutral, this method also takes the following optional extra parameters:

- The neutral impedance (in $\Omega$/km), noted $\underline{Z_{\mathrm{n}}}$ and `zn` in the code.
- The phase-to-neutral reactance (in $\Omega$/km), noted $\left(\underline{X_{p\mathrm{n}}}\right)_{p\in\{\mathrm{a},
  \mathrm{b},\mathrm{c}\}}$. As these are supposed to be the same, this unique value is noted `xpn` in
  the code.
- The neutral susceptance (in S/km), noted $\underline{B_{\mathrm{n}}}$ and `bn` in the code.
- The phase-to-neutral susceptance (in S/km), noted $\left(\underline{B_{p\mathrm{n}}}\right)_{p\in\{\mathrm{a},
  \mathrm{b},\mathrm{c}\}}$. As these are supposed to be the same, this unique value is noted `bpn` in the code.

```{note}
If any of those parameters is omitted or if $\underline{Z_{\mathrm{n}}}$ and
$\underline{X_{p\mathrm{n}}}$ are zeros, the neutral wire is omitted and a 3-phase line parameters
is built.
```

In this case, the following matrices are built:

```{math}
\begin{aligned}
    \underline{Z} &= \begin{pmatrix}
        \underline{Z_{\mathrm{s}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{an}}}\\
        \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{s}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{p\mathrm{bn}}}\\
        \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{m}}} & \underline{Z_{\mathrm{s}}} & \underline{Z_{\mathrm{cn}}}\\
        \underline{Z_{\mathrm{an}}} & \underline{Z_{\mathrm{bn}}} & \underline{Z_{\mathrm{cn}}} & \underline{Z_{\mathrm{n}}}\\
    \end{pmatrix}\\
    \underline{Y} &=
    \begin{pmatrix}
        \underline{Y_{\mathrm{s}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{an}}} \\
        \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{s}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{bn}}} \\
        \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{m}}} & \underline{Y_{\mathrm{s}}} & \underline{Y_{\mathrm{cn}}} \\
        \underline{Y_{\mathrm{an}}} & \underline{Y_{\mathrm{bn}}} & \underline{Y_{\mathrm{cn}}} & \underline{Y_{\mathrm{n}}} \\
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

respectively the phase-to-neutral series impedance (in $\Omega$/km), the neutral shunt admittance (in S/km) and
the phase-to-neutral shunt admittance (in S/km).

````{note}
If the computed impedance matrix is be non-invertible, the `from_sym` class method builds impedance
and shunt admittance matrices using the following definitions:

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

## Geometric model

### Definition

The `LineParameters` class has a class method called `from_geometry` which builds impedance and shunt admittance
matrices from dimensions and materials used for the insulator and the conductors. Two geometric configurations are
proposed: the first one is for a twisted line and the second is for an underground line. Both of them include a
neutral wire.

This class method accepts the following arguments:

- the line type to choose between the twisted and the underground options.
- the conductor type which defines the material of the conductors.
- the insulator type which is the material used as insulator.
- the section of the phase wires (in mm²). The sections of the wires of the three phases are considered equal.
- the section of the neutral wire (in mm²).
- the height of the line above or below the ground (in meters).
- the external diameter of the wire (in meters).

#### Resistance

The resistances of the conductors are computed using the following formula:

```{math}
R_{p}=\frac{\rho}{S_{p}}\quad\forall p\in\{\mathrm{a},\mathrm{b},\mathrm{c},\mathrm{n}\} \qquad(\text{in }
\Omega\text{/km})
```

where:

- $\left(S_p\right)_{p\in\{\mathrm{a},\mathrm{b},\mathrm{c}\}}$ are the (equal) sections of the phase conductors;
- $S_{\mathrm{n}}$ the section of the neutral conductor;
- $\rho$ the resistivity of the conductor material (the same for the phases and for the neutral).

The following resistivities are used by _Roseau Load Flow_:

| Material                   | Resistivity ($\Omega$m) |
| :------------------------- | :---------------------- |
| Copper -- Fr: Cuivre       | $1.72\times10^{-8}$     |
| Aluminum -- Fr: Aluminium  | $2.82\times10^{-8}$     |
| Al-Mg Alloy -- Fr: Almélec | $3.26\times10^{-8}$     |
| ACSR -- Fr: Alu-Acier      | $4.0587\times10^{-8}$   |
| AACSR -- Fr: Almélec-Acier | $3.26\times10^{-8}$     |

These values are defined in the `utils` module: {data}`roseau.load_flow.utils.constants.RHO`.

#### Inductance

The inductance matrix in Henry/km is computed using the following formula:

```{math}
L=
\begin{pmatrix}
    L_{\mathrm{a}} & M_{\mathrm{ab}} & M_{\mathrm{ac}} & M_{\mathrm{an}}\\
    M_{\mathrm{ba}} & L_{\mathrm{b}} & M_{\mathrm{bc}} & M_{\mathrm{bn}}\\
    M_{\mathrm{ca}} & M_{\mathrm{cb}} & L_{\mathrm{c}} & M_{\mathrm{cn}}\\
    M_{\mathrm{na}} & M_{\mathrm{nb}} & M_{\mathrm{nc}} & L_{\mathrm{n}}\\
\end{pmatrix}
```

where for $(i,j)\in \{\mathrm{a}, \mathrm{b}, \mathrm{c}, \mathrm{n}\}^2$

```{math}
\begin{aligned}
    L_i&=\dfrac{\mu_0}{2\pi} \ln\left(\frac{D_0}{GMR_{i}}\right) \\
    M_{ij}&=\dfrac{\mu_0}{2\pi} \ln\left(\frac{D_0}{D_{ij}}\right) \\
\end{aligned}
```

where:

- $\mu_0$ is the vacuum magnetic permeability (H/m);
- $D_0$ an arbitrary distance taken equal to 1 meter;
- $D_{ij}$ the distances between the center of the conductor $i$ and the center of the conductor $j$
- $GMR_i$ the _geometric mean radius_ of the conductor $i$.

The vacuum magnetic permeability is defined in the `utils` module {data}`roseau.load_flow.utils.constants.MU_0`.

The geometric mean radius is defined for all $i\in \{\mathrm{a}, \mathrm{b}, \mathrm{c}, \mathrm{n}\}$ as

```{math}
GMR_i=R_i\exp\left(-\dfrac{1}{4}\right)\quad \text{(in m)}
```

```{note}
When the geometric mean radius is computed, the radius must be taken in meters!
```

#### Capacitance

In order to compute the capacitances of the line, the $(\lambda_{ij})_{(i,j)\in\{\mathrm{a},\mathrm{b},\mathrm{c},
\mathrm{n}\}^2}$ matrix of potential coefficients is built. Those coefficients were first introduced by Maxwell in 1873
({cite:p}`Maxwell_1873` page 89).

```{math}
\begin{aligned}
    \lambda_{ij}&= \dfrac{1}{2\pi\varepsilon}\ln\left(\dfrac{D'_{ij}}{D_{ij}}\right) \quad\text{if } i\neq j\\
    \lambda_{ii}&= \dfrac{1}{2\pi\varepsilon}\ln\left(\dfrac{D'_{i}}{R_i}\right) \quad\text{otherwise}\\
\end{aligned}
```

where:

- $\varepsilon$ is the permittivity of the insulator in F/m;
- $D_{ij}$ the distance between the center of the conductor $i$ and the conductor $j$;
- $R_i$ the radius of the conductor $i$;
- $D'_i$ the distance between the conductor $i$ and its image with respect to the ground;
- $D'_{ij}$ the distance between the conductor $i$ and the image of the conductor $j$ with respect to the ground.

The method of images ({cite:p}`wiki:Method_Of_Image_Charges`) is depicted in the following figure. It indicates how
to compute the distances based on the position of wires.

````{tab} Planar ground
```{image} /_static/Line/Image_Method_Plane.svg
:alt: Image method for a planar ground
:width: 400px
:align: center
```
````

````{tab} Circular ground
```{image} /_static/Line/Image_Method_Circle.svg
:alt: Image method for a circular ground
:width: 400px
:align: center
```
````

The permittivity of the insulator $\varepsilon$ (in F/m) is defined as $\varepsilon_0\varepsilon_{\mathrm{r}}$ with
$\varepsilon_0$ the permittivity of the vacuum (in F/m) and $\varepsilon_{\mathrm{r}}$ the relative
permittivity of the insulator (no unit). These values are defined in the `utils` module
[](#roseau.load_flow.utils.constants.EPSILON_0) and [](#roseau.load_flow.utils.constants.EPSILON_R).

The capacitance matrix $C$ is then defined by:

```{math}
C=
\begin{pmatrix}
    C_{\mathrm{a}} & C_{\mathrm{ab}} & C_{\mathrm{ac}} & C_{\mathrm{an}}\\
    C_{\mathrm{ab}} & C_{\mathrm{b}} & C_{\mathrm{bc}} & C_{\mathrm{bn}}\\
    C_{\mathrm{ac}} & C_{\mathrm{bc}} & C_{\mathrm{c}} & C_{\mathrm{cn}}\\
    C_{\mathrm{an}} & C_{\mathrm{bn}} & C_{\mathrm{cn}} & C_{\mathrm{n}}
\end{pmatrix}
=\lambda^{-1} \quad\text{in F/km}
```

#### Conductance

The conductance matrix $G$ (in S/km) is defined by:

```{math}
G=
\begin{pmatrix}
    G_{\mathrm{a}} & 0 & 0 & 0\\
    0 & G_{\mathrm{b}} & 0 & 0\\
    0 & 0 & G_{\mathrm{c}} & 0\\
    0 & 0 & 0 & G_{\mathrm{n}}
\end{pmatrix}
```

where $G_i=C_i\omega\tan\delta$ for all $i\in\{\mathrm{a},\mathrm{b},\mathrm{c},\mathrm{n}\}$.

$\tan\delta$ is the loss tangent and is taken from this table:

| Insulator                        | Loss tangent $\tan\delta$ |
| :------------------------------- | :------------------------ |
| PolyVinyl Chloride (PVC)         | $600\times10^{-4}$        |
| High-Density PolyEthylene (HDPE) | $6\times10^{-4}$          |
| Low-Density PolyEthylene (LDPE)  | $6\times10^{-4}$          |
| Cross-linked polyethylene (PEX)  | $30\times10^{-4}$         |
| Ethylene-Propylene Rubber (EPR)  | $125\times10^{-4}$        |

These values are defined in the `utils` module: [](#roseau.load_flow.utils.constants.TAN_D).

Finally, the impedance matrix and the admittance matrix can be computed.

```{math}
\begin{aligned}
    \underline{Z} &= R + j\omega L \\
    \underline{y} &= G + j\omega C \\
\end{aligned}
```

```{warning}
The admittance matrix $\underline{y}$ shouldn't be confused with the shunt admittance matrix
$\underline{Y}$ defined [here](models-line-shunt-admittance-matrix).
```

```{note}
The frequency used to compute $\omega$ is 50 Hz.
```

### Twisted line

The following configuration of the wires is supposed:

```{image} /_static/Line/Twisted_Geometry.svg
:alt: Twisted model geometry
:width: 600px
:align: center
```

Here is the details of the parameters used:

```{image} /_static/Line/Twisted_Geometry_Details.svg
:alt: Twisted model geometry details
:width: 600px
:align: center
```

In this configuration, the phase conductors are around the neutral conductor, separated by $\dfrac{2\pi}{3}$ angles
and located at the distance $\dfrac{d_{\mathrm{ext}}}{4}$ from the center of the neutral conductor. Phases and
neutral are separated by the insulator and air. The height distance $h$ is the distance between the center of the
neutral conductor and the ground.

From these figures, the following geometric positions can be deduced:

```{math}
\begin{aligned}
    (x_{\mathrm{a}}, y_{\mathrm{a}}) &= \left(\dfrac{-\sqrt{3}}{8}\cdot d_{\mathrm{ext}},h+\dfrac{d_{\mathrm{ext}}}{8}\right)\\
    (x_{\mathrm{b}}, y_{\mathrm{b}}) &= \left(\dfrac{\sqrt{3}}{8}\cdot d_{\mathrm{ext}},h+\dfrac{d_{\mathrm{ext}}}{8}\right)\\
    (x_{\mathrm{c}}, y_{\mathrm{c}}) &= \left(0,h-\dfrac{d_{\mathrm{ext}}}{4}\right)\\
    (x_{\mathrm{n}}, y_{\mathrm{n}}) &= (0, h)\\
    (x_{\mathrm{a}}', y_{\mathrm{a}}') &= (x_{\mathrm{a}}, -y_{\mathrm{a}})\\
    (x_{\mathrm{b}}', y_{\mathrm{b}}') &= (x_{\mathrm{b}}, -y_{\mathrm{b}})\\
    (x_{\mathrm{c}}', y_{\mathrm{c}}') &= (x_{\mathrm{c}}, -y_{\mathrm{c}})\\
    (x_{\mathrm{n}}', y_{\mathrm{n}}') &= (x_{\mathrm{n}}, -y_{\mathrm{n}})\\
\end{aligned}
```

The position $(x_{\mathrm{a}}, y_{\mathrm{a}})$ are the position of the point $A$, $(x_{\mathrm{b}}, y_{\mathrm{b}})$
the point $B$, etc. The prime positions are the positions of the images of the conductor with respect to the ground.

The formulas of the previous sections are used to get the impedance and shunt admittances matrices.

```pycon
>>> from roseau.load_flow import LineParameters, Q_, LineType, ConductorType, InsulatorType

>>> # A twisted line example
... line_parameters = LineParameters.from_geometry(
...     "twisted_example",
...     line_type=LineType.TWISTED,
...     conductor_type=ConductorType.AL,
...     insulator_type=InsulatorType.PEX,
...     section=150,  # mm²
...     section_neutral=70,  # mm²
...     height=10,  # m
...     external_diameter=Q_(4, "cm"),
... )

>>> line_parameters.z_line
array(
    [[0.188     +0.32828403j, 0.        +0.25483745j, 0.        +0.25483745j, 0.        +0.28935138j],
     [0.        +0.25483745j, 0.188     +0.32828403j, 0.        +0.25483745j, 0.        +0.28935138j],
     [0.        +0.25483745j, 0.        +0.25483745j, 0.188     +0.32828403j, 0.        +0.28935138j],
     [0.        +0.28935138j, 0.        +0.28935138j, 0.        +0.28935138j, 0.40285714+0.35222736j]]
) <Unit('ohm / kilometer')>

>>> line_parameters.y_shunt.to("uS/km")
array(
    [[0.09883654 +48.82465468j, 0.          -1.92652134j, 0.          -1.92555213j, 0.         -12.02706891j],
     [0.          -1.92652134j, 0.09883654 +48.82465468j, 0.          -1.92555213j, 0.         -12.02706891j],
     [0.          -1.92555213j, 0.          -1.92555213j, 0.09884227 +48.82653968j, 0.         -12.02801059j],
     [0.         -12.02706891j, 0.         -12.02706891j, 0.         -12.02801059j, 0.21303236+107.09293474j]]
) <Unit('microsiemens / kilometer')>)
```

### Underground line

The following configuration of the wires is supposed:

```{image} /_static/Line/Underground_Geometry.svg
:alt: Underground model geometry
:width: 600px
:align: center
```

Here is the details of the parameters used:

```{image} /_static/Line/Underground_Geometry_Details.svg
:alt: Underground model geometry details
:width: 600px
:align: center
```

In this configuration, the conductors are separated by $\dfrac{\pi}{2}$ angles
and located at the distance $\dfrac{d_{\mathrm{ext}}}{4}$ from the center of the wire. Phases and
neutral are separated by the insulator. The height distance $h$ is the distance between the center of the
wire and the ground.

From these figures, the following geometric positions can be deduced:

```{math}
\begin{aligned}
    (x_{\mathrm{a}}, y_{\mathrm{a}}) &= \left(-\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}},h-\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}}\right)\\
    (x_{\mathrm{b}}, y_{\mathrm{b}}) &= \left(\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}},h-\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}}\right)\\
    (x_{\mathrm{c}}, y_{\mathrm{c}}) &= \left(\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}},h+\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}}\right)\\
    (x_{\mathrm{n}}, y_{\mathrm{n}}) &= \left(-\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}},h+\dfrac{\sqrt{2}}{8}d_{\mathrm{ext}}\right)\\
    (x_{\mathrm{a}}', y_{\mathrm{a}}') &= \left(-\dfrac{3\sqrt{2}}{8}d_{\mathrm{ext}},h-\dfrac{3\sqrt{2}}{8} d_{\mathrm{ext}}\right)\\
    (x_{\mathrm{b}}', y_{\mathrm{b}}') &= \left(\dfrac{3\sqrt{2}}{8}d_{\mathrm{ext}},h-\dfrac{3\sqrt{2}}{8}d_
    {\mathrm{ext}}\right)\\
    (x_{\mathrm{c}}', y_{\mathrm{c}}') &= \left(\dfrac{3\sqrt{2}}{8} d_{\mathrm{ext}},h+\dfrac{3\sqrt{2}}{8} d_
    {\mathrm{ext}}\right)\\
    (x_{\mathrm{n}}', y_{\mathrm{n}}') &= \left(-\dfrac{3\sqrt{2}}{8} d_{\mathrm{ext}},h+\dfrac{3\sqrt{2}}{8} d_
    {\mathrm{ext}}\right)\\
\end{aligned}
```

The position $(x_{\mathrm{a}}, y_{\mathrm{a}})$ are the position of the point $A$, $(x_{\mathrm{b}}, y_{\mathrm{b}})$
the point $B$, etc. The prime positions are the positions of the images of the conductor with respect to the ground.

The formulas of the previous sections are used to get the impedance and shunt admittances matrices.

```{note}
Please note that for underground lines, the provided height $h$ must be negative as shown in the example below.
```

```pycon
>>> from roseau.load_flow import LineParameters, Q_, LineType, ConductorType, InsulatorType

>>> # An underground line example
... line_parameters = LineParameters.from_geometry(
...     "underground_example",
...     line_type=LineType.UNDERGROUND,
...     conductor_type=ConductorType.AL,
...     insulator_type=InsulatorType.PVC,
...     section=150, #mm²
...     section_neutral=70, #mm²
...     height=-1.5, # m # Underground so negative!
...     external_diameter=0.049, #m
... )

>>> line_parameters.z_line
array(
    [[0.188     +0.32828403j, 0.        +0.25482437j, 0.        +0.23304851j, 0.        +0.25482437j],
     [0.        +0.25482437j, 0.188     +0.32828403j, 0.        +0.25482437j, 0.        +0.23304851j],
     [0.        +0.23304851j, 0.        +0.25482437j, 0.188     +0.32828403j, 0.        +0.25482437j],
     [0.        +0.25482437j, 0.        +0.23304851j, 0.        +0.25482437j, 0.40285714+0.35222736j]]
) <Unit('ohm / kilometer')>

>>> line_parameters.y_shunt.to("uS/km")
array(
    [[19.06271927+458.27618628j,  0.         -74.71708551j,  0.         -20.98651877j,  0.         -44.86059415j],
     [ 0.         -74.71708551j, 20.61057729+499.04239152j,  0.         -74.71708551j,  0.          -6.09859898j],
     [ 0.         -20.98651877j,  0.         -74.71708551j, 19.06271927+458.27618628j,  0.         -44.86059415j],
     [ 0.         -44.86059415j,  0.          -6.09859898j,  0.         -44.86059415j, 12.66715195+306.9389864j ]]
) <Unit('microsiemens / kilometer')>
```

## Bibliography

```{bibliography}
:filter: docname in docnames
```
