# Loads

The load element can be used to model consumption loads (with positive active power) as well as generation loads
(with negative active power).

## Connections

For each load type, two connections can be made.

### Star connection

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

In order to be created in *Roseau Load Flow*, the `phases` argument of the constructor must contain `"n"`.

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

In order to be created in *Roseau Load Flow*, the `phases` argument of the constructor must **not** contain `"n"`.

## Available models

The following load models are available in *Roseau Load Flow*:

```{toctree}
---
maxdepth: 2
caption: Loads
---
PowerLoad
ImpedanceLoad
CurrentLoad
FlexibleLoad
```
