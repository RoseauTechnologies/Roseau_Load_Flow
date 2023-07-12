# Loads

The load element can be used to model consumption loads (with positive active power) as well as generation loads
(with negative active power). For each load type, two connections can be made:
* star-connected loads using a `phases` constructor argument containing a `"n"`

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

* delta-connected loads using a `phases` constructor argument which doesn't contain `"n"`

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
