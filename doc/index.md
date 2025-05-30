---
myst:
  html_meta:
    description lang=en: |
      Documentation of the Roseau Load Flow solver. Multi-phase, unbalanced power flow analysis with a performance optimized solver. Free academic licence and demo version available !
    keywords lang=en: power flow, Roseau, Load flow, python, distribution grid, three-phase, multiphase, unbalanced
    # spellchecker:off
    description lang=fr: |
      Documentation du solveur d'écoulements de charge Roseau Load Flow. Simulation des réseaux électriques
      multiphasés et déséquilibrés par Roseau Technologies. Licences académiques offertes.
    keywords lang=fr: |
      Roseau, load flow, python, écoulement de charge, écoulement de puissance, réseau de distribution, triphasé, power flow
      déséquilibré
    # spellchecker:on
---

# Welcome to the Roseau Load Flow documentation

```{include} ../README.md
---
start-after: <!-- start rlf-pitch -->
end-before: <!-- end rlf-pitch -->
---
```

```{include} ../README.md
---
start-after: <!-- start rlf-networks -->
end-before: <!-- end rlf-networks -->
---
```

<iframe src="./_static/Network/Catalogue.html" height="600px" width="100%" frameborder="0"></iframe>

More details are given in the [Catalogues page](catalogues-networks).

## Installation

`roseau-load-flow` is the python interface to the power flow solver. It is compatible with Python version 3.11 and newer
and can be installed with:

```{toctree}
---
maxdepth: 2
caption: Installation and License
---
Installation
```

## License

Read more about the license of this project:

```{toctree}
---
maxdepth: 2
---
License
```

## Usage

The following tutorials are available to help you get started:

```{toctree}
---
maxdepth: 2
caption: Usage
---
usage/index
```

## Models

A description of the electrical models used for each component, an example usage, and a reference to the API of the
classes are available here:

```{toctree}
---
maxdepth: 2
caption: Models
---
models/index
```

## Advanced

Advanced concepts, edge cases and more are explained in this section:

```{toctree}
---
maxdepth: 2
caption: Advanced
---
advanced/index
```

## Changelog

```{toctree}
---
maxdepth: 2
caption: More
---
Changelog
```

## API Reference

If you want the full documentation of all the classes and functions, you can refer to the following references:

```{toctree}
---
maxdepth: 2
---
autoapi/roseau/load_flow/index
```
