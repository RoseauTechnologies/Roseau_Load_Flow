---
myst:
  html_meta:
    "description lang=en": |
      Learn about advanced concepts around the potential reference point of electric network for a
      load flow calculation with Roseau Load Flow.
    "description lang=fr": |
      Découvrez les concepts avancés autour du point de référence potentiel du réseau électrique
      pour un calcul d'écoulement de charge avec Roseau Load Flow.
    "keywords lang=fr": simulation, réseau, électrique,  potentiel, référence, origine de tension
    "keywords lang=en": simulation, power grid, potentials, reference, voltage origin
---

(advanced-pref)=

# Potential Reference

## Introduction

A voltage is a difference in electric potential between two points in space. It represents the
energy required to move a unit of electric charge from a reference point to a specific point. In
electrical engineering, the electric potential of nodes is calculated relative to a chosen reference
point. While the reference point is often the earth, it can be any point in the network. The choice
of the reference point does not impact the physical behavior of the network, but it does affect the
numerical values of the electric potentials in the network.

In the power system, transformers are used to connect different parts of the network without direct
conduction of electric current between these parts, except for autotransformers. A transformer thus
isolates the electric potentials of its different sides. This isolation, called galvanic isolation,
allows the electric potentials of the different sides of a transformer to be set independently.
This means that networks might have different reference points for the electric potentials. More
precisely, a network must have a reference point for each galvanically isolated section.

## Potential reference in Roseau Load Flow

In _Roseau Load Flow_, the definition of the reference point for the electric potentials is managed
by the {class}`~roseau.load_flow.PotentialRef` element. The potential reference is decoupled from
the "earth" that is represented by the {class}`~roseau.load_flow.Ground` element. This decoupling
gives more flexibility in terms of the choice of the reference point for the electric potentials in
the network. There are three ways to set the reference point for the electric potentials in the
network.

1. Settting the potential reference with a ground
2. Settting the potential reference with a specific node and phase
3. Settting the potential reference with a specific node and two or more phases

### Reference with a ground

This covers the most common case where the earth is considered as the reference point. In this case,
the potential of the ground is fixed at $0V$ and the electric potentials of the other nodes are
computed relative to the ground.

```python
import roseau.load_flow as rlf

# Create a bus with a voltage source
bus = rlf.Bus("Bus", phases="abcn")
source = rlf.VoltageSource("Source", bus=bus, voltages=230)
# Create a ground and a potential reference connected to the ground
ground = rlf.Ground("Ground")
pref = rlf.PotentialRef("PotentialRef", element=ground)
# Connect the ground to any phase of the bus, here the neutral
ground.connect(bus=bus, phase="n")
en = rlf.ElectricalNetwork.from_element(bus)
en.solve_load_flow()

# The potential of the ground is guaranteed to be 0V
print(ground.res_potential)  # 0j volt
# Consequently, the potential of neutral is also 0V
print(bus.res_potentials[3])  # 0j volt
# The potential of phase "a" is 230V relative to the reference (ground/neutral)
print(bus.res_potentials[0])  # (230+0j) volt
# The voltage Van is also 230V: Van = Va - Vn = (230+0j) - 0j = (230+0j) volt
print(bus.res_voltages[0])  # (230+0j) volt
```

### Reference with a specific node and phase

In this case, the reference point is a particular phase of a node (bus). The potential of the
reference phase is fixed at $0V$ and the electric potentials of the other phases are computed
relative to the reference phase.

```python
import roseau.load_flow as rlf

# Create a bus with a voltage source
bus = rlf.Bus("Bus", phases="abcn")
source = rlf.VoltageSource("Source", bus=bus, voltages=230)
# Create a potential reference connected to phase "n" of the bus
pref = rlf.PotentialRef("PotentialRef", element=bus, phases="n")
en = rlf.ElectricalNetwork.from_element(bus)
en.solve_load_flow()

# The potential Vn is guaranteed to be 0V, the potential Va is (230+0j) volt
print(bus.res_potentials)  # [230+0j, -115-199.1858j, -115+199.1858j, 0j] volt
print(abs(bus.res_potentials))  # [230.0, 230.0, 230.0, 0.0] volt
# The voltages Van, Vbn, and Vcn are 230V as defined by the source
print(bus.res_voltages)  # [230+0j, -115-199.1858j, -115+199.1858j] volt
print(abs(bus.res_voltages))  # [230.0, 230.0, 230.0] volt
```

