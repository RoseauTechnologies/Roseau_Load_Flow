---
myst:
  html_meta:
    "description lang=en": |
      Load models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau Technologies.
    "keywords lang=en": simulation, distribution grid, switch, load, model
    # spellchecker:off
    "description lang=fr": |
      Les modèles de charge dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une
      API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, charges, modèle
# spellchecker:on
---

# Loads

## Definition

The load element can be used to model consumption loads (with positive active power) as well as
generation loads (with negative active power).

## Connections

A load can be either star-connected or delta-connected depending on whether its phases include a
neutral or not.

### Star (wye) connection

Here is the diagram of a star-connected three-phase load:

````{tab} European standards
```{image}  /_static/Load/European_Star_Load.svg
:alt: Star load diagram
:width: 300px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Load/American_Star_Load.svg
:alt: Star load diagram
:width: 300px
:align: center
```
````

In _Roseau Load Flow_, the `phases` argument of the constructor must contain `"n"` for star loads.

```{note}
You can create star connected constant-power or constant-impedance loads even on buses that don't
have a neutral. In this case, the load's neutral will be floating and its potential can be accessed
similar to normal star loads.
```

### Delta connection

Here is the diagram of a delta-connected three-phase load:

````{tab} European standards
```{image}  /_static/Load/European_Delta_Load.svg
:alt: Delta load diagram
:width: 300px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Load/American_Delta_Load.svg
:alt: Delta load diagram
:width: 300px
:align: center
```
````

In _Roseau Load Flow_, the `phases` argument of the constructor must **not** contain `"n"` for delta
loads.

## Available Results

The following results are available for all loads:

| Result Accessor      | Default Unit | Type          | Description                                                                                    |
| -------------------- | ------------ | ------------- | ---------------------------------------------------------------------------------------------- |
| `res_potentials`     | $V$          | complex array | The potentials of each phase of the load                                                       |
| `res_currents`       | $A$          | complex array | The line currents flowing into each phase of the load                                          |
| `res_powers`         | $V\!A$       | complex array | The line powers flowing into each phase of the load                                            |
| `res_voltages`       | $V$          | complex array | The phase-to-neutral voltages if the load has a neutral, the phase-to-phase voltages otherwise |
| `res_inner_currents` | $A$          | complex array | The currents flowing in each component (dipole) of the load.                                   |
| `res_inner_powers`   | $V\!A$       | complex array | The powers dissipated by each component (dipole) of the load.                                  |

Additionally, the following results are available for loads with a neutral:

| Result Accessor   | Default Unit | Type          | Description                               |
| ----------------- | ------------ | ------------- | ----------------------------------------- |
| `res_voltages_pn` | $V$          | complex array | The phase-to-neutral voltages of the load |

And the following results are available for loads with more than one phase:

| Result Accessor   | Default Unit | Type          | Description                             |
| ----------------- | ------------ | ------------- | --------------------------------------- |
| `res_voltages_pp` | $V$          | complex array | The phase-to-phase voltages of the load |

And the following results are available for _three-phase_ loads:

| Result Accessor           | Default Unit | Type   | Description                                                                     |
| ------------------------- | ------------ | ------ | ------------------------------------------------------------------------------- |
| `res_voltage_unbalance()` | $\%$         | number | The voltage unbalance of the load according to the IEC, IEEE or NEMA definition |
| `res_current_unbalance()` | $\%$         | number | The Current Unbalance Factor of the load (CUF)                                  |

## Available models

The _ZIP_ model is commonly used to represent electric loads in static grid analysis. This model
considers the voltage dependency of loads. ZIP stands for the three load types:

- Z = constant impedance load
- I = constant current load
- P = constant power load

The following load models are available in _Roseau Load Flow_:

```{toctree}
:maxdepth: 3
:caption: Loads

ImpedanceLoad
CurrentLoad
PowerLoad
FlexibleLoad/index
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.AbstractLoad
   :members:
   :show-inheritance:
   :no-index:
.. autoapiclass:: roseau.load_flow.models.ImpedanceLoad
   :members:
   :show-inheritance:
   :no-index:
.. autoapiclass:: roseau.load_flow.models.CurrentLoad
    :members:
    :show-inheritance:
    :no-index:
.. autoapiclass:: roseau.load_flow.models.PowerLoad
    :members:
    :show-inheritance:
    :no-index:
```
