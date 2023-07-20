# Lines

Lines are modeled using passive components lumped in a PI section. The lumped parameters are
defined using the series impedance matrix $\underline{Z}$ and the shunt admittance matrix
$\underline{Y}$.

## Matrices definition

Before diving into the different line models, lets define the series impedance matrix $Z$, and the
shunt admittance matrix $Y$ used to model the lines.

### Series impedance matrix

The series impedance matrix $\underline{Z}$, in $\Omega$, consists of the series resistance of the
conductors ($R\in{\mathbb{R}^+}^4$), the self-inductances ($L\in\mathbb{R}^4$) and the mutual
inductances ($M\in\mathbb{R}^{12}$).

```{math}
\begin{aligned}
    \underline{Z} &= R + j \cdot X \\
    \underline{Z} &= \begin{pmatrix}
        \underline{Z_{\mathrm{aa}}} & \underline{Z_{\mathrm{ab}}} & \underline{Z_{\mathrm{ac}}} & \underline{Z_{\mathrm{an}}}\\
        \underline{Z_{\mathrm{ba}}} & \underline{Z_{\mathrm{bb}}} & \underline{Z_{\mathrm{bc}}} & \underline{Z_{\mathrm{bn}}}\\
        \underline{Z_{\mathrm{ca}}} & \underline{Z_{\mathrm{cb}}} & \underline{Z_{\mathrm{cc}}} & \underline{Z_{\mathrm{cn}}}\\
        \underline{Z_{\mathrm{na}}} & \underline{Z_{\mathrm{nb}}} & \underline{Z_{\mathrm{nc}}} & \underline{Z_{\mathrm{nn}}}\\
    \end{pmatrix}\\
    \underline{Z} &= \underbrace{
        \begin{pmatrix}
            R_{\mathrm{a}} & 0 & 0 & 0\\
            0 & R_{\mathrm{b}} & 0 & 0\\
            0 & 0 & R_{\mathrm{c}} & 0\\
            0 & 0 & 0 & R_{\mathrm{n}}\\
        \end{pmatrix}
    }_{R} + j \cdot \underbrace{
        \omega \cdot
        \begin{pmatrix}
            L_{\mathrm{a}} & M_{\mathrm{ab}} & M_{\mathrm{ac}} & M_{\mathrm{an}}\\
            M_{\mathrm{ba}} & L_{\mathrm{b}} & M_{\mathrm{bc}} & M_{\mathrm{bn}}\\
            M_{\mathrm{ca}} & M_{\mathrm{cb}} & L_{\mathrm{c}} & M_{\mathrm{cn}}\\
            M_{\mathrm{na}} & M_{\mathrm{nb}} & M_{\mathrm{nc}} & L_{\mathrm{n}}\\
        \end{pmatrix}
    }_{X}
\end{aligned}
```

### Admittance matrix

```{warning}
The admittance matrix $\underline{y}$ shouldn't be confused with the shunt admittance matrix
$\underline{Y}$ defined below.
```

$\underline{y}$ represents the admittances between each node, while $\underline{Y}$ is used to
compute the currents and voltages.

```{math}
\begin{aligned}
    \underline{y} &= G + j \cdot B \\
    \underline{y} &= \begin{pmatrix}
        \underline{y_{\mathrm{ag}}} & \underline{y_{\mathrm{ab}}} & \underline{y_{\mathrm{ac}}} & \underline{y_{\mathrm{an}}}\\
        \underline{y_{\mathrm{ab}}} & \underline{y_{\mathrm{bg}}} & \underline{y_{\mathrm{bc}}} & \underline{y_{\mathrm{bn}}}\\
        \underline{y_{\mathrm{ac}}} & \underline{y_{\mathrm{bc}}} & \underline{y_{\mathrm{cg}}} & \underline{y_{\mathrm{cn}}}\\
        \underline{y_{\mathrm{an}}} & \underline{y_{\mathrm{bn}}} & \underline{y_{\mathrm{cn}}} & \underline{y_{\mathrm{ng}}}
    \end{pmatrix}\\
    \underline{y} &= \underbrace{
        \begin{pmatrix}
            G_{\mathrm{a}} & 0 & 0 & 0\\
            0 & G_{\mathrm{b}} & 0 & 0\\
            0 & 0 & G_{\mathrm{c}} & 0\\
            0 & 0 & 0 & G_{\mathrm{n}}
        \end{pmatrix}
    }_{G} + j \cdot \underbrace{
        \omega \cdot
        \begin{pmatrix}
          C_{\mathrm{a}} & C_{\mathrm{ab}} & C_{\mathrm{ac}} & C_{\mathrm{an}}\\
          C_{\mathrm{ab}} & C_{\mathrm{b}} & C_{\mathrm{bc}} & C_{\mathrm{bn}}\\
          C_{\mathrm{ac}} & C_{\mathrm{bc}} & C_{\mathrm{c}} & C_{\mathrm{cn}}\\
          C_{\mathrm{an}} & C_{\mathrm{bn}} & C_{\mathrm{cn}} & C_{\mathrm{n}}
        \end{pmatrix}
    }_{B}
\end{aligned}
```

