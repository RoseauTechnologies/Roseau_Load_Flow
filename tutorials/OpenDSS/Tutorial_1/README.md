# Modelling and analyzing a simple unbalanced network with Roseau Load Flow solver

This tutorial is meant to introduce the procedure for modelling components of a given low voltage (LV) network using
the _Roseau Load Flow_ solver. It will also cover the process of running a power flow, accessing results, and analysis
such as voltage regulation and energy losses.

In this tutorial, we use the simple network coming from the tutorial of _OpenDSS_ provided by
[TeamNando](https://github.com/Team-Nando) and called `Tutorial-DERHostingCapacity-1-AdvancedTools_LV`. Cf
[here](https://github.com/Team-Nando/Tutorial-DERHostingCapacity-1-AdvancedTools_LV) for the original tutorial.

This simple LV network is shown in the figure below containing a MV/LV, $\Delta$-Y transformer (20kV/0.4kV,
250 kVA) between the source bus and bus A, a 240 mm², 3-phase line connecting buses A and B, and three 16 mm²
single-phase lines connecting bus B with buses C, D and E each of which serves as a connection point for a house.

!["Simple LV network"](../images/LV_Network_With_Neutral.png)
**<div style="text-align: center;"> Figure 1. Simple LV Network</div>**
