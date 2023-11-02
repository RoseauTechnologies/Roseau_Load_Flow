# Installation

Please select one of the following installation methods that best suits your workflow.

```{note}
If you are a beginner in Python, please note that the commands below must be executed in a
**terminal**, not in the _Python console_. This is indicated by the `$` or `C:>` prompt as opposed
to the Python console prompt `>>>`.
```

## 1. Using `pip`

`roseau-load-flow` is available on [PyPI](https://pypi.org/project/roseau-load-flow/). It can be
installed using pip with:

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
It is recommended to work in a virtual environment to isolate your project. Create and activate a virtual environment before installing the package. You can create one with:

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

Optional dependencies can be installed using the available extras. These are only needed if you use
the corresponding functions. They can be installed with the
`python -m pip install roseau-load-flow[EXTRA]` command where `EXTRA` is one of the following:

1. `plot`: installs _matplotlib_ for the plotting functions
2. `graph` installs _networkx_ for graph theory analysis functions

## 2. Using `pip` in Jupyter Notebooks

If you are using Jupyter Notebooks, you can install `roseau-load-flow` directly from a notebook
cell with:

```ipython3
In [1]: %pip install roseau-load-flow
```

This installs the package in the correct environment for the active notebook kernel.

## 3. Using `conda`

`roseau-load-flow` is also available on [conda-forge](https://anaconda.org/conda-forge/roseau-load-flow).
It can be installed using conda with:

````{tab} Windows

```doscon
C:> conda install -c conda-forge roseau-load-flow
```

````

````{tab} Linux/MacOS

```console
$ conda install -c conda-forge roseau-load-flow
```

````

This installs the package and all its required and optional dependencies.

```{tip}
If you use *conda* to manage your project, it is recommended to use the `conda` package manager
instead of `pip`.
```

<!-- Local Variables: -->
<!-- mode: markdown -->
<!-- coding: utf-8-unix -->
<!-- fill-column: 100 -->
<!-- ispell-local-dictionary: "english" -->
<!-- End: -->
