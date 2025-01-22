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

- $\mathrm{VG}$: the vector group of the transformer. This parameter is called `vg` in the code.
- $U_\mathrm{HV}$: the phase-to-phase nominal voltage of the high voltage side (in V). This
  parameter is called `uhv` in the code.
- $U_\mathrm{LV}$: the phase-to-phase nominal voltage of the low voltage side (in V). This
  parameter is called `ulv` in the code.
- $S^n$: the nominal power of the transformer (in VA). This parameter is called `sn` in the code.
- $Z_2$: the series impedance located at the low voltage side of the transformer. It represents
  non-ideal transformer losses due to winding resistance and leakage reactance. This parameter is
  called `z2` in the code.
- $Y_m$: the magnetizing admittance located at the high voltage side of the transformer. It
  represents non-ideal transformer losses due to core magnetizing inductance and iron losses. This
  parameter is called `ym` in the code.

The vector group defines the type of transformer and its high voltage and low voltage winding
configuration:

- `"Ii0"` or `"Ii6"` to model a single-phase transformer, in-phase or in opposition respectively;
- `"Iii0"` or `"Iii6"` to model a center-tapped transformer, in-phase or in opposition respectively;
- `"Dd0"`, `"Dyn11"`, etc. to model a three-phase transformer with different winding configurations.
  For a full list of supported three-phase transformer configurations, please refer to the
  [three-phase transformer models](./Three_Phase_Transformer.md) page.

$Z_2$ and $Y_m$ are usually obtained from the following results of open-circuit and short-circuit
tests:

- $i^0$: the current during open-circuit test (in %). This parameter is called `i0` in the code.
- $P^0$: the losses during open-circuit test (in W). This parameter is called `p0` in the code.
- $P^\mathrm{sc}$: the losses during short-circuit test (in W). This parameter is called `psc`
  in the code.
- $V^\mathrm{sc}$: the voltage on LV side during short-circuit test (in %). This parameter is
  called `vsc` in the code.

First, we define the following quantities:

- $i_\mathrm{HV}^n=\dfrac{S^n}{U_\mathrm{HV}}$: the nominal current of the high voltage winding
  of the transformer.
- $i_\mathrm{LV}^n=\dfrac{S^n}{U_\mathrm{LV}}$: the nominal current of the low voltage winding
  of the transformer.

### Open-circuit and short-circuit tests

#### Open-circuit test

Let $P^0$ be the no-load losses and $i^0_\mathrm{HV}$ be the current in the high voltage winding of
the transformer during the no-load (open-circuit) test. The following values can be computed:

```{math}
\begin{aligned}
    i^0&=100\cdot \frac{i_\mathrm{HV}^0}{i_\mathrm{HV}^n} \qquad \text{(in \%)} \\%
    S^0 &= U^0\cdot i_\mathrm{HV}^0 = U_\mathrm{HV}\cdot (i^0\cdot i_\mathrm{HV}^n) = i^0\cdot S^n
      \qquad \text{(in VA)}\\%
    R_{\mathrm{iron}} &= \dfrac{U_\mathrm{HV}^2}{P^0} \qquad \text{(in Ohm)}\\%
    L_{\mathrm{m}} &= \dfrac{U_\mathrm{HV}^2}{\omega\sqrt{{S^0}^2-{P^0}^2}} \text{(in H)}%
\end{aligned}
```

Then, $\underline{Y_{\mathrm{m}}}$ can be deduced:

```{math}
\underline{Y_{\mathrm{m}}} = \left\{
    \begin{aligned}
        \frac{1}{R_{\mathrm{iron}}} + \frac{1}{j\omega L_{\mathrm{m}}} & \qquad \text{if } S^0 > P^0 \\%
        \frac{1}{R_{\mathrm{iron}}} & \qquad \text{otherwise}%
    \end{aligned}
\right\}.
```

#### Short-circuit test

Let $P^{\mathrm{sc}}$ be the short-circuit losses and $U_\mathrm{LV}^\mathrm{sc}$ be the voltage on
LV side during the short-circuit test. The following values can be computed:

```{math}
\begin{aligned}
    V^{\mathrm{sc}}&= 100\cdot \frac{U_\mathrm{LV}^\mathrm{sc}}{U_\mathrm{LV}}
      \qquad \text{(in \%)} \\
    Z_2&=\frac{U_\mathrm{LV}^\mathrm{sc}}{i_\mathrm{LV}^n}
        =U_\mathrm{LV}^\mathrm{sc}\cdot\frac{U_\mathrm{LV}}{S^n}
        =V^\mathrm{sc}\cdot\frac{U_\mathrm{LV}^2}{S^n}
      \qquad \text{(in Ohm)}\\
    R_2&=\frac{P^\mathrm{sc}}{{i_\mathrm{LV}^n}^2}
        =\frac{P^\mathrm{sc}\cdot U_\mathrm{LV}^2}{{S^n}^2}
      \qquad \text{(in Ohm)} \\
    X_2&=L_2\cdot\omega = \sqrt{Z_2^2-R_2^2}
      \qquad \text{(in Ohm)}
\end{aligned}
```

