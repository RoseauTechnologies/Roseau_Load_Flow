---
myst:
  html_meta:
    "description lang=en": |
      Three-phase transformers in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by
      Roseau Technologies.
    "description lang=fr": |
      Les transformateurs triphasés dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré
      dans une API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, transformateurs, triphasé, modèle
    "keywords lang=en": simulation, distribution grid, switch, transformers, three-phase, 3-phase, model
---

(three-phase-transformer)=

# Three-phase transformer

Three-phase transformers are modeled with three separate single-phase non-ideal transformers. The
windings of the individual transformers are connected with different configurations to the high
voltage (HV) side and to the low voltage (LV) side.
The non-ideal transformer losses are represented by $\underline{Z_2}$ the series impedances and
$\underline{Y_{\mathrm{m}}}$ the magnetizing admittances.

````{tab} European standards
```{image}  /_static/Transformer/European_Three_Phase_Transformer.svg
:alt: Three-phase transformer diagram
:width: 700px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Three_Phase_Transformer.svg
:alt: Three-phase transformer diagram
:width: 700px
:align: center
```
````

For example, the windings with a $Dyn11$ configuration are represented by the following diagram:

````{tab} European standards
```{image}  /_static/Transformer/European_Dyn11.svg
:alt: Dyn11 windings diagram
:width: 700px
:align: center
```
````

````{tab} American standards
```{image}  /_static/Transformer/American_Dyn11.svg
:alt: Dyn11 windings diagram
:width: 700px
:align: center
```
````

Notice how the neutral is accessible on the LV side of the transformer. Transformers with the
neutral not brought out are also supported by omitting the $n$ in the vector group (e.g. $Dy11$).
In this case there will be no neutral connection on the LV side.

## Winding configurations

_Roseau Load Flow_ supports most of the 2-winding transformer configurations as defined in the IEC
60076-1 standard.

The following common connections are supported:

```{image} /_static/Transformer/Common_Connections.svg
:alt: Common transformer connections
:width: 700px
:align: center
```

The following additional connections are also supported:

```{image} /_static/Transformer/Additional_Connections.svg
:alt: Additional transformer connections
:width: 700px
:align: center
```

Note that the neutral connection is omitted in the diagrams above for simplicity. All _Wye_ and
_Zigzag_ connections, whether on the HV side or on the LV side, may have a neutral connection
brought out.

## Equations

The following equations are used to model 3-phase transformers:

```{math}
\begin{equation}
    \left\{
    \begin{aligned}
        K_{\mathrm{UXYZ}} \cdot \underline{U_{\mathrm{XYZ}}}
        &= K_{\mathrm{VABC}} \cdot \underline{V_{\mathrm{ABC}}} - K_{\mathrm{N}} \cdot \underline{V_{\mathrm{N}}} \\
        K_{\mathrm{Uxyz}} \cdot M_{\mathrm{TV}}\cdot \underline{U_{\mathrm{XYZ}}} + o_r \cdot \underline{Z_2} \cdot
        \underline{I_{\mathrm{xyz}}}
            &= K_{\mathrm{Vabc}} \cdot \underline{V_{\mathrm{abc}}} - K_{\mathrm{n}} \cdot \underline{V_{\mathrm{n}}} \\
        K_{\mathrm{IABC}} \cdot \underline{I_{\mathrm{ABC}}} &= K_{\mathrm{IXYZ}} \cdot
            \left( \underline{Y_{\mathrm{m}}} \cdot \underline{U_{\mathrm{XYZ}}} + M_{\mathrm{TI}} \cdot
            \underline{I_{\mathrm{xyz}}} \right)\\
        K_{\mathrm{Iabc}} \cdot \underline{I_{\mathrm{abc}}} &= K_{\mathrm{Ixyz}} \cdot \underline{I_{\mathrm{xyz}}} \\
        \underline{I_{\mathrm{N}}} &= - K_{\mathrm{N}}^\top \cdot \underline{I_{\mathrm{ABC}}} \\
        \underline{I_{\mathrm{n}}} &= - K_{\mathrm{n}}^\top \cdot \underline{I_{\mathrm{abc}}}
    \end{aligned}
  \right.
\end{equation}
```

