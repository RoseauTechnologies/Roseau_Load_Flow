---
myst:
  html_meta:
    "description lang=en": |
      Center-tapped transformers in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by
      Roseau Technologies.
    "description lang=fr": |
      Transformateur à prise centrale dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré
      dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, transformateurs, prise centrale, modèle
    "keywords lang=en": simulation, distribution grid, switch, transformers, Center-tapped, model
---

# Center-tapped transformer

Center-tapped transformers allow to split two-phase connection on its HV side into a two-phase
connection with a neutral point in the middle on its LV side. It is modelled as follows:

````{tab} European standards
```{image}  /_static/Transformer/European_Center_Tapped_Transformer.svg
:alt: Center-tapped transformer diagram
:width: 500px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Center_Tapped_Transformer.svg
:alt: Center-tapped transformer diagram
:width: 500px
:align: center
```
````

Non-ideal models are used in _Roseau Load Flow_. The series impedances $\underline{Z_2}$ and the
magnetizing admittances $\underline{Y_{\mathrm{m}}}$ are included in the model.

```{note}
Figures and equations on this page are related to a transformer connected between the phases $\mathrm{a}$ and $\mathrm
{b}$. Nevertheless, center-tapped transformers can be connected between any two phases **as long as the center phase
at the secondary is always $\mathrm{n}$**.
```

## Equations

The following equations are used:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
        \underline{U_{2,\mathrm{a}}^0} &= -\underline{U_{2,\mathrm{b}}^0} \\
        k \cdot \underline{U_{1,\mathrm{ab}}} &= \underline{U_{2,\mathrm{a}}^0} - \underline{U_{2,\mathrm
        {b}}^0} \\
        \underline{I_{1,\mathrm{a}}} - Y_{\mathrm{m}} \cdot \underline{U_{1,\mathrm{ab}}} &=
        -k \cdot \frac{\underline{I_{2,\mathrm{a}}} + \underline{I_{2,\mathrm{b}}}}{2} \\
        \underline{I_{1,\mathrm{a}}} &= -\underline{I_{1,\mathrm{n}}} \\
        \underline{I_{2,\mathrm{a}}} + \underline{I_{2,\mathrm{b}}} + \underline{I_{2,\mathrm{n}}} &= 0 \\
    \end{aligned}
  \right.
\end{equation}
```

Where $\underline{Z_2}$ is the series impedance, $\underline{Y_{\mathrm{m}}}$ is the magnetizing
admittance of the transformer, $k$ the transformation ratio, and:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
        \underline{U_{2,\mathrm{a}}^0} &= \underline{U_{2,\mathrm{a}}} - \frac{Z_2}{2} \underline{I_{2,\mathrm{a}}} \\
        \underline{U_{2,\mathrm{b}}^0} &= \underline{U_{2,\mathrm{b}}} - \frac{Z_2}{2} \underline{I_{2,\mathrm{b}}}
        \end{aligned}
  \right.
\end{equation}
```

## Example

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Create a ground and set it as the reference of potentials
ground = rlf.Ground("ground")
pref = rlf.PotentialRef("pref", ground)

# Create a source bus and voltage source (MV)
source_bus = rlf.Bus("source_bus", phases="abc")
vs = rlf.VoltageSource(id="vs", bus=source_bus, voltages=20e3)

# Create a load bus and a load (MV)
load_bus = rlf.Bus(id="load_bus", phases="abc")
mv_load = rlf.PowerLoad("mv_load", load_bus, powers=[10000, 10000, 10000])

# Connect the two MV buses with an Underground ALuminium line of 150mm²
lp = rlf.LineParameters.from_catalogue(name="U_AL_150")
line = rlf.Line("line", source_bus, load_bus, parameters=lp, length=1.0, ground=ground)

# Create a low-voltage bus and a load
lv_bus = rlf.Bus(id="lv_bus", phases="abn")
lv_bus.connect_ground(ground)
lv_load = rlf.PowerLoad("lv_load", lv_bus, powers=[-2000, 0])

# Create a transformer
tp = rlf.TransformerParameters.from_open_and_short_circuit_tests(
    "t",
    vg="Iii0",  # <--- Center-tapped transformer
    sn=630e3,
    uhv=20000.0,
    ulv=230.0,
    i0=0.018,
    p0=1300.0,
    psc=6500.0,
    vsc=0.04,
)
transformer = rlf.Transformer("transfo", load_bus, lv_bus, parameters=tp)

# Create the network and solve the load flow
en = rlf.ElectricalNetwork.from_element(source_bus)
en.solve_load_flow()

# The current flowing into the line from the source side
en.res_lines[["current1"]].dropna().transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                     1.1229 |                -35.6881 |
# | ('line', 'b') |                   0.559322 |                 -157.84 |
# | ('line', 'c') |                    0.95146 |                 114.464 |


# The current flowing into the transformer from the source side
en.res_transformers[["current_hv"]].dropna().transform(
    [np.abs, ft.partial(np.angle, deg=True)]
)
# |                  |   ('current_hv', 'absolute') |   ('current_hv', 'angle') |
# |:-----------------|-----------------------------:|--------------------------:|
# | ('transfo', 'a') |                     0.564362 |                  -93.5552 |
# | ('transfo', 'b') |                     0.564362 |                   86.4448 |


# The current flowing into the line from the load side
en.res_lines[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |               |   ('current2', 'absolute') |   ('current2', 'angle') |
# |:--------------|---------------------------:|------------------------:|
# | ('line', 'a') |                    1.22632 |                 125.666 |
# | ('line', 'b') |                   0.726787 |                -10.3247 |
# | ('line', 'c') |                   0.866039 |                -90.0003 |


# The current flowing into the transformer from the load side
en.res_transformers[["current_lv"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                  |   ('current_lv', 'absolute') |   ('current_lv', 'angle') |
# |:-----------------|-----------------------------:|--------------------------:|
# | ('transfo', 'a') |                      17.3905 |                 0.0141285 |
# | ('transfo', 'b') |                            0 |                         0 |
# | ('transfo', 'n') |                      17.3905 |                  -179.986 |
# We can see the secondary phase "b" of the transformer does not carry any current as
# the load has 0VA on this phase.

# The voltages at the buses of the network
en.res_buses_voltages[["voltage"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                      |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------------|--------------------------:|-----------------------:|
# | ('source_bus', 'ab') |                     20000 |                      0 |
# | ('source_bus', 'bc') |                     20000 |                   -120 |
# | ('source_bus', 'ca') |                     20000 |                    120 |
# | ('load_bus', 'ab')   |                   19999.6 |             6.9969e-05 |
# | ('load_bus', 'bc')   |                   19999.8 |                   -120 |
# | ('load_bus', 'ca')   |                   19999.6 |                119.999 |
# | ('lv_bus', 'an')     |                   115.005 |              0.0141285 |
# | ('lv_bus', 'bn')     |                   114.998 |                   -180 |
```