with $G\in\mathbb{R}^4$ the conductance of the line, $B\in\mathbb{R}^4$ the susceptance of the line and
$C\in\mathbb{R}^{16}$ the transverse susceptances of the line.

### Shunt admittance matrix

The shunt admittance matrix $\underline{Y}$ is defined from the admittance matrix $\underline{y}$ as:

```{math}
\underline{Y} =
\begin{pmatrix}
  \underline{Y_{\mathrm{aa}}} & \underline{Y_{\mathrm{ab}}} & \underline{Y_{\mathrm{ac}}} & \underline{Y_{\mathrm{an}}}\\
  \underline{Y_{\mathrm{ba}}} & \underline{Y_{\mathrm{bb}}} & \underline{Y_{\mathrm{bc}}} & \underline{Y_{\mathrm{bn}}}\\
  \underline{Y_{\mathrm{ca}}} & \underline{Y_{\mathrm{cb}}} & \underline{Y_{\mathrm{cc}}} & \underline{Y_{\mathrm{cn}}}\\
  \underline{Y_{\mathrm{na}}} & \underline{Y_{\mathrm{nb}}} & \underline{Y_{\mathrm{nc}}} & \underline{Y_{\mathrm{nn}}}\\
\end{pmatrix}
\quad \text{with} \quad
\left\{
  \begin{aligned}
    \underline{Y_{ii}} &= \sum_{k\in\{\mathrm{a},\mathrm{b},\mathrm{c},\mathrm{n},\mathrm{g}\}}{\underline{y_{ik}}}\\
    \underline{Y_{ij}} &= -\underline{y_{ij}}\\
  \end{aligned}
\right.\text{, }\forall(i,j)\in\{\mathrm{a},\mathrm{b},\mathrm{c},\mathrm{n}\}^2
```

## Line parameters

The parameters of the lines are defined using the `LineParameters` class. It takes the series
impedance matrix $\underline{Z}$ and optionally, the shunt admittance matrix $\underline{Y}$. The
first one must be given in $\Omega/km$ (or an equivalent unit) and the second must be given in
$S/km$ (or an equivalent unit).

```python
import numpy as np

from roseau.load_flow import LineParameters, Q_

# An impedance matrix
z_line = Q_(
    np.array(
        [
            [0.3 + 0.35j, 0.25j, 0.25j, 0.25j],
            [0.25j, 0.3 + 0.35j, 0.25j, 0.25j],
            [0.25j, 0.25j, 0.3 + 0.35j, 0.25j],
            [0.25j, 0.25j, 0.25j, 0.3 + 0.35j],
        ]
    ),
    "ohm/km",
)

# A shunt admittance matrix
y_shunt = Q_(
    np.array(
        [
            [20 + 475j, -68j, -10j, -68j],
            [-68j, 20 + 475j, -68j, -10j],
            [-10j, -68j, 20 + 475j, -68j],
            [-68j, -10j, -68j, 20 + 475j],
        ]
    ),
    "uS/km",  # micro Siemens per kilometer
)

# The line parameter for a simple line (no shunt)
simple_line_parameters = LineParameters(id="simple_line_parameters", z_line=z_line)

# The line parameter for a line with a shunt
shunt_line_parameters = LineParameters(
    id="shunt_line_parameters", z_line=z_line, y_shunt=y_shunt
)
```

## Available models

The following line models are available in *Roseau Load Flow*:

```{toctree}
---
maxdepth: 2
caption: Lines
---
ShuntLine
SimplifiedLine
```
