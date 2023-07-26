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

In *Roseau Load Flow*, the `phases` argument of the constructor must contain `"n"` for star loads.

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

In *Roseau Load Flow*, the `phases` argument of the constructor must **not** contain `"n"` for delta
loads.

## Available models

The *ZIP* model is commonly used to represent electric loads in static grid analysis. This model
considers the voltage dependency of loads. ZIP stands for the three load types:

* Z = constant impedance load
* I = constant current load
* P = constant power load

The following load models are available in *Roseau Load Flow*:

```{toctree}
---
maxdepth: 2
caption: Loads
---
ImpedanceLoad
CurrentLoad
PowerLoad
FlexibleLoad
```
