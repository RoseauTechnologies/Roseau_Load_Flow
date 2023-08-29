# Transformers

## Definition

_Roseau Load Flow_ can model single-phase, center-tapped and three-phase transformers.

(models-transformer_parameters)=

## Transformer parameters

Transformers are modeled with the following parameters:

- $U_{1,\mathrm{nom.}}$: the phase-to-phase nominal voltage of the high voltages side (in V). This
  parameter is called `uhv` in the code.
- $U_{2,\mathrm{nom.}}$: the phase-to-phase nominal voltage of the low voltages side (in V). This
  parameter is called `ulv` in the code.
- $S_{\mathrm{nom.}}$: the nominal power of the transformer (in VA). This parameter is called `sn`
  in the code.
- $i_0$: the current during off-load test (in %). This parameter is called `i0` in the code.
- $P_0$: the losses during off-load test (in W). This parameter is called `p0` in the code.
- $P_{\mathrm{sc}}$: the losses during short-circuit test (in W). This parameter is called `psc`
  in the code.
- $V_{\mathrm{sc}}$: the voltage on LV side during short-circuit test (in %). This parameter is
  called `vsc` in the code.

For three-phase transformers, the windings configuration is also required. See the dedicated page
of [three-phase transformers](Three_Phase_Transformer.md) for more details.

These parameters come from off-load and short-circuit tests. Internally, these parameters are
converted into a series impedance $\underline{Z_2}$ and the magnetizing admittance
$\underline{Y_{\mathrm{m}}}$.

First, we define the following quantities:

- $i_{1,\mathrm{nom.}}=\dfrac{S_{\mathrm{nom.}}}{U_{1,\mathrm{nom.}}}$: the nominal current of the
  winding on the primary side of the transformer
- $i_{2,\mathrm{nom.}}=\dfrac{S_{\mathrm{nom.}}}{U_{2,\mathrm{nom.}}}$: the nominal current of the
  winding on the secondary side of the transformer.

### Off-load test

We note $P_0$ the losses and $i_1^0$ the current in the primary winding of the transformer during
this test. The following values can be computed:

```{math}
\begin{aligned}
    i_0&=100\cdot \frac{i_1^0}{i_{1,\mathrm{nom.}}} \qquad \text{(in %)} \\
    S_0 &= U_0\cdot i_1^0 = U_{1,\mathrm{nom.}}\cdot (i_0\cdot i_{1,\mathrm{nom.}}) = i_0\cdot S_{\mathrm{nom.}}
      \qquad \text{(in VA)}\\
    R_{\mathrm{iron}} &= \dfrac{U_{1,\mathrm{nom.}}^2}{P_0} \qquad \text{(in Ohm)}\\
    L_{\mathrm{m}} &= \dfrac{U_{1,\mathrm{nom.}}}{\omega\sqrt{S_0^2-P_0^2}} \text{(in H)}
\end{aligned}
```

Then, $\underline{Y_{\mathrm{m}}}$ can be deduced:

```{math}
\underline{Y_{\mathrm{m}}} = \left\{
    \begin{aligned}
        \frac{1}{R_{\mathrm{iron}}+j\omega L_{\mathrm{m}}} & \qquad \text{if } i_0\cdot S_{\mathrm{nom.}} > P_0 \\
        \frac{1}{R_{\mathrm{iron}}} & \qquad \text{otherwise}
    \end{aligned}
\right.
```

### Short-circuit test

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

## Usage

To define the parameters of the transformers, use the `TransformerParameters` class. It takes as
arguments the elements described in the previous section and converts them into the series
impedance and the magnetizing admittance. The `type` argument of the constructor can take the
following values:

- `"single"` to model a single-phase transformer
- `"center"` to model a center-tapped transformer
- Any windings (`"Dd0"`, `"Dz6"`, etc.) to model a three-phase transformer.

```python
from roseau.load_flow import TransformerParameters, Q_

# The transformer parameters for a single-phase transformer
single_phase_transformer_parameters = TransformerParameters(
    id="single_phase_transformer_parameters",
    type="single",  # <--- single-phase transformer
    uhv=Q_(20, "kV"),
    ulv=Q_(400, "V"),
    sn=Q_(160, "kVA"),
    p0=Q_(300, "W"),
    i0=Q_(1.4, "%"),
    psc=Q_(2000, "W"),
    vsc=Q_(4, "%"),
)

# The transformer parameters for a three-phase transformer
three_phase_transformer_parameters = TransformerParameters(
    id="three_phase_transformer_parameters",
    type="Dyn11",  # <--- three-phase transformer with delta primary and wye secondary
    uhv=Q_(20, "kV"),
    ulv=Q_(400, "V"),
    sn=Q_(160, "kVA"),
    p0=Q_(300, "W"),
    i0=Q_(1.4, "%"),
    psc=Q_(2000, "W"),
    vsc=Q_(4, "%"),
)

# The transformer parameters for a center-tapped transformer
center_tapped_transformer_parameters = TransformerParameters(
    id="center_tapped_transformer_parameters",
    type="center",  # <--- center-tapped transformer
    uhv=Q_(20, "kV"),
    ulv=Q_(400, "V"),
    sn=Q_(160, "kVA"),
    p0=Q_(300, "W"),
    i0=Q_(1.4, "%"),
    psc=Q_(2000, "W"),
    vsc=Q_(4, "%"),
)
```

A catalogue of transformer parameters is available. More details [here](catalogues-transformers).

## Available models

The following transformer models are available in _Roseau Load Flow_:

```{toctree}
---
maxdepth: 2
caption: Transformers
---
Single_Phase_Transformer
Three_Phase_Transformer
Center_Tapped_Transformer
```