Choosing another phase as the reference point will change the numerical values of the electric
potentials but not the values of the voltages.

```python
import roseau.load_flow as rlf

# Create a bus with a voltage source
bus = rlf.Bus("Bus", phases="abcn")
source = rlf.VoltageSource("Source", bus=bus, voltages=230)
# Create a potential reference connected to phase "a" of the bus
pref = rlf.PotentialRef("PotentialRef", element=bus, phases="a")
en = rlf.ElectricalNetwork.from_element(bus)
en.solve_load_flow()

# The potential Va is guaranteed to be 0V, the potential Vn becomes (-230+0j) volt
print(bus.res_potentials)  # [0+0j, -345-199.1858j, -345+199.1858j, -230+0j] volt
print(abs(bus.res_potentials))  # [0.0, 398.3717, 398.3717, 230.0] volt
# The voltages Van, Vbn, and Vcn are still 230V
print(bus.res_voltages)  # [230+0j, -115-199.1858j, -115+199.1858j] volt
print(abs(bus.res_voltages))  # [230.0, 230.0, 230.0] volt
```

### Reference with a specific node and two or more phases

In this case, the reference point is not a physical point in the network but a virtual point defined
by the sum of the potentials of two or more phases of a node (bus). The reference potential of $0V$
is defined as the sum of the potentials of the reference phases.

```python
import roseau.load_flow as rlf

# Create a bus with a voltage source
bus = rlf.Bus("Bus", phases="abcn")
source = rlf.VoltageSource("Source", bus=bus, voltages=230)
# Create a potential reference with phases "a" and "b" of the bus
pref = rlf.PotentialRef("PotentialRef", element=bus, phases="ab")
en = rlf.ElectricalNetwork.from_element(bus)
en.solve_load_flow()

# The potential of the midpoint between phases "a" and "b" is guaranteed to be 0V
print(bus.res_potentials[0] + bus.res_potentials[1])  # 0j volt
# The potential of phase "b" is thus the negative of that of phase "a"
print(bus.res_potentials[:2])  # [172.5+99.5929j, -172.5-99.5929j] volt
# The potential of phase "c" is 1.5x 230V, 3x the potential of "n"
print(abs(bus.res_potentials[2:]))  # [345.0, 115.0] volt
# The voltages Van, Vbn, and Vcn are still 230V as defined by the source
print(abs(bus.res_voltages))  # [230.0, 230.0, 230.0] volt
```

## Galvanic isolation and potential references

In a network with galvanic isolation as mentioned in the introduction, the electric potentials of
the different sections of the network are independent. For instance, consider a MV/LV transformer
with a neutral point on the LV side. Consider that the neutral point of the LV side is connected to
the ground while the MV side does not have a neutral point. In this case, the electric potentials
of the MV and LV sides of the transformer can be set as follows:

```python
import roseau.load_flow as rlf

# Create MV and LV buses with an MV source
mv_bus = rlf.Bus("MVBus", phases="abc")
lv_bus = rlf.Bus("LVBus", phases="abcn")
rlf.VoltageSource("MVSource", bus=mv_bus, voltages=20e3)

# Create a delta-wye transformer connecting the MV and LV buses
tp = rlf.TransformerParameters.from_catalogue("SE Minera AA0Ak 160kVA 20kV 410V Dyn11")
rlf.Transformer("MV/LV Transformer", bus1=mv_bus, bus2=lv_bus, parameters=tp)

# Define the potential references for the MV and LV sides
rlf.PotentialRef("MV PotentialRef", element=mv_bus)  # by default, phases="abc"
rlf.PotentialRef("LV PotentialRef", element=lv_bus)  # by default, phases="n"

en = rlf.ElectricalNetwork.from_element(mv_bus)
en.solve_load_flow()

# The potential of the neutral of the LV side is guaranteed to be 0V
print(lv_bus.res_potentials[3])  # 0j volt
# The sum of the potentials of the phases of the MV side is 0V
print(mv_bus.res_potentials.sum())  # 0j volt
```

