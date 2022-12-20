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
import numpy as np

from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    Ground,
    Line,
    LineCharacteristics,
    PotentialRef,
    PowerLoad,
    VoltageSource,
)

# Create a main bus and a voltage source
ground = Ground("ground")  # A ground connection
p_ref = PotentialRef("pref", element=ground)  # A potential reference
vn = 400 / np.sqrt(3)
voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
source_bus = Bus(id="source bus", phases="abcn")
ground.connect_to_bus(source_bus)
vs = VoltageSource(id="source", phases="abcn", bus=source_bus, voltages=voltages)

# Create a load bus and a load
load_bus = Bus(id="load bus", phases="abcn")
load = PowerLoad(id="power load", phases="abcn", bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])

# Create a line between the two buses
line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
line = Line(
    id="line",
    phases="abcn",
    bus1=source_bus,
    bus2=load_bus,
    line_characteristics=line_characteristics,
    length=10,  # km
)

# Create the network from these elements
en = ElectricalNetwork(
    buses=[source_bus, load_bus],
    branches=[line],
    loads=[load],
    voltage_sources=[vs],
    special_elements=[p_ref, ground],
)
# or simply using the main bus
# en = ElectricalNetwork.from_element(source_bus)

# Solve the load flow
en.solve_load_flow(auth=("username", "password"))
```

<!-- Local Variables: -->
<!-- mode: gfm -->
<!-- coding: utf-8-unix -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