Then, $\underline{Z_2}$ can be deduced:

```{math}
\underline{Z_2} = R_2+j\cdot X_2
```

## Usage

To define the parameters of the transformers, use the `TransformerParameters` class. Depending on
the information you have, you can choose between the following methods:

### Using pre-defined transformers in the catalogue

If you don't have all the information needed to model the transformer but you know its nominal power
and voltage, check if your transformer is already defined in the catalogue. You can then create the
transformer parameters using the {meth}`~roseau.load_flow.TransformerParameters.from_catalogue`
method:

```python
transformer_params = rlf.TransformerParameters.from_catalogue(
    name="SE Minera A0Ak 50kVA 15/20kV(15) 410V Yzn11"
)
```

Refer to the [catalogues page](catalogues-transformers) for more information.

### Using open-circuit and short-circuit test results

If your transformer is not in the catalogue but you have the results of the open-circuit and
short-circuit tests, you can create the transformer parameters using the
{meth}`~roseau.load_flow.TransformerParameters.from_open_and_short_circuit_tests` method:

```python
import roseau.load_flow as rlf

# The transformer parameters for a single-phase transformer
transformer_params_1ph = rlf.TransformerParameters.from_open_and_short_circuit_tests(
    id="transformer_params_1ph",
    vg="Ii0",  # <--- single-phase transformer
    uhv=rlf.Q_(20, "kV"),
    ulv=rlf.Q_(400, "V"),
    sn=rlf.Q_(160, "kVA"),
    p0=rlf.Q_(300, "W"),
    i0=rlf.Q_(1.4, "%"),
    psc=rlf.Q_(2000, "W"),
    vsc=rlf.Q_(4, "%"),
)
assert transformer_params_1ph.type == "single-phase"

# The transformer parameters for a three-phase transformer
transformer_params_3ph = rlf.TransformerParameters.from_open_and_short_circuit_tests(
    id="transformer_params_3ph",
    vg="Dyn11",  # <--- three-phase transformer with (Δ) HV leading (Y) LV by 30°
    uhv=rlf.Q_(20, "kV"),
    ulv=rlf.Q_(400, "V"),
    sn=rlf.Q_(160, "kVA"),
    p0=rlf.Q_(300, "W"),
    i0=rlf.Q_(1.4, "%"),
    psc=rlf.Q_(2000, "W"),
    vsc=rlf.Q_(4, "%"),
)
assert transformer_params_3ph.type == "three-phase"

# The transformer parameters for a center-tapped transformer
transformer_params_ct = rlf.TransformerParameters.from_open_and_short_circuit_tests(
    id="transformer_params_ct",
    vg="Iii0",  # <--- center-tapped transformer
    uhv=rlf.Q_(20, "kV"),
    ulv=rlf.Q_(400, "V"),
    sn=rlf.Q_(160, "kVA"),
    p0=rlf.Q_(300, "W"),
    i0=rlf.Q_(1.4, "%"),
    psc=rlf.Q_(2000, "W"),
    vsc=rlf.Q_(4, "%"),
)
assert transformer_params_ct.type == "center-tapped"

# Available vector groups:
print(rlf.TransformerParameters.allowed_vector_groups)
# "Dd0", "Dd6", ..., "Ii0", "Ii6", "Iii0", "Iii6",
```

### Using the transformer parameters directly

If you know the $Z_2$ and $Y_m$ values, you can create the transformer parameters directly:

```python
transformer_params_1ph = rlf.TransformerParameters(
    id="transformer_params_1ph",
    vg="Ii0",
    uhv=rlf.Q_(20, "kV"),
    ulv=rlf.Q_(400, "V"),
    sn=rlf.Q_(160, "kVA"),
    z2=rlf.Q_(0.0125 + 0.038j, "ohm"),
    ym=rlf.Q_(7.5e-7 - 5.5e-6j, "S"),
)
```

### Using data from another software

If you have the transformer parameters in another software, you can use the available data exchange
methods to create the transformer parameters. We currently support _PowerFactory_ and _OpenDSS_.

- For OpenDSS, use the {meth}`~roseau.load_flow.TransformerParameters.from_open_dss` method.
  Refer to the [OpenDss section](OpenDSS-Transformers) in the data exchange page for more information.
- For PowerFactory, use the {meth}`~roseau.load_flow.TransformerParameters.from_power_factory` method.
  Refer to the [PowerFactory section](PowerFactory-Transformers) in the data exchange page for more
  information.

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
