# Transformers

## Definition

The transformers which can be modelled using *Roseau Load Flow* are of three different types: single phase,
center-tapped and three-phase transformers. To describe their behaviour, the following parameters are required:
* $U_{1,\mathrm{nom.}}$: the phase-to-phase nominal voltage of the high voltages side (in V). This parameter is noted
  `uhv` in the code.
* $U_{2,\mathrm{nom.}}$: the phase-to-phase nominal voltage of the low voltages side (in V). This parameter is noted
  `ulv` in the code.
* $S_{\mathrm{nom.}}$: the nominal power of the transformer (in VA). This parameter is noted  `sn` in the code.
* $i_0$: the current during off-load test (in %). This parameter is noted  `i0` in the code.
* $P_0$: the losses during off-load test (in W). This parameter is noted  `p0` in the code.
* $P_{\mathrm{sc}}$: the losses during short circuit test (in W). This parameter is noted  `psc` in the code.
* $V_{\mathrm{sc}}$: the voltage on LV side during short circuit test (in %). This parameter is noted  `vsc` in the
  code.

For three-phase transformer, the windings is also required. See the dedicated page of
[three-phase transformers](three-phase-transformer) for more details.

These parameters come from off-load test and short-circuit test. Internally, these parameters are converted into a
series impedance $\underline{Z_2}$ and the magnetizing admittance $\underline{Y_{\mathrm{m}}}$.

First, some notations:
* on the primary side of the transformer, we note $i_{1,\mathrm{nom.}}=\dfrac{S_{\mathrm{nom.}}}{U_{1,\mathrm{nom.}}}$
  the nominal current of the primary winding.
* on the secondary side of the transformer, we note $i_{2,\mathrm{nom.}}=\dfrac{S_{\mathrm{nom.}}}{U_{2,\mathrm{nom.}}}$
  the nominal current of the secondary winding.

### Off-load test

We note $P_0$ the losses and $i_1^0$ the current in the primary winding of the transformer during this test. The
following values can be computed:

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
\underline{Z_2} = R2+j\cdot X2
```

## Transformer parameters

To define the parameters of the transformers, the `TransformerParameters` instance must be used. It takes the
elements described in the previous section in order to define the behaviour of a transformer. The argument `type` of
the constructor has three potential values:

* `"single"` if you want to model a single-phase transformer
* `"center"` if you want to model a center-tapped transformer
* Any windings (`"Dd0"`, `"Dz6"`, etc.) to model a three-phase transformer.

Here is an example of the creation of `TansformerParameters` instances.

```python
from roseau.load_flow import TransformerParameters, Q_

# The transformer parameters for a single-phase transformer
single_phase_transformer_parameters = TransformerParameters(
    id="single_phase_transformer_parameters",
    type="single",  # Here the keyword "single" is provided in the `type` argument
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
    type="Dyn11",  # Here the windings is provided in the `type` argument
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
    type="center",  # Here the keyword "center" is provided in the `type` argument
    uhv=Q_(20, "kV"),
    ulv=Q_(400, "V"),
    sn=Q_(160, "kVA"),
    p0=Q_(300, "W"),
    i0=Q_(1.4, "%"),
    psc=Q_(2000, "W"),
    vsc=Q_(4, "%"),
)
```

## Available models

The following transformer models are available in *Roseau Load Flow*:

```{toctree}
---
maxdepth: 2
caption: Transformers
---
Single_Phase_Transformer
Three_Phase_Transformer
Center_Tapped_Transformer
```
