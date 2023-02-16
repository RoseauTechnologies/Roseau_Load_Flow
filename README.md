![CI](https://github.com/RoseauTechnologies/Roseau_Load_Flow/workflows/CI/badge.svg)
[![Documentation](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/doc.yml/badge.svg)](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/doc.yml)
[![pre-commit](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/pre-commit.yml)

# Roseau Load Flow #

## Installation ##

The simplest way is to download the docker container attached to this repository and to start it.
It will start a Jupyterlab session with all the required packages installed.

The project can also be installed via `pip` or `conda`. Please see the [Installation](https://roseautechnologies.github.io/Roseau_Load_Flow/installation.html) page for more details.

## Documentation ##

The documentation contianing the installation instructions, tutorials, and the API index is
available at https://roseautechnologies.github.io/Roseau_Load_Flow/

## Usage ##

There are 2 main ways to execute a load flow:

### From files ###

By giving path to the needed files:

```python
from roseau.load_flow import ElectricalNetwork

en = ElectricalNetwork.from_json(path="./data/my-network.json")

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
    LineParameters,
    PotentialRef,
    PowerLoad,
    VoltageSource,
)

# Create a ground connection and a potential reference
ground = Ground(id="g")  # A ground connection
p_ref = PotentialRef(id="pr", element=ground)  # A potential reference

# Create a main bus and a source
vn = 400 / np.sqrt(3)
voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
source_bus = Bus(id="sb", phases="abcn")
ground.connect(source_bus)  # The neutral of the main bus is connected to the ground
vs = VoltageSource(id="vs", bus=source_bus, phases="abcn", voltages=voltages)

# Create a load bus and a load
load_bus = Bus(id="lb", phases="abcn")
load = PowerLoad(id="pl", bus=load_bus, phases="abcn", powers=[100 + 0j, 100 + 0j, 100 + 0j])

# Create a line between the two buses
lp = LineParameters("lp_series", z_line=np.eye(4, dtype=complex))
line = Line(id="l", bus1=source_bus, bus2=load_bus, phases="abcn", parameters=lp, length=10)

# Create the network from these elements
en = ElectricalNetwork(
    buses=[source_bus, load_bus],
    branches=[line],
    loads=[load],
    sources=[vs],
    grounds=[ground],
    potential_refs=[p_ref],
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
