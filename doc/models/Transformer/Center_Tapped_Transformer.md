# Center-tapped transformer

Center-tapped transformers allow to convert two phases primary connection into a split-phase
secondary connection, with the neutral at the center secondary winding. It is modelled as follows:

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
from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    Transformer,
    TransformerParameters,
    VoltageSource,
)

# Create a ground and set it as the reference potential
ground = Ground("ground")
pref = PotentialRef("pref", ground)

# Create a source bus and voltage source (MV)
source_bus = Bus("source_bus", phases="abcn")
ground.connect(source_bus)
voltages = 20e3 / np.sqrt(3) * np.exp([0, -2j * np.pi / 3, 2j * np.pi / 3])
vs = VoltageSource(id="vs", bus=source_bus, voltages=voltages)

# Create a load bus and a load (MV)
load_bus = Bus(id="load_bus", phases="abc")
mv_load = PowerLoad("mv_load", load_bus, powers=[10000, 10000, 10000])

# Connect the two MV buses with a line
lp = LineParameters.from_name_mv("S_AL_150")
line = Line("line", source_bus, load_bus, parameters=lp, length=1.0, ground=ground)

# Create a low-voltage bus and a load
lv_bus = Bus(id="lv_bus", phases="abn")
ground.connect(lv_bus)
lv_load = PowerLoad("lv_load", lv_bus, powers=[-2000, 0])

# Create a transformer
tp = TransformerParameters(
    "t",
    "center",  # <--- Center-tapped transformer
    sn=630e3,
    uhv=20000.0,
    ulv=230.0,
    i0=0.018,
    p0=1300.0,
    psc=6500.0,
    vsc=0.04,
)
transformer = Transformer("transfo", load_bus, lv_bus, parameters=tp)

# Create the network and solve the load flow
en = ElectricalNetwork.from_element(source_bus)
en.solve_load_flow()

# The current flowing into the the line and transformer from the source side
en.res_branches[["current1"]].dropna().transform([np.abs, ft.partial(np.angle, deg=True)])
# |                  |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:-----------------|---------------------------:|------------------------:|
# | ('line', 'a')    |                   1.58451  |                 45.1554 |
# | ('line', 'b')    |                   1.28415  |                -55.5618 |
# | ('line', 'c')    |                   1.84471  |               -178      |
# | ('transfo', 'a') |                   0.564366 |                -63.5557 |
# | ('transfo', 'b') |                   0.564366 |                116.444  |

# The current flowing into the line and transformer from the load side
en.res_branches[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                  |   ('current2', 'absolute') |   ('current2', 'angle') |
# |:-----------------|---------------------------:|------------------------:|
# | ('line', 'a')    |                   1.22632  |                155.665  |
# | ('line', 'b')    |                   0.726784 |                 19.6741 |
# | ('line', 'c')    |                   0.866034 |                -60.0009 |
# | ('transfo', 'a') |                  17.3904   |                 30.0135 |
# | ('transfo', 'b') |                   0        |                  0      |
# | ('transfo', 'n') |                  17.3904   |               -149.987  |
# We can see the secondary phase "b" of the transformer does not carry any current as
# the load has 0VA on this phase.

# The voltages at the buses of the network
en.res_buses_voltages.transform([np.abs, ft.partial(np.angle, deg=True)])
# |                      |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:---------------------|--------------------------:|-----------------------:|
# | ('source_bus', 'an') |                 11547     |            9.20565e-25 |
# | ('source_bus', 'bn') |                 11547     |         -120           |
# | ('source_bus', 'cn') |                 11547     |          120           |
# | ('load_bus', 'ab')   |                 19999.8   |           29.9994      |
# | ('load_bus', 'bc')   |                 19999.9   |          -90.0009      |
# | ('load_bus', 'ca')   |                 19999.7   |          149.999       |
# | ('lv_bus', 'an')     |                   115.006 |           30.0135      |
# | ('lv_bus', 'bn')     |                   114.999 |         -150.001       |
```
