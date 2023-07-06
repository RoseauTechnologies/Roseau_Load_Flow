# Lines

## Matrices definition

Before describing the different line models, we first have to define the $Z$ and $Y$ matrices.
$Z$ is the series impedance matrix and $Y$ the shunt admittance matrix.

### Series impedance matrix

```{math}
\begin{aligned}
Z &= \begin{pmatrix}
       Z_{aa} & Z_{ab} & Z_{ac} & Z_{an}\\
       Z_{ba} & Z_{bb} & Z_{bc} & Z_{bn}\\
       Z_{ca} & Z_{cb} & Z_{cc} & Z_{cn}\\
       Z_{na} & Z_{nb} & Z_{nc} & Z_{nn}\\
     \end{pmatrix}\\
\\
Z &= R + j \cdot X\\
\\
Z &= \underbrace{\begin{pmatrix}
                   R_{a} & 0 & 0 & 0\\
                   0 & R_{b} & 0 & 0\\
                   0 & 0 & R_{c} & 0\\
                   0 & 0 & 0 & R_{n}\\
                 \end{pmatrix}}_{R} + j \cdot \underbrace{\omega
    \cdot \begin{pmatrix}
            L_{a} & M_{ab} & M_{ac} & M_{an}\\
            M_{ba} & L_{b} & M_{bc} & M_{bn}\\
            M_{ca} & M_{cb} & L_{c} & M_{cn}\\
            M_{na} & M_{nb} & M_{nc} & L_{n}\\
\end{pmatrix}}_{X}
\end{aligned}
```

### Admittance matrix

The admittance matrix $y$ shouldn't be confused with the shunt admittance matrix $Y$.
$y$ represents the admittances between each node, while $Y$ is used to compute the currents and voltages.

```{math}
\begin{aligned}
y &=
    \begin{pmatrix}
      y_{ag} & y_{ab} & y_{ac} & y_{an}\\
      y_{ab} & y_{bg} & y_{bc} & y_{bn}\\
      y_{ac} & y_{bc} & y_{cg} & y_{cn}\\
      y_{an} & y_{bn} & y_{cn} & y_{ng}
    \end{pmatrix}
\\
\\
y &= G + j \cdot B
\\
\\
y &= \underbrace{\begin{pmatrix}
                   G_{a} & 0 & 0 & 0\\
                   0 & G_{b} & 0 & 0\\
                   0 & 0 & G_{c} & 0\\
                   0 & 0 & 0 & G_{n}
                 \end{pmatrix}}_{G} + j \underbrace{\cdot \omega \cdot
    \begin{pmatrix}
      C_{a} & C_{ab} & C_{ac} & C_{an}\\
      C_{ab} & C_{b} & C_{bc} & C_{bn}\\
      C_{ac} & C_{bc} & C_{c} & C_{cn}\\
      C_{an} & C_{bn} & C_{cn} & C_{n}
    \end{pmatrix}}_{B}
\end{aligned}
```

with $G_i$ the transverse conductances and $C_{ij}$ the transverse susceptances.

### Shunt admittance matrix

```{math}
Y =
\begin{pmatrix}
  Y_{aa} & Y_{ab} & Y_{ac} & Y_{an}\\
  Y_{ba} & Y_{bb} & Y_{bc} & Y_{bn}\\
  Y_{ca} & Y_{cb} & Y_{cc} & Y_{cn}\\
  Y_{na} & Y_{nb} & Y_{nc} & Y_{nn}\\
\end{pmatrix}
\quad \text{with} \quad
\left\{
  \begin{aligned}
    Y_{ii} &= \sum_{k\in\{a,b,c,n,g\}}{y_{ik}}\\
    Y_{ij} &= -y_{ij}\\
  \end{aligned}
\right.
```

## Shunt line model

An electrical line PI model with series impedance and shunt admittance. The corresponding diagram is:

```{image} /_static/Shunt_Line.svg
:alt: Shunt line diagram
:width: 1000px
:align: center
```

```{math}
V_1 &= a \cdot V_2 - b \cdot I_2 + g \cdot V_{\mathrm{g}} \\
I_1 &= c \cdot V_2 - d \cdot I_2 + h \cdot V_{\mathrm{g}} \\
I_{\mathrm{g}} &= f^t \cdot \left(V_1 + V_2 - 2\cdot V_{\mathrm{g}}\right)
```

where

```{math}
a &= \mathcal{I}_4 + \dfrac{1}{2} \cdot Z \cdot Y  \\
b &= Z  \\
c &= Y + \dfrac{1}{4}\cdot Y \cdot Z \cdot Y  \\
d &= \mathcal{I}_4 + \dfrac{1}{2} \cdot Y \cdot Z  \\
f &= -\dfrac{1}{2} \cdot \begin{pmatrix} y_{\mathrm{ag}} & y_{\mathrm{bg}} & y_{\mathrm{cg}} &
y_{\mathrm{ng}} \end{pmatrix} ^t  \\
g &= Z \cdot f  \\
h &= 2 \cdot f + \frac{1}{2}\cdot Y \cdot Z \cdot f  \\
```

with $Z$ the series impedance matrix and $Y$ the shunt admittance matrix.

## Simplified line model

If the line does not define a shunt admittance, we can simplify the model as there is no coupling with
the ground. With $Y = 0$, the equations become:

```{math}
\left(V_1 - V_2\right) &= Z \cdot I_1 \\
I_2 &= -I_1
```

The corresponding diagram is:


```{image} /_static/Simplified_Line.svg
:alt: Shunt line diagram
:width: 600px
:align: center
```