Where $\underline{Z_2}$ is the series impedance and $\underline{Y_{\mathrm{m}}}$ is the magnetizing
admittance of the transformer. $o_r$ is the orientation variable, equals to $1$ for direct windings,
i.e. windings with the hour index in the top half of the clock, and $-1$ for inverse windings, i.e.
windings with the hour index in the bottom half of the clock. The other quantities are the matrices
defined below.

## Matrices

Let $I_3$ be the identity matrix $\begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{pmatrix}$,
$S_3$ be the shifting matrix $\begin{pmatrix} 0 & 1 & 0 \\ 0 & 0 & 1 \\ 1 & 0 & 0 \end{pmatrix}$, and
$S_3^T$ be its transpose. Also, let $0_3$ be the null vector $\begin{pmatrix} 0 \\ 0 \\ 0 \end{pmatrix}$
and $1_3$ be the vector $\begin{pmatrix} 1 \\ 1 \\ 1 \end{pmatrix}$.
The following matrices are used to model the winding configurations described above:

### Transformation matrices

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 2
:align: center

* - Windings
  - Clock numbers
  - $M_{\mathrm{TV}}$
  - $M_{\mathrm{TI}}$

* - _Dd_, _Yy_, _Dy_, _Yd_
  - _all_
  - $k I_3$
  - $-k I_3$

* - _Dz_, _Yz_
  - 4,5,10,11
  - $k I_3$
  - $-k (I_3 - S_3^T)$

* - _Dz_, _Yz_
  - 0,6,1,2,7,8
  - $k I_3$
  - $-k (I_3 - S_3)$
```

Where $k$ is the transformation ratio of the internal transformers defined as:

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 1
:align: center

* - Windings
  - $k$
* - Dy, Yz
  - $\dfrac{U_{\mathrm{LV}}}{\sqrt{3} \cdot  U_{\mathrm{HV}}}$
* - Dd, Yy
  - $\dfrac{U_{\mathrm{LV}}}{U_{\mathrm{HV}}}$
* - Yd
  - $\dfrac{\sqrt{3} \cdot U_{\mathrm{LV}}}{U_{\mathrm{HV}}}$
* - Dz
  - $\dfrac{U_{\mathrm{LV}}}{3 \cdot U_{\mathrm{HV}}}$
```

### HV winding matrices

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 2
:align: center

* - HV Winding
  - Clock numbers
  - $K_{\mathrm{VABC}}$
  - $K_{\mathrm{UXYZ}}$
  - $K_{\mathrm{IABC}}$
  - $K_{\mathrm{IXYZ}}$
  - $K_{\mathrm{N}}$

* - _D_
  - 0,6,4,5,10,11
  - $I_3 - S_3$
  - $I_3$
  - $I_3$
  - $I_3 - S_3^T$
  - $0_3$

* - _D_
  - 1,2,7,8
  - $I_3 - S_3^T$
  - $I_3$
  - $I_3$
  - $I_3 - S_3$
  - $0_3$

* - _Y_
  - _all_
  - $I_3$
  - $I_3$
  - $I_3$
  - $I_3$
  - $1_3$
```

### LV winding matrices

```{list-table}
:class: borderless
:header-rows: 1
:stub-columns: 2
:align: center

* - LV Winding
  - Clock numbers
  - $K_{\mathrm{Vabc}}$
  - $K_{\mathrm{Uxyz}}$
  - $K_{\mathrm{Iabc}}$
  - $K_{\mathrm{Ixyz}}$
  - $K_{\mathrm{n}}$
* - _d_
  - 0,6,1,2,7,8
  - $I_3 - S_3$
  - $I_3$
  - $I_3$
  - $I_3 - S_3^T$
  - $0_3$

* - _d_
  - 4,5,10,11
  - $I_3 - S_3^T$
  - $I_3$
  - $I_3$
  - $I_3 - S_3$
  - $0_3$

