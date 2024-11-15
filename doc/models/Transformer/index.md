---
myst:
  html_meta:
    "description lang=en": |
      Transformers in Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau Technologies.
    "description lang=fr": |
      Les transformateurs dans Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une
      API Python par Roseau Technologies.
    "keywords lang=fr": simulation, réseau, électrique, bus, roseau load flow, transformateurs, modèle
    "keywords lang=en": simulation, distribution grid, switch, transformers, model
---

# Transformers

## Definition

_Roseau Load Flow_ can model single-phase, center-tapped and three-phase transformers.

(models-transformer_parameters)=

## Transformer parameters

Transformers are modeled with the following parameters:

- $U_{1,\mathrm{nom.}}$: the phase-to-phase nominal voltage of the primary side (in V). This
  parameter is called `up` in the code.
- $U_{2,\mathrm{nom.}}$: the phase-to-phase nominal voltage of the secondary side (in V). This
  parameter is called `us` in the code.
- $S_{\mathrm{nom.}}$: the nominal power of the transformer (in VA). This parameter is called `sn`
  in the code.
- $Z_2$: the series impedance located at the secondary side of the transformer. It represents
  non-ideal transformer losses due to winding resistance and leakage reactance.
- $Y_m$: the magnetizing admittance located at the primary side of the transformer. It represents
  non-ideal transformer losses due to core magnetizing inductance and iron losses.

$Z_2$ and $Y_m$ parameters come from open-circuit and short-circuit tests. They can be obtained
using the following tests results:

- $i_0$: the current during open-circuit test (in %). This parameter is called `i0` in the code.
- $P_0$: the losses during open-circuit test (in W). This parameter is called `p0` in the code.
- $P_{\mathrm{sc}}$: the losses during short-circuit test (in W). This parameter is called `psc`
  in the code.
- $V_{\mathrm{sc}}$: the voltage on LV side during short-circuit test (in %). This parameter is
  called `vsc` in the code.

For three-phase transformers, the windings configuration is also required. See the dedicated page
of [three-phase transformers](Three_Phase_Transformer.md) for more details.

First, we define the following quantities:

- $i_{1,\mathrm{nom.}}=\dfrac{S_{\mathrm{nom.}}}{U_{1,\mathrm{nom.}}}$: the nominal current of the
  winding on the primary side of the transformer
- $i_{2,\mathrm{nom.}}=\dfrac{S_{\mathrm{nom.}}}{U_{2,\mathrm{nom.}}}$: the nominal current of the
  winding on the secondary side of the transformer.

### Open-circuit and short-circuit tests

#### Open-circuit test

We note $P_0$ the losses and $i_1^0$ the current in the primary winding of the transformer during
this test. The following values can be computed:

```{math}
\begin{aligned}
    i_0&=100\cdot \frac{i_1^0}{i_{1,\mathrm{nom.}}} \qquad \text{(in %)} \\
    S_0 &= U_0\cdot i_1^0 = U_{1,\mathrm{nom.}}\cdot (i_0\cdot i_{1,\mathrm{nom.}}) = i_0\cdot S_{\mathrm{nom.}}
      \qquad \text{(in VA)}\\
    R_{\mathrm{iron}} &= \dfrac{U_{1,\mathrm{nom.}}^2}{P_0} \qquad \text{(in Ohm)}\\
    L_{\mathrm{m}} &= \dfrac{U_{1,\mathrm{nom.}}^2}{\omega\sqrt{S_0^2-P_0^2}} \text{(in H)}
\end{aligned}
```

Then, $\underline{Y_{\mathrm{m}}}$ can be deduced:

```{math}
\underline{Y_{\mathrm{m}}} = \left\{
    \begin{aligned}
        \frac{1}{R_{\mathrm{iron}}} + \frac{1}{j\omega L_{\mathrm{m}}} & \qquad \text{if } S_0 > P_0 \\
        \frac{1}{R_{\mathrm{iron}}} & \qquad \text{otherwise}
    \end{aligned}
\right.
```

#### Short-circuit test

We note $P_{\mathrm{sc}}$ the losses, $U_{2,\mathrm{sc}}$ the voltage on LV side during this test. The following
values can be computed:

