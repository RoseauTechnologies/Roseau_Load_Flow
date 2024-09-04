---
myst:
  html_meta:
    "description lang=en": |
      Load models in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau Technologies.
    "description lang=fr": |
      Les modèles de charge dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une
      API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, charges, modèle
    "keywords lang=en": simulation, distribution grid, switch, load, model
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