* - _y_
  - _all_
  - $I_3$
  - $I_3$
  - $I_3$
  - $I_3$
  - $1_3$

* - _z_
  - 0,6,1,2,7,8
  - $I_3$
  - $I_3 - S_3^T$
  - $I_3$
  - $I_3$
  - $1_3$

* - _z_
  - 4,5,10,11
  - $I_3$
  - $I_3 - S_3$
  - $I_3$
  - $I_3$
  - $1_3$
```

## Example

The following example shows a 160kVA MV/LV transformer with a $Dyn11$ configuration that
connects a voltage source on the MV network to a load on the LV network.

```python
import functools as ft
import numpy as np
import roseau.load_flow as rlf

# Create a MV bus
bus_mv = rlf.Bus(id="bus_mv", phases="abc")

# Create a LV bus
bus_lv = rlf.Bus(id="bus_lv", phases="abcn")

# Set the potential references of the MV and LV networks
pref_mv = rlf.PotentialRef(id="pref_mv", element=bus_mv)
pref_lv = rlf.PotentialRef(id="pref_lv", element=bus_lv)

# Create a voltage source and connect it to the MV bus
vs = rlf.VoltageSource(id="vs", bus=bus_mv, voltages=20e3)

# Create a MV/LV transformer
tp = rlf.TransformerParameters.from_open_and_short_circuit_tests(
    id="SE Minera A0Ak 100kVA",
    vg="Dyn11",
    sn=100.0 * 1e3,
    uhv=20e3,
    ulv=400.0,
    i0=0.5 / 100,
    p0=145.0,
    psc=1250.0,
    vsc=4.0 / 100,
)
transformer = rlf.Transformer(
    id="transfo",
    bus_hv=bus_mv,
    bus_lv=bus_lv,
    phases_hv="abc",
    phases_lv="abcn",
    parameters=tp,
    tap=1.025,
)

# Create a balanced constant-power 9kW LV load (3kW per phase)
load = rlf.PowerLoad(id="load", bus=bus_lv, phases="abcn", powers=3e3)

# Create the network and solve the load flow
en = rlf.ElectricalNetwork.from_element(bus_mv)
en.solve_load_flow()

# The current flowing into the transformer from the MV bus
en.res_transformers[["current1"]].dropna().transform(
    [np.abs, ft.partial(np.angle, deg=True)]
)
# |                  |   ('current1', 'absolute') |   ('current1', 'angle') |
# |:-----------------|---------------------------:|------------------------:|
# | ('transfo', 'a') |                   0.275904 |                -38.8165 |
# | ('transfo', 'b') |                   0.275904 |               -158.817  |
# | ('transfo', 'c') |                   0.275904 |                 81.1835 |

# The current flowing into the transformer from the LV bus
en.res_transformers[["current2"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                  |   ('current2', 'absolute') |   ('current2', 'angle') |
# |:-----------------|---------------------------:|------------------------:|
# | ('transfo', 'a') |               12.6872      |                179.813  |
# | ('transfo', 'b') |               12.6872      |                 59.8133 |
# | ('transfo', 'c') |               12.6872      |                -60.1867 |
# | ('transfo', 'n') |                2.25156e-13 |                -80.4634 |

# The voltages at the buses of the network
en.res_buses_voltages[["voltage"]].transform([np.abs, ft.partial(np.angle, deg=True)])
# |                  |   ('voltage', 'absolute') |   ('voltage', 'angle') |
# |:-----------------|--------------------------:|-----------------------:|
# | ('bus_mv', 'ab') |                 20000     |               0        |
# | ('bus_mv', 'bc') |                 20000     |            -120        |
# | ('bus_mv', 'ca') |                 20000     |             120        |
# | ('bus_lv', 'an') |                   236.459 |              -0.186695 |
# | ('bus_lv', 'bn') |                   236.459 |            -120.187    |
# | ('bus_lv', 'cn') |                   236.459 |             119.813    |
```
