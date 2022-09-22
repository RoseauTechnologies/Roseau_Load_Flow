![CI](https://github.com/RoseauTechnologies/Roseau_Load_Flow/workflows/CI/badge.svg)

# Roseau Load Flow #

## Installation ##

### As a dependency of a project via `poetry` ###

```toml
[[tool.poetry.source]]
name = "roseau"
url = "https://gitlab.com/api/v4/projects/21838126/packages/pypi/simple"
secondary = true
default = false

[tool.poetry.dependencies]
#...
roseau_load_flow = { version = ">=0.1.0", source = "roseau" }
```

Le Pypi repository `roseau` is a private repository. An authentication is required. Do not forget to apply
a `poetry update` after that.

### To develop via Git ###

First, clone this repository:

```bash
git clone git@github.com:RoseauTechnologies/Roseau_Load_Flow.git
cd Roseau_Load_Flow
```

Then, create your virtual environment and activate it.

Use the following command to install `Roseau Load Flow`:

```bash
poetry install
```

## Usage ##

There are 2 main ways to execute a load flow with thunders:

### From files ###

By giving path to the needed files:

```python
from roseau.load_flow import ElectricalNetwork

en = ElectricalNetwork.from_dgs(path=path)  # DGS

en = ElectricalNetwork.from_json(path=path)  # Json

en.solve_load_flow()
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
    voltages=voltages,
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

en.solve_load_flow()
```

<!-- Local Variables: -->
<!-- mode: gfm -->
<!-- coding: utf-8-unix -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
