![CI](https://github.com/RoseauTechnologies/Roseau_Load_Flow/workflows/CI/badge.svg)
[![Documentation](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/doc.yml/badge.svg)](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/doc.yml)
[![pre-commit](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/pre-commit.yml)

# Roseau Load Flow #

## Installation ##

The simplest way is to download the docker container attached to this repository and to start it. I will start a
Jupyterlab session with all the required packages installed.

The entire documentation is available via [GitHub pages](https://roseautechnologies.github.io/Roseau_Load_Flow/)

## Usage ##

There are 2 main ways to execute a load flow:

### From files ###

By giving path to the needed files:

```python
from roseau.load_flow import ElectricalNetwork

en = ElectricalNetwork.from_dgs(path=path)  # DGS

en = ElectricalNetwork.from_json(path=path)  # Json

en.solve_load_flow(auth=("username", "password"))
```

### From code ###

By describing the network and its components, here is a simple example:

```python
from roseau.load_flow import Ground, VoltageSource, Bus, PowerLoad, PotentialRef, SimplifiedLine, ElectricalNetwork, LineCharacteristics
import numpy as np

ground = Ground()
vn = 400 / np.sqrt(3)
voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
vs = VoltageSource(
    id="source",
    n=4,
    ground=ground,
    source_voltages=voltages,
)
load_bus = Bus(id="load bus", n=4)
load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
line_characteristics = LineCharacteristics(type_name="test", z_line=np.eye(4, dtype=complex))
line = SimplifiedLine(
    id="line",
    n=4,
    bus1=vs,
    bus2=load_bus,
    line_characteristics=line_characteristics,
    length=10  # km
)
p_ref = PotentialRef(element=ground)

en = ElectricalNetwork(buses=[vs, load_bus], branches=[line], loads=[load], special_elements=[p_ref, ground])
# or
# en = ElectricalNetwork.from_element(vs)

en.solve_load_flow(auth=("username", "password"))
```

<!-- Local Variables: -->
<!-- mode: gfm -->
<!-- coding: utf-8-unix -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
