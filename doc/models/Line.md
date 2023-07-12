# Lines

## Matrices definition

Before describing the different line models, we first have to define the series impedance matrix, noted $Z$, and the
shunt admittance matrix, noted $Y$.

### Series impedance matrix

The series impedance matrix $Z$, in $\Omega$, is composed of the resistance of the conductors ($R\in{\mathbb{R}^+}
^4$),
the self-inductances ($L\in\mathbb{R}^4$) and the mutual inductances ($M\in\mathbb{R}^{12}$).

```{math}
\begin{aligned}
    Z &= R + j \cdot X \\
    Z &= \begin{pmatrix}
        Z_{\mathrm{aa}} & Z_{\mathrm{ab}} & Z_{\mathrm{ac}} & Z_{\mathrm{an}}\\
        Z_{\mathrm{ba}} & Z_{\mathrm{bb}} & Z_{\mathrm{bc}} & Z_{\mathrm{bn}}\\
        Z_{\mathrm{ca}} & Z_{\mathrm{cb}} & Z_{\mathrm{cc}} & Z_{\mathrm{cn}}\\
        Z_{\mathrm{na}} & Z_{\mathrm{nb}} & Z_{\mathrm{nc}} & Z_{\mathrm{nn}}\\
    \end{pmatrix}\\
    Z &= \underbrace{
        \begin{pmatrix}
            R_{\mathrm{a}} & 0 & 0 & 0\\
            0 & R_{\mathrm{b}} & 0 & 0\\
            0 & 0 & R_{\mathrm{c}} & 0\\
            0 & 0 & 0 & R_{\mathrm{n}}\\
        \end{pmatrix}
    }_{R} + j \cdot \underbrace{
        \omega \cdot
        \begin{pmatrix}
            L_{\mathrm{a}} & M_{\mathrm{ab}} & M_{\mathrm{ac}} & M_{\mathrm{an}}\\
            M_{\mathrm{ba}} & L_{\mathrm{b}} & M_{\mathrm{bc}} & M_{\mathrm{bn}}\\
            M_{\mathrm{ca}} & M_{\mathrm{cb}} & L_{\mathrm{c}} & M_{\mathrm{cn}}\\
            M_{\mathrm{na}} & M_{\mathrm{nb}} & M_{\mathrm{nc}} & L_{\mathrm{n}}\\
        \end{pmatrix}
    }_{X}
\end{aligned}
```

### Admittance matrix

```{warning}
The admittance matrix $y$ shouldn't be confused with the shunt admittance matrix $Y$.
```

$y$ represents the admittances between each node, while $Y$ is used to compute the currents and
voltages.

```{math}
\begin{aligned}
    y &= G + j \cdot B \\
    y &= \begin{pmatrix}
        y_{\mathrm{ag}} & y_{\mathrm{ab}} & y_{\mathrm{ac}} & y_{\mathrm{an}}\\
        y_{\mathrm{ab}} & y_{\mathrm{bg}} & y_{\mathrm{bc}} & y_{\mathrm{bn}}\\
        y_{\mathrm{ac}} & y_{\mathrm{bc}} & y_{\mathrm{cg}} & y_{\mathrm{cn}}\\
        y_{\mathrm{an}} & y_{\mathrm{bn}} & y_{\mathrm{cn}} & y_{\mathrm{ng}}
    \end{pmatrix}\\
    y &= \underbrace{
        \begin{pmatrix}
            G_{\mathrm{a}} & 0 & 0 & 0\\
            0 & G_{\mathrm{b}} & 0 & 0\\
            0 & 0 & G_{\mathrm{c}} & 0\\
            0 & 0 & 0 & G_{\mathrm{n}}
        \end{pmatrix}
    }_{G} + j \cdot \underbrace{
        \omega \cdot
        \begin{pmatrix}
          C_{\mathrm{a}} & C_{\mathrm{ab}} & C_{\mathrm{ac}} & C_{\mathrm{an}}\\
          C_{\mathrm{ab}} & C_{\mathrm{b}} & C_{\mathrm{bc}} & C_{\mathrm{bn}}\\
          C_{\mathrm{ac}} & C_{\mathrm{bc}} & C_{\mathrm{c}} & C_{\mathrm{cn}}\\
          C_{\mathrm{an}} & C_{\mathrm{bn}} & C_{\mathrm{cn}} & C_{\mathrm{n}}
        \end{pmatrix}
    }_{B}
\end{aligned}
```

