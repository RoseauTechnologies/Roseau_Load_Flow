---
myst:
  html_meta:
    description lang=en: |
      Line models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau Technologies.
    keywords lang=en: simulation, distribution grid, power line, electric line, lines, model
    # spellchecker:off
    description lang=fr: |
      Les modèles de ligne dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une
      API Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, bus, roseau load flow, lignes, modèle
# spellchecker:on
---

# Lines

## Definition

Lines are modeled using passive components lumped in a PI section. The lumped parameters are defined using the series
impedance matrix $\underline{Z}$ and the shunt admittance matrix $\underline{Y}$.

## Matrices definition

Before diving into the different line models, lets define the series impedance matrix $\underline{Z}$, and the shunt
admittance matrix $\underline{Y}$ used to model the lines.

### Series impedance matrix

The series impedance matrix $\underline{Z}$, in $\Omega$, consists of the series resistance of the conductors
($R\in{\mathbb{R}^+}^4$), the self-inductances ($L\in\mathbb{R}^4$) and the mutual inductances ($M\in\mathbb{R}^{12}$).

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

$\underline{y}$ represents the admittances between each node, while $\underline{Y}$ is used to compute the currents and
voltages.

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

(models-line-shunt-admittance-matrix)=

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

(models-line_parameters)=

## Line parameters

The parameters of the lines are defined using the `LineParameters` class. It takes the series impedance matrix
$\underline{Z}$ and optionally, the shunt admittance matrix $\underline{Y}$. The first one must be given in $\Omega$/km
(or an equivalent unit) and the second must be given in $S/km$ (or an equivalent unit).

```python
import numpy as np
import roseau.load_flow as rlf

# An impedance matrix
z_line = rlf.Q_(
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
y_shunt = rlf.Q_(
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
simple_line_parameters = rlf.LineParameters(id="simple_line_parameters", z_line=z_line)

# The line parameter for a line with a shunt
shunt_line_parameters = rlf.LineParameters(
    id="shunt_line_parameters", z_line=z_line, y_shunt=y_shunt
)
```

```{tip}
The `Line` instance itself has the `z_line` and `y_shunt` properties. They retrieve the line impedance in $\Omega$
and the line shunt admittance in Siemens (taking into account the length of the line).
```

There are several alternative constructors for `LineParameters` objects. The description of them can be found in the
dedicated [Line parameters page](Parameters.md).

## Available Results

The following results are available for all lines:

| Result Accessor           | Default Unit  | Type             | Description                                                                                    |
| ------------------------- | ------------- | ---------------- | ---------------------------------------------------------------------------------------------- |
| `res_potentials`⭑         | $V$           | 2 complex arrays | The potentials of each phase of the line                                                       |
| `res_currents`⭑           | $A$           | 2 complex arrays | The currents flowing into each phase of the line                                               |
| `res_powers`⭑             | $V\!A$        | 2 complex arrays | The powers flowing into each phase of the line                                                 |
| `res_voltages`⭑           | $V$           | 2 complex arrays | The phase-to-neutral voltages if the line has a neutral, the phase-to-phase voltages otherwise |
| `res_series_currents`     | $A$           | complex array    | The currents flowing in the series impedance of each phase of the line from bus 1 to bus 2     |
| `res_power_losses`        | $V\!A$        | complex array    | The total power losses in each phase of the line                                               |
| `res_series_power_losses` | $V\!A$        | complex array    | The power losses in the series impedance of each phase of the line                             |
| `res_loading`             | $\mathrm{pu}$ | number array     | The loading of each phase of the line compared to its ampacity                                 |
| `res_violated`            | -             | boolean array    | Indicates if the loading of each phase exceeds the maximal loading                             |

Lines with shunt components also have the following results:

