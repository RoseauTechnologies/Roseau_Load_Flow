![CI](https://github.com/RoseauTechnologies/thunders/workflows/CI/badge.svg)

# Thunders #

## Installation ##

`Thunders` requires a few additional libraries which can be installed with:

``` bash
sudo apt install libspdlog-dev libfmt-dev libeigen3-dev libcppad-dev
```

### As a dependency of a project via `poetry` ###

```toml
[[tool.poetry.source]]
name = "roseau"
url = "https://gitlab.com/api/v4/projects/21838126/packages/pypi/simple"
secondary = true

[tool.poetry.dependencies]
#...
thunders = { version = ">=0.4.0", source = "roseau" }
```

Le Pypi repository `roseau` is a private repository. An authentication is required. Do not forget to apply
a `poetry update` after that.

### To develop via Git ###

First, clone this repository:

```bash
git clone git@github.com:RoseauTechnologies/thunders.git
cd thunders
```

Then, create your virtual environment and activate it.

Use the following command to install `Thunders`:

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

en = ElectricalNetwork.from_files(  # CSV (deprecated)
    buses=buses,
    branches=branches,
    loads=loads,
    lines=lines,
    transformers=transformers,
    voltages=voltages,
    load_point=load_point
)

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
    id_="source",
    n=4,
    ground=ground,
    voltages=voltages,
)
load_bus = Bus(id_="load bus", n=4)
load = PowerLoad(id_="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
line_characteristics = LineCharacteristics(type_name="test", z_line=np.eye(4, dtype=complex))
line = SimplifiedLine(
    id_="line",
    n=4,
    bus1=vs,
    bus2=load_bus,
    line_characteristics=line_characteristics,
    length=10  # km
)
p_ref = PotentialRef(element=ground)

en = ElectricalNetwork(buses=[vs, load_bus], branches=[line], loads=[load], special_elements=[p_ref, ground])
# or
en = ElectricalNetwork.from_element(vs)

en.solve_load_flow()
```

<!-- Local Variables: -->
<!-- mode: gfm -->
<!-- coding: utf-8-unix -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