In this example, it is not possible to set a single reference point for the electric potentials of
the MV and LV sides of the transformer. This is a very simple example that clearly illustrates the
concept of galvanic isolation. In a real MV/LV network, both sides may be connected to a common
ground through the shunt components of their lines or the neutral point of the transformer. In this
case, the two sides of the transformer are not galvanically isolated, and the electric potentials
of the two sides must be set relative to a common reference point:

```python
import roseau.load_flow as rlf

# Create 2 MV and 2 LV buses with a MV source
mv_bus1 = rlf.Bus("MVBus1", phases="abc")
mv_bus2 = rlf.Bus("MVBus2", phases="abc")
lv_bus1 = rlf.Bus("LVBus1", phases="abcn")
lv_bus2 = rlf.Bus("LVBus2", phases="abcn")
rlf.VoltageSource("Source", bus=mv_bus1, voltages=20_000)

# Create a delta-wye transformer connecting the MV and LV buses
tp = rlf.TransformerParameters.from_catalogue("SE Minera AA0Ak 160kVA 20kV 410V Dyn11")
rlf.Transformer("MV/LV Transformer", bus1=mv_bus1, bus2=lv_bus1, parameters=tp)

# Create a common ground for the MV and LV sides
ground = rlf.Ground("Ground")
mv_lp = rlf.LineParameters.from_catalogue("U_AL_150", nb_phases=3)
rlf.Line("MV Line", bus1=mv_bus1, bus2=mv_bus2, length=1, parameters=mv_lp, ground=ground)
lv_lp = rlf.LineParameters.from_catalogue("U_AL_70", nb_phases=4)
rlf.Line(
    "LV Line", bus1=lv_bus1, bus2=lv_bus2, length=0.1, parameters=lv_lp, ground=ground
)

# Create a common potential reference for the MV and LV sides
rlf.PotentialRef("PotentialRef", element=mv_bus1)

en = rlf.ElectricalNetwork.from_element(mv_bus1)
en.solve_load_flow()  # OK
```

Trying to set another reference point for the electric potentials in this network will result in an
error because the network is galvanically connected through the common ground:

```python
# Adding this line to the above network will raise an error
rlf.PotentialRef("PotentialRef2", element=lv_bus1)
# RoseauLoadFlowException: The connected component containing the element 'LVBus2'
# has 2 potential references, it should have only one. [several_potential_reference]
```

This can be worked around by creating separate ground elements for the MV and LV sides:

```python
import roseau.load_flow as rlf

# Create 2 MV and 2 LV buses with a MV source
mv_bus1 = rlf.Bus("MVBus1", phases="abc")
mv_bus2 = rlf.Bus("MVBus2", phases="abc")
lv_bus1 = rlf.Bus("LVBus1", phases="abcn")
lv_bus2 = rlf.Bus("LVBus2", phases="abcn")
rlf.VoltageSource("Source", bus=mv_bus1, voltages=20_000)

# Create a delta-wye transformer connecting the MV and LV buses
tp = rlf.TransformerParameters.from_catalogue("SE Minera AA0Ak 160kVA 20kV 410V Dyn11")
rlf.Transformer("MV/LV Transformer", bus1=mv_bus1, bus2=lv_bus1, parameters=tp)

# Create separate grounds for the MV and LV sides
mv_ground = rlf.Ground("MVGround")
mv_lp = rlf.LineParameters.from_catalogue("U_AL_150", nb_phases=3)
rlf.Line(
    "MV Line", bus1=mv_bus1, bus2=mv_bus2, length=1, parameters=mv_lp, ground=mv_ground
)
lv_ground = rlf.Ground("LVGround")
lv_lp = rlf.LineParameters.from_catalogue("U_AL_70", nb_phases=4)
rlf.Line(
    "LV Line", bus1=lv_bus1, bus2=lv_bus2, length=0.1, parameters=lv_lp, ground=lv_ground
)

# Create separate potential references for the MV and LV sides
rlf.PotentialRef("MVPotentialRef", element=mv_bus1)
rlf.PotentialRef("LVPotentialRef", element=lv_bus1)

en = rlf.ElectricalNetwork.from_element(mv_bus1)
en.solve_load_flow()  # OK
```
