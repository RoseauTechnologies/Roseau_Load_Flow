---
myst:
  html_meta:
    description lang=en: |
      Installation of Roseau Load Flow in a Python environment - Simulation of smart and unbalanced electrical
      distribution networks.
    keywords lang=en: Roseau, Load flow, python, power flow, distribution grid, three-phase, multiphase, unbalanced
    # spellchecker:off
    description lang=fr: |
      Installation de Roseau Load Flow dans un environnement Python - Simulation des réseaux de distribution
      électriques intelligents et déséquilibrés.
    keywords lang=fr: |
      Roseau, load flow, python, écoulement de charge, écoulement de puissance, réseau de distribution, triphasé,
      déséquilibré
    # spellchecker:on
---

# Installation

Please select one of the following installation methods that best suits your workflow.

```{note}
If you are a beginner in Python, please note that the commands below must be executed in a
**terminal**, not in the _Python console_. This is indicated by the `$` or `C:>` prompt as opposed
to the Python console prompt `>>>`.
```

## Using `pip`

`roseau-load-flow` is available on [PyPI](https://pypi.org/project/roseau-load-flow/). It can be installed using pip
with:

````{tab} Windows

```doscon
C:> python -m pip install roseau-load-flow
```

````

````{tab} Linux/MacOS

```console
$ python -m pip install roseau-load-flow
```

````

`````{tip}
It is recommended to work in a virtual environment to isolate your project. Create and activate a virtual environment
before installing the package. You can create one with:

````{tab} Windows

```doscon
C:> python -m venv .venv
```

````

````{tab} Linux/MacOS

```console
$ python -m venv .venv
```

````

A folder named `.venv` will be created. To activate the virtual environment, run:

````{tab} Windows

```doscon
C:> .venv\Scripts\activate
```

````

````{tab} Linux/MacOS

```console
$ source .venv/bin/activate
```

````

`````

To upgrade to the latest version (recommended), use:

````{tab} Windows

```doscon
C:> python -m pip install --upgrade roseau-load-flow
```

````

````{tab} Linux/MacOS

```console
$ python -m pip install --upgrade roseau-load-flow
```

````

Optional dependencies can be installed using the available extras. These are only needed if you use the corresponding
functions. They can be installed with the `python -m pip install roseau-load-flow[EXTRA]` command where `EXTRA` is one
of the following:

1. `plot`: installs _matplotlib_ for the plotting functions
2. `graph` installs _networkx_ for graph theory analysis functions

## Using `pip` in Jupyter Notebooks

If you are using Jupyter Notebooks, you can install `roseau-load-flow` directly from a notebook cell with:

```ipython
In [1]: %pip install roseau-load-flow
```

This installs the package in the correct environment for the active notebook kernel.
