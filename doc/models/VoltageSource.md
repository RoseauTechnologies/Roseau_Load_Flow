---
myst:
  html_meta:
    description lang=en: |
      Define an ideal voltage source and its connection type in Roseau Load Flow - Three-phase unbalanced load flow
      solver in a Python API by Roseau Technologies.
    keywords lang=en: simulation, distribution grid, voltage source, ideal, connection, model
    # spellchecker:off
    description lang=fr: |
      Définir une source de tension idéale et son type de connexion dans Roseau Load Flow - Solveur d'écoulement de
      charge triphasé et déséquilibré dans une API Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, source, tension, idéale, connexion, modèle
    # spellchecker:on
---

# Voltage source

## Definition

It represents an ideal voltage source that maintains a fixed voltage independently of the load resistance or the output
current.

## Connections

A voltage source can be either star-connected or delta-connected depending on whether its phases include a neutral or
not.

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

Where $\underline{U}\in\mathbb{C}^3$ is the voltage vector (user defined parameter) and $\underline{V}\in\mathbb{C}^4$
is the node potentials vector (variable).

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

Where $\underline{U}\in\mathbb{C}^3$ is the voltage vector (user defined parameter) and $\underline{V}\in\mathbb{C}^3$
is the node potentials vector (variable).

## Available Results

The following results are available for all sources:

| Result Accessor  | Default Unit | Type          | Description                                                                                      |
| ---------------- | ------------ | ------------- | ------------------------------------------------------------------------------------------------ |
| `res_potentials` | $V$          | complex array | The potentials of each phase of the source                                                       |
| `res_currents`   | $A$          | complex array | The line currents flowing into each phase of the source                                          |
| `res_powers`     | $V\!A$       | complex array | The line powers flowing into each phase of the source                                            |
| `res_voltages`   | $V$          | complex array | The phase-to-neutral voltages if the source has a neutral, the phase-to-phase voltages otherwise |

Additionally, the following results are available for sources with a neutral:

| Result Accessor   | Default Unit | Type          | Description                                 |
| ----------------- | ------------ | ------------- | ------------------------------------------- |
| `res_voltages_pn` | $V$          | complex array | The phase-to-neutral voltages of the source |

And the following results are available for sources with more than one phase:

| Result Accessor   | Default Unit | Type          | Description                               |
| ----------------- | ------------ | ------------- | ----------------------------------------- |
| `res_voltages_pp` | $V$          | complex array | The phase-to-phase voltages of the source |

And the following results are available for _three-phase_ sources:

| Result Accessor           | Default Unit | Type   | Description                                                                       |
| ------------------------- | ------------ | ------ | --------------------------------------------------------------------------------- |
| `res_voltage_unbalance()` | $\%$         | number | The voltage unbalance of the source according to the IEC, IEEE or NEMA definition |
| `res_current_unbalance()` | $\%$         | number | The Current Unbalance Factor of the source (CUF)                                  |

(models-voltage-source-usage)=

## Usage

A voltage source defined with a neutral phase is a star-connected voltage source, otherwise it is a delta-connected
voltage source. The phases of the source must be a subset of the phases of the bus it is connected to. A voltage source
takes the same phases as the bus by default.

```python
import numpy as np
import roseau.load_flow as rlf

bus = rlf.Bus(id="bus", phases="abcn")
# The phases of the source are the same as the bus by default
vs1 = rlf.VoltageSource("vs1", bus=bus, voltages=230)  # phases="abcn" implied
vs1.phases  # "abcn"
vs1.voltage_phases  # ["an", "bn", "cn"]

# Explicitly define the phases of the source (star connection)
vs2 = rlf.VoltageSource("vs2", bus=bus, phases="abcn", voltages=230)  # Same as vs1
vs2.phases  # "abcn"
vs2.voltage_phases  # ["an", "bn", "cn"]

# Explicitly define the phases of the source (delta connection)
vs3 = rlf.VoltageSource("vs3", bus=bus, phases="abc", voltages=400)
vs3.phases  # "abc"
vs3.voltage_phases  # ["ab", "bc", "ca"]

# Incorrect phases: the source's phases must be a subset of the bus's phases
bus2 = rlf.Bus(id="bus2", phases="an")
rlf.VoltageSource("vs4", bus=bus2, phases="bn", voltages=230)  # Error
```

A **scalar** (potentially complex) voltage value can be used to define the source's balanced voltages. For a
single-phase source, the scalar value is used as the voltage of the source's phase. For a two-phase source, the second
voltage value is the negative of the first value (180° phase shift). For a three-phase source, the second and third
values are calculated by rotating the first value by -120° and 120°, respectively (120° phase shift clockwise).

```python
bus = rlf.Bus(id="bus", phases="abcn")

# Three-phase connection (star)
# -----------------------------
rlf.VoltageSource("vs1", bus=bus, phases="abcn", voltages=230)
# {'an': (230+0j), 'bn': (-115-199.18584287042083j), 'cn': (-115+199.1858428704209j)}

# Three-phase connection (delta)
# ------------------------------
rlf.VoltageSource("vs2", bus=bus, phases="abc", voltages=400)
# {'ab': (400+0j), 'bc': (-200-346.41016151377534j), 'ca': (-200+346.4101615137755j)}

# Two-phase connection
# --------------------
rlf.VoltageSource("vs3", bus=bus, phases="abn", voltages=230)
# {'an': (230+0j), 'bn': (-230+0j)}

# Single-phase connection
# -----------------------
rlf.VoltageSource("vs4", bus=bus, phases="an", voltages=230)
# {'an': (230+0j)}

# Unbalanced source, explicit voltage vector
# ------------------------------------------
rlf.VoltageSource(
    "vs5",
    bus=bus,
    phases="abcn",
    voltages=[230, 115 * np.exp(1j * np.pi / 2), 115 * np.exp(-1j * np.pi / 2)],
)
# {'an': (230+0j), 'bn': (115j), 'cn': (-115j)}

# Incorrect voltage vector: only two elements!!
rlf.VoltageSource(
    id="vs6", bus=bus, phases="abc", voltages=400 * np.exp([0, -2j * np.pi / 3])
)  # Error
```

A voltage **vector** (list or numpy array) can be used to create an unbalanced voltage source if needed. The voltage
vector must have the same size as the number of the phase-to-phase or phase-to-neutral connections of the source.

```python
bus = rlf.Bus(id="bus", phases="abcn")

# Unbalanced source, explicit voltage vector
# ------------------------------------------
rlf.VoltageSource(
    "vs1",
    bus=bus,
    phases="abcn",
    voltages=[230, 115 * np.exp(1j * np.pi / 2), 115 * np.exp(-1j * np.pi / 2)],
)
# {'an': (230+0j), 'bn': (115j), 'cn': (-115j)}

# Incorrect voltage vector: only two voltage values!!
rlf.VoltageSource(
    id="vs2", bus=bus, phases="abc", voltages=400 * np.exp([0, -2j * np.pi / 3])
)  # Error
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.VoltageSource
   :members:
   :show-inheritance:
   :no-index:
```
