# Modelling and Analysis of a Simple Unbalanced LV Network

## Introduction

This tutorial will demonstrate how to model an unbalanced LV network with _Roseau Load Flow (RLF)_ solver. We use
the simple network coming from the tutorial of _OpenDSS_ provided by
[TeamNando](https://github.com/Team-Nando) and called `Tutorial-DERHostingCapacity-1-AdvancedTools_LV`. Cf
[here](https://github.com/Team-Nando/Tutorial-DERHostingCapacity-1-AdvancedTools_LV) for the original tutorial.

Before attempting this tutorial, you should have finished "Tutorial 1" in this repository for a basic knowledge of
how the _RLF_ solver works. We'll be using a modified form of the network in Tutorial 1. The network consists of an
MV bus, a MV/LV, $\Delta$-Y transformer (11kV/0.4kV, 250 kVA) between the source bus and bus A, a 240 mm² 3-phase
line connecting buses A and B, and three 16 mm² single-phase lines connecting bus B with buses C, D and E each of
which serves as a connection point for a house.

The [original tutorial](https://github.com/Team-Nando/Tutorial-DERHostingCapacity-1-AdvancedTools_LV) uses _OpenDSS_
to model this LV network using an earth return system as depicted in Figure 1.

!["Simple LV Network with Earth Return System"](../images/LV_Network_Without_Neutral.png)
**<div style="text-align: center;"> Figure 1. Simple LV Network with Earth Return System</div>**

This first tutorial allows the user of _RLF_ to get the same results as in the original tutorial.

In a second tutorial, we propose to add a neutral to this network as depicted in Figure 2.

!["Simple LV Network with a Neutral"](../images/LV_Network_With_Neutral.png)
**<div style="text-align: center;"> Figure 2. Simple LV Network with a Neutral Wire</div>**

The details for the loads in the network are given in the table below.
| Load Name | Phases | Connected bus | Peak Demand (kW) | PF |
| :-------- | :----- | :------------ | :--------------- | :--- |
| Load_1 | 1 | C | 7 | 0.95 |
| Load_2 | 1 | D | 6 | 0.95 |
| Load_3 | 1 | E | 8 | 0.95 |

Because this tutorial focuses on the _RLF_ solver, we will only provide a brief overview of how to model the above
network in _OpenDSS_. For a detailed explanation of how to model this network in _OpenDSS_, we refer you to this origin
of this tutorial which is available [here](https://github.com/Team-Nando/Tutorial-DERHostingCapacity-1-AdvancedTools_LV).
