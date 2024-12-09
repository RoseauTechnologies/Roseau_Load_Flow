---
myst:
  html_meta:
    "description lang=en": |
      Documentation of the Roseau Load Flow solver. Simulation of multiphase and unbalanced electrical networks by
      Roseau Technologies.
    "description lang=fr": |
      Documentation du solveur d'écoulements de charge Roseau Load Flow. Simulation des réseaux électriques
      multiphasés et déséquilibrés par Roseau Technologies.
    "keywords lang=fr": |
      Roseau, load flow, python, écoulement de charge, écoulement de puissance, réseau de distribution, triphasé,
      déséquilibré
    "keywords lang=en": Roseau, Load flow, python, power flow, distribution grid, three-phase, multiphase, unbalanced
---

# Welcome to the Roseau Load Flow documentation

_Roseau Load Flow_ is a powerful load flow solver and static analysis tool that offers:

- **Multi-phase**, **unbalanced** power flow analysis
- A performance optimized solver written in C++
- A catalogue of real-world transformer and line models
- An ergonomic object-oriented Python interface with unit-aware quantities
- A comprehensive documentation with code examples
- Real-world distribution network data samples in the library (with more available on request)

In addition to the following **unique** set of features:

- Support for _floating neutrals_ for loads and sources
- Four-wire multi-phase modelling with no Kron's reduction, no transformations, no assumptions on the
  network topology and no implicit earthing everywhere
- Support for **flexible**, voltage-dependent, loads directly in the Newton algorithm for better
  convergence and stability

This software is developed by [Roseau Technologies](https://www.roseautechnologies.com/en).
<a href="https://www.linkedin.com/company/roseau-technologies/"><i class="fa-brands fa-linkedin" ></i></a>
<a href="https://github.com/RoseauTechnologies/"><i class="fa-brands fa-github" ></i></a>

_Roseau Load Flow_ ships with a sample of 20 low-voltage and 20 medium-voltage feeder networks. Each
network is provided with its summer and winter load points. At _Roseau Technologies_, we can provide
the major part of the French medium and low voltage networks on demand. For more information, please
contact us at
[contact@roseautechnologies.com](mailto:contact@roseautechnologies.com).

<iframe src="./_static/Network/Catalogue.html" height="600px" width="100%" frameborder="0"></iframe>

More details are given in the [Catalogues page](catalogues-networks).

## Installation

`roseau-load-flow` is the python interface to the solver. It is compatible with Python version 3.10
and newer and can be installed with:

```{toctree}
:maxdepth: 2
:caption: Installation and License

Installation
```

## License

Read more about the license of this project:

```{toctree}
:maxdepth: 2

License
```

## Usage

The following tutorials are available to help you get started:

```{toctree}
:maxdepth: 2
:caption: Usage

usage/index
```

## Models

A description of the electrical models used for each component, an example usage, and a reference
to the API of the classes are available here:

```{toctree}
:maxdepth: 2
:caption: Models

models/index
```

## Advanced

Advanced concepts, edge cases and more are explained in this section:

```{toctree}
:maxdepth: 2
:caption: Advanced

advanced/index
```

## Changelog

```{toctree}
:maxdepth: 2
:caption: More

Changelog
```

## API Reference

If you want the full documentation of all the classes and functions, you can refer to the following
references:

```{toctree}
:maxdepth: 2

autoapi/roseau/load_flow/index
```
