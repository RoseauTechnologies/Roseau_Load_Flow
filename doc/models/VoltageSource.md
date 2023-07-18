# Voltage source

It refers to an ideal voltage source, that can maintain a fixed voltage independently of the load resistance
or the output current.

## Star connection

The diagram of the star voltage source is:

````{tab} European standards
```{image} /_static/VoltageSource/European_Star_Voltage_Source.svg
:alt: Star voltage source diagram
:width: 400px
:align: center
```
````
````{tab} American standards
```{image} /_static/VoltageSource/American_Star_Voltage_Source.svg
:alt: Star voltage source diagram
:width: 400px
:align: center
```
````
The equations associated to the star voltage source are the following:

```{math}
\left\{
    \begin{split}
        \underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{n}}} &= \underline{U_{\mathrm{an}}} \\
        \underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{n}}} &= \underline{U_{\mathrm{bn}}} \\
        \underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{n}}} &= \underline{U_{\mathrm{cn}}}
    \end{split}
\right.
```

Where $\underline{U}\in\mathbb{C}^3$ is the voltages (user defined parameters) and $\underline{V}\in\mathbb{C}^4$
are the node potentials (variables).


## Delta connection

The diagram of the delta voltage source is:

````{tab} European standards
```{image} /_static/VoltageSource/European_Delta_Voltage_Source.svg
:alt: Delta voltage source diagram
:width: 400px
:align: center
```
````
````{tab} American standards
```{image} /_static/VoltageSource/American_Delta_Voltage_Source.svg
:alt: Delta voltage source diagram
:width: 400px
:align: center
```
````
The equations associated to the delta voltage source are the following:

```{math}
\left\{
    \begin{split}
        \underline{V_{\mathrm{a}}}-\underline{V_{\mathrm{b}}} &= \underline{U_{\mathrm{ab}}} \\
        \underline{V_{\mathrm{b}}}-\underline{V_{\mathrm{c}}} &= \underline{U_{\mathrm{bc}}} \\
        \underline{V_{\mathrm{c}}}-\underline{V_{\mathrm{a}}} &= \underline{U_{\mathrm{ca}}}
    \end{split}
\right.
```

Where $\underline{U}\in\mathbb{C}^3$ are the voltages (user defined parameters) and $\underline{V}\in\mathbb{C}^3$
are the node potentials (variables).