```{math}
\begin{aligned}
    V_{\mathrm{sc}}&= 100\cdot \frac{U_{2,\mathrm{sc}}}{U_{2,\mathrm{nom.}}} \qquad \text{(in %)} \\
    Z_2&=\frac{U_{2,\mathrm{sc}}}{i_{2,\mathrm{nom.}}}=U_{2,\mathrm{sc}}\cdot\frac{U_{2,\mathrm{nom.}}}{
    S_{\mathrm{nom.}}} =V_{\mathrm{sc}}\cdot\frac{U_{2,\mathrm{nom.}}^2}{S_{\mathrm{nom.}}} \qquad \text{(in Ohm)}\\
    R_2&=\frac{P_{\mathrm{sc}}}{i_{2,\mathrm{nom.}}^2} = \frac{P_{\mathrm{sc}}\cdot U_{2,\mathrm{nom.}}^2}{
    S_{\mathrm{nom.}}^2} \qquad \text{(in Ohm)} \\
    X_2&= L_2\cdot\omega = \sqrt{Z_2^2-R_2^2} \qquad \text{(in Ohm)}
\end{aligned}
```

Then, $\underline{Z_2}$ can be deduced:

```{math}
\underline{Z_2} = R_2+j\cdot X_2
```

### Import from OpenDSS

Transformer parameters can also be created using an OpenDSS transformer parameters. Only two-winding
three-phase transformers are currently supported. For more information and an example, see the
{meth}`TransformerParameters.from_open_dss() <roseau.load_flow.TransformerParameters.from_open_dss>`
method.

## Usage

To define the parameters of the transformers, use the `TransformerParameters` class. It takes as
arguments the elements described in the previous section and converts them into the series
impedance and the magnetizing admittance. The `type` argument of the constructor can take the
following values:

- `"single"` to model a single-phase transformer
- `"center"` to model a center-tapped transformer
- Any windings (`"Dd0"`, `"Dz6"`, etc.) to model a three-phase transformer.

```python
import roseau.load_flow as rlf

# The transformer parameters for a single-phase transformer
single_phase_transformer_parameters = (
    rlf.TransformerParameters.from_open_and_short_circuit_tests(
        id="single_phase_transformer_parameters",
        type="single",  # <--- single-phase transformer
        up=rlf.Q_(20, "kV"),
        us=rlf.Q_(400, "V"),
        sn=rlf.Q_(160, "kVA"),
        p0=rlf.Q_(300, "W"),
        i0=rlf.Q_(1.4, "%"),
        psc=rlf.Q_(2000, "W"),
        vsc=rlf.Q_(4, "%"),
    )
)
# Alternatively, if you have z2 and ym already:
# single_phase_transformer_parameters = rlf.TransformerParameters(
#     id="single_phase_transformer_parameters",
#     type="single",
#     up=rlf.Q_(20, "kV"),
#     us=rlf.Q_(400, "V"),
#     sn=rlf.Q_(160, "kVA"),
#     z2=rlf.Q_(0.0125+0.038j, "ohm"),
#     ym=rlf.Q_(7.5e-7-5.5e-6j, "S"),
# )


# The transformer parameters for a three-phase transformer
three_phase_transformer_parameters = (
    rlf.TransformerParameters.from_open_and_short_circuit_tests(
        id="three_phase_transformer_parameters",
        type="Dyn11",  # <--- three-phase transformer with delta primary and wye secondary
        up=rlf.Q_(20, "kV"),
        us=rlf.Q_(400, "V"),
        sn=rlf.Q_(160, "kVA"),
        p0=rlf.Q_(300, "W"),
        i0=rlf.Q_(1.4, "%"),
        psc=rlf.Q_(2000, "W"),
        vsc=rlf.Q_(4, "%"),
    )
)

# The transformer parameters for a center-tapped transformer
center_tapped_transformer_parameters = (
    rlf.TransformerParameters.from_open_and_short_circuit_tests(
        id="center_tapped_transformer_parameters",
        type="center",  # <--- center-tapped transformer
        up=rlf.Q_(20, "kV"),
        us=rlf.Q_(400, "V"),
        sn=rlf.Q_(160, "kVA"),
        p0=rlf.Q_(300, "W"),
        i0=rlf.Q_(1.4, "%"),
        psc=rlf.Q_(2000, "W"),
        vsc=rlf.Q_(4, "%"),
    )
)
```

A catalogue of transformer parameters is available. More details [here](catalogues-transformers).

## Available models

The following transformer models are available in _Roseau Load Flow_:

```{toctree}
:maxdepth: 2
:caption: Transformers

Single_Phase_Transformer
Three_Phase_Transformer
Center_Tapped_Transformer
```

## API Reference

```{eval-rst}
.. autoapiclass:: roseau.load_flow.models.TransformerParameters
   :members:
   :show-inheritance:
   :no-index:
.. autoapiclass:: roseau.load_flow.models.Transformer
   :members:
   :show-inheritance:
   :no-index:
```
