---
myst:
  html_meta:
    "description lang=en": |
      Define an ideal voltage source and its connection type in Roseau Load Flow - Three-phase unbalanced load flow
      solver in a Python API by Roseau Technologies.
    "description lang=fr": |
      Définir une source de tension idéale et son type de connexion dans Roseau Load Flow - Solveur d'écoulement de
      charge triphasé et déséquilibré dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, source, tension, idéale, connexion, modèle
    "keywords lang=en": simulation, distribution grid, voltage source, ideal, connection, model
---

# Voltage source

## Definition

It represents an ideal voltage source that maintains a fixed voltage independently of the load
resistance or the output current.

## Connections

A voltage source can be either star-connected or delta-connected depending on whether its phases
include a neutral or not.

### Star (wye) connection

The diagram of the star voltage source is:

````{tab} European standards
```{image} /_static/VoltageSource/European_Star_Voltage_Source.svg
:alt: Star voltage source diagram
:width: 400px
:align: center
```
````

````{tab} American standards
```{image} /_static/VoltageSource/American_Star_Voltage_Source.svg
:alt: Star voltage source diagram
:width: 400px
:align: center
```
````

The equations that model a star voltage source are:

```{math}
\left\{
    \begin{split}
        \underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{n}}} &= \underline{U_{\mathrm{an}}} \\
        \underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{n}}} &= \underline{U_{\mathrm{bn}}} \\
        \underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{n}}} &= \underline{U_{\mathrm{cn}}}
    \end{split}
\right.
```

Where $\underline{U}\in\mathbb{C}^3$ is the voltage vector (user defined parameter) and
$\underline{V}\in\mathbb{C}^4$ is the node potentials vector (variable).

```{note}
You can create star connected sources even on buses that don't have a neutral. In this case, the
source's neutral will be floating and its potential can be accessed similar to normal star sources.
```

### Delta connection

The diagram of the delta voltage source is:

````{tab} European standards
```{image} /_static/VoltageSource/European_Delta_Voltage_Source.svg
:alt: Delta voltage source diagram
:width: 400px
:align: center
```
````

````{tab} American standards
```{image} /_static/VoltageSource/American_Delta_Voltage_Source.svg
:alt: Delta voltage source diagram
:width: 400px
:align: center
```
````

The equations that model a delta voltage source are:

```{math}
\left\{
    \begin{split}
        \underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{b}}} &= \underline{U_{\mathrm{ab}}} \\
        \underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{c}}} &= \underline{U_{\mathrm{bc}}} \\
        \underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{a}}} &= \underline{U_{\mathrm{ca}}}
    \end{split}
\right.
```

Where $\underline{U}\in\mathbb{C}^3$ is the voltage vector (user defined parameter) and
$\underline{V}\in\mathbb{C}^3$ is the node potentials vector (variable).

## Usage

A voltage source defined with a neutral phase is a star voltage source, otherwise it is a delta
voltage source. The voltage vector must have the same size as the number of the phase-to-phase
or phase-to-neutral connections of the source.

```python
import numpy as np
import roseau.load_flow as rlf

bus = rlf.Bus(id="bus", phases="abcn")

# Star connection
un = 400 / np.sqrt(3)  # 400V phase-to-phase -> 230V phase-to-neutral
voltages = un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
rlf.VoltageSource(
    id="vs", bus=bus, phases="abcn", voltages=voltages
)  # Voltages are considered phase-to-neutral because phases="abcn"

# Delta connection
un = 400  # 400V phase-to-phase
voltages = un * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
rlf.VoltageSource(
    id="vs", bus=bus, phases="abc", voltages=voltages
)  # Voltages are considered phase-to-phase because phases="abc"

# Incorrect voltage vector
un = 400
voltages = un * np.exp([0, -2j * np.pi / 3])  # Only two elements!!
rlf.VoltageSource(id="vs", bus=bus, phases="abc", voltages=voltages)  # Error
```

## API Reference

```{eval-rst}
.. autoclass:: roseau.load_flow.models.VoltageSource
   :members:
   :show-inheritance:
   :no-index:
```