with $G\in\mathbb{R}^4$ the conductance of the line, $B\in\mathbb{R}^4$ the susceptance of the line and
$C\in\mathbb{R}^{16}$ the transverse susceptances of the line.

### Shunt admittance matrix

The shunt admittance matrix $Y$ is defined from the admittance matrix $y$ as:

```{math}
Y =
\begin{pmatrix}
  Y_{\mathrm{aa}} & Y_{\mathrm{ab}} & Y_{\mathrm{ac}} & Y_{\mathrm{an}}\\
  Y_{\mathrm{ba}} & Y_{\mathrm{bb}} & Y_{\mathrm{bc}} & Y_{\mathrm{bn}}\\
  Y_{\mathrm{ca}} & Y_{\mathrm{cb}} & Y_{\mathrm{cc}} & Y_{\mathrm{cn}}\\
  Y_{\mathrm{na}} & Y_{\mathrm{nb}} & Y_{\mathrm{nc}} & Y_{\mathrm{nn}}\\
\end{pmatrix}
\quad \text{with} \quad
\left\{
  \begin{aligned}
    Y_{ii} &= \sum_{k\in\{\mathrm{a},\mathrm{b},\mathrm{c},\mathrm{n},\mathrm{g}\}}{y_{ik}}\\
    Y_{ij} &= -y_{ij}\\
  \end{aligned}
\right.\text{, }\forall(i,j)\in\{\mathrm{a},\mathrm{b},\mathrm{c},\mathrm{n}\}^2
```

## Shunt line model

The first model of line which can be used is a PI model with series impedance and shunt admittance. The
corresponding diagram is:

````{tab} European standards
```{image} /_static/Line/European_Shunt_Line.svg
:alt: Shunt line diagram
:width: 1000px
:align: center
```
````
````{tab} American standards
```{image} /_static/Line/American_Shunt_Line.svg
:alt: Shunt line diagram
:width: 1000px
:align: center
```
````

The corresponding equations are:

```{math}
\left\{
    \begin{aligned}
        V_1 &= a \cdot V_2 - b \cdot I_2 + g \cdot V_{\mathrm{g}} \\
        I_1 &= c \cdot V_2 - d \cdot I_2 + h \cdot V_{\mathrm{g}} \\
        I_{\mathrm{g}} &= f^t \cdot \left(V_1 + V_2 - 2\cdot V_{\mathrm{g}}\right)
    \end{aligned}
\right.
```

where

```{math}
\left\{
    \begin{aligned}
        a &= \mathcal{I}_4 + \dfrac{1}{2} \cdot Z \cdot Y  \\
        b &= Z  \\
        c &= Y + \dfrac{1}{4}\cdot Y \cdot Z \cdot Y  \\
        d &= \mathcal{I}_4 + \dfrac{1}{2} \cdot Y \cdot Z  \\
        f &= -\dfrac{1}{2} \cdot \begin{pmatrix} y_{\mathrm{ag}} & y_{\mathrm{bg}} & y_{\mathrm{cg}} &
        y_{\mathrm{ng}} \end{pmatrix} ^t  \\
        g &= Z \cdot f  \\
        h &= 2 \cdot f + \frac{1}{2}\cdot Y \cdot Z \cdot f  \\
    \end{aligned}
\right.
```

with $Z$ the series impedance matrix and $Y$ the shunt admittance matrix.

## Simplified line model

If the line does not define a shunt admittance, we can simplify the model as there is no coupling with
the ground. With $Y = 0$, the equations become:

```{math}
\left\{
    \begin{aligned}
        V_1 - V_2 &= Z \cdot I_1 \\
        I_2 &= -I_1
    \end{aligned}
\right.
```

The corresponding diagram is:

````{tab} European standards
```{image} /_static/Line/European_Simplified_Line.svg
:alt: Simplified line diagram
:width: 600px
:align: center
```
````
````{tab} American standards
```{image} /_static/Line/American_Simplified_Line.svg
:alt: Simplified line diagram
:width: 600px
:align: center
```
````
