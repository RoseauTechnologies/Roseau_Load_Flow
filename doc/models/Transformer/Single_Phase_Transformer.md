---
myst:
  html_meta:
    description lang=en: |
      Single-phase transformers in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by
      Roseau Technologies.
    keywords lang=en: simulation, distribution grid, switch, transformers, single-phase, model
    # spellchecker:off
    description lang=fr: |
      Les transformateurs monophasés dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré
      dans une API Python par Roseau Technologies.
    keywords lang=fr: simulation, réseau, électrique, bus, roseau load flow, transformateurs, monophasé, modèle
# spellchecker:on
---

# Single-phase transformer

Single-phase transformers are modelled as follows:

````{tab} European standards
```{image}  /_static/Transformer/European_Single_Phase_Transformer.svg
:alt: Single-phase transformer diagram
:width: 500px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Single_Phase_Transformer.svg
:alt: Single-phase transformer diagram
:width: 500px
:align: center
```
````

Non-ideal transformer models are used in _Roseau Load Flow_. The series impedances $\underline{Z_2}$ and the magnetizing
admittances $\underline{Y_{\mathrm{m}}}$ are included in the model.

```{note}
Figures and equations on this page are related to a transformer connected between the phases $\mathrm{a}$ and $\mathrm
{n}$. Nevertheless, single-phase transformers can be connected between any two phases.
```

## Equations

The following equations are used:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
        k \cdot \underline{U_{1,\mathrm{a}}} &= \underline{U_{2,\mathrm{a}}} - \underline{Z_2} \cdot \underline{I_{2,
        \mathrm{a}}} \\
        \underline{I_{1,\mathrm{a}}} - \underline{Y_{\mathrm{m}}} \cdot \underline{U_{1,\mathrm{a}}} &= -k \cdot
        \underline{I_{2,\mathrm{a}}} \\
        \underline{I_{1,\mathrm{a}}} &= -\underline{I_{1,\mathrm{n}}} \\
        \underline{I_{2,\mathrm{a}}} &= -\underline{I_{2,\mathrm{n}}} \\
    \end{aligned}
  \right.
\end{equation}
```

Where $\underline{Z_2}$ is the series impedance, $\underline{Y_{\mathrm{m}}}$ is the magnetizing admittance of the
transformer, and $k$ the transformation ratio.

## Example

The following examples shows a single-phase load connected via an isolating single-phase transformer to a three-phase
voltage source.

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Create the source bus and the voltage source
bus1 = rlf.Bus(id="bus1", phases="abcn")
pref1 = rlf.PotentialRef(id="pref1", element=bus1)

vs = rlf.VoltageSource(id="vs", bus=bus1, voltages=400 / rlf.SQRT3)

# Create the load bus and the load
bus2 = rlf.Bus(id="bus2", phases="an")
pref2 = rlf.PotentialRef(id="pref2", element=bus2)

load = rlf.PowerLoad(id="load", bus=bus2, powers=[100], phases="an")

# Create the transformer
tp = rlf.TransformerParameters.from_open_and_short_circuit_tests(
    id="Example_TP",
    vg="Ii0",  # <--- Single-phase transformer
    sn=800,
    uhv=400,
    ulv=400,
    i0=0.022,
    p0=17,
    psc=25,
    vsc=0.032,
)
transformer = rlf.Transformer(
    id="transfo",
    bus_hv=bus1,
    bus_lv=bus2,
    phases_hv="an",
    phases_lv="an",
    parameters=tp,
)

# Create the network and solve the load flow
en = rlf.ElectricalNetwork.from_element(bus1)
en.solve_load_flow()

# The current flowing into the transformer from the source side
en.res_transformers[["current_hv"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                  |   ('current_hv', 'absolute') |   ('current_hv', 'angle') |
# |:-----------------|-----------------------------:|--------------------------:|
# | ('transfo', 'a') |                     0.462811 |                 -0.956008 |
# | ('transfo', 'n') |                     0.462811 |                179.044    |

# The current flowing into the transformer from the load side
en.res_transformers[["current_lv"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                  |   ('current_lv', 'absolute') |   ('current_lv', 'angle') |
# |:-----------------|-----------------------------:|--------------------------:|
# | ('transfo', 'a') |                     0.438211 |                179.85     |
# | ('transfo', 'n') |                     0.438211 |                 -0.149761 |

# The power flow in the transformer
en.res_transformers[["power_hv", "power_lv"]].abs()
# |                  |   power_hv |   power_lv |
# |:-----------------|-----------:|-----------:|
# | ('transfo', 'a') |    106.882 |        100 |
# | ('transfo', 'n') |      0     |          0 |

# The voltages at the buses of the network
en.res_buses_voltages[["voltage"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------|--------------------------:|-----------------------:|
# | ('bus1', 'an') |                    230.94 |               0        |
# | ('bus1', 'bn') |                    230.94 |            -120        |
# | ('bus1', 'cn') |                    230.94 |             120        |
# | ('bus2', 'an') |                    228.2  |              -0.149761 |
```