| Result Accessor          | Default Unit | Type             | Description                                                 |
| ------------------------ | ------------ | ---------------- | ----------------------------------------------------------- |
| `res_shunt_currents`⭑    | $A$          | 2 complex arrays | The currents flowing into the shunt admittances of the line |
| `res_shunt_power_losses` | $V\!A$       | complex array    | The power losses in the shunt admittances of the line       |
| `res_ground_potential`   | $V$          | complex          | The potential of the ground element connected to the line   |

```{note}
The result accessors marked with ⭑ contain tuples for the results of the first and second sides of
the line. These are the old accessors to the results of the sides of the line. They may be deprecated
in the future. The new interface is to use `<side>.res_*` presented below.
```

Additionally, the following results are available on each side of the line accessible with `<side>.` prefix where
`<side>` is either `side1` or `side2`:

| Result Accessor         | Default Unit | Type          | Description                                                                                                 |
| ----------------------- | ------------ | ------------- | ----------------------------------------------------------------------------------------------------------- |
| `<side>.res_potentials` | $V$          | complex array | The potentials of each phase of the corresponding line side                                                 |
| `<side>.res_currents`   | $A$          | complex array | The currents flowing **into** each phase of the corresponding line side                                     |
| `<side>.res_powers`     | $V\!A$       | complex array | The powers flowing **into** each phase of the corresponding line side                                       |
| `<side>.res_voltages`   | $V$          | complex array | The voltages of the corresponding line side: phase-to-neutral if it has a neutral, phase-to-phase otherwise |

And the following results are available for lines _with shunt components_:

| Result Accessor             | Default Unit | Type          | Description                                                                    |
| --------------------------- | ------------ | ------------- | ------------------------------------------------------------------------------ |
| `<side>.res_shunt_currents` | $A$          | complex array | The currents flowing into the shunt admittances of the corresponding line side |
| `<side>.res_shunt_losses`   | $V\!A$       | complex array | The losses in the shunt admittances of the corresponding line side             |

And the following results are available for lines _with a neutral and at least one phase_:

| Result Accessor                | Default Unit  | Type          | Description                                                                                          |
| ------------------------------ | ------------- | ------------- | ---------------------------------------------------------------------------------------------------- |
| `<side>.res_voltages_pn`       | $V$           | complex array | The phase-to-neutral voltages of the corresponding line side                                         |
| `<side>.res_voltage_levels_pn` | $\mathrm{pu}$ | number array  | The voltage levels of each phase of the corresponding line side ($\sqrt{3} V_{pn} / V_\mathrm{nom}$) |

And the following results are available for lines _with more than one phase_:

| Result Accessor                | Default Unit  | Type          | Description                                                                                 |
| ------------------------------ | ------------- | ------------- | ------------------------------------------------------------------------------------------- |
| `<side>.res_voltages_pp`       | $V$           | complex array | The phase-to-phase voltages of the corresponding line side                                  |
| `<side>.res_voltage_levels_pp` | $\mathrm{pu}$ | number array  | The voltage levels of each phase of the corresponding line side ($V_{pp} / V_\mathrm{nom}$) |

And the following results are available for _three-phase_ lines:

| Result Accessor                  | Default Unit | Type   | Description                                                                                        |
| -------------------------------- | ------------ | ------ | -------------------------------------------------------------------------------------------------- |
| `<side>.res_voltage_unbalance()` | $\%$         | number | The voltage unbalance of the corresponding line side according to the IEC, IEEE or NEMA definition |
| `<side>.res_current_unbalance()` | $\%$         | number | The Current Unbalance Factor (CUF) of the line side                                                |

## Available models

The following line models are available in _Roseau Load Flow_. Please also have a look at the parameters page to define
the parameters of lines.

```{toctree}
---
maxdepth: 2
caption: Lines
---
Parameters
ShuntLine
SimplifiedLine
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.LineParameters
   :members:
   :show-inheritance:
   :no-index:
.. autoapiclass:: roseau.load_flow.models.Line
   :members:
   :show-inheritance:
   :no-index:
```
