# Roseau Load Flow

![CI](https://github.com/RoseauTechnologies/Roseau_Load_Flow/workflows/CI/badge.svg)
![pre-commit](https://github.com/RoseauTechnologies/Roseau_Load_Flow/actions/workflows/pre-commit.yml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/roseau-load-flow/badge/?version=latest)](https://roseau-load-flow.readthedocs.io/en/latest/?badge=latest)

<!-- start rlf-pitch -->

_Roseau Load Flow_ is a powerful load flow solver and static analysis tool that offers:

- **Multi-phase**, **unbalanced** power flow analysis
- A performance optimized solver written in C++
- A catalogue of real-world transformer and line models
- An ergonomic object-oriented Python interface with unit-aware quantities
- A comprehensive documentation with code examples
- Real-world distribution network data samples in the library (with more available on request)

In addition to the following **unique** set of features:

- Support for _floating neutrals_ for loads and sources
- Four-wire multi-phase modelling with no Kron's reduction, no transformations, no assumptions on the network topology
  and no implicit earthing everywhere
- Support for **flexible**, voltage-dependent, loads directly in the Newton algorithm for better convergence and
  stability

<!-- end rlf-pitch -->

This project is compatible with Python version 3.11 and newer. The
[installation instructions](https://roseau-load-flow.roseautechnologies.com/en/latest/Installation.html) will guide you
through the installation process. If you are new to _Roseau Load Flow_, we recommend you start with the
[getting started tutorial](https://roseau-load-flow.roseautechnologies.com/en/latest/usage/Getting_Started.html). You
can find the complete documentation at https://roseau-load-flow.roseautechnologies.com/.

## License

This project is _partially_ open source but using the solver requires a license. The license key
`A8C6DA-9405FB-E74FB9-C71C3C-207661-V3` can be used free of charge with networks containing up to 10 buses. To obtain a
personal or commercial license, please contact us at
[contact@roseautechnologies.com](mailto:contact@roseautechnologies.com).

> [!NOTE]
> Licenses are given free of charge for **students and teachers**. Please contact us at contact@roseautechnologies.com
> for more information.

Read more at [License](https://roseau-load-flow.roseautechnologies.com/en/latest/License.html).

## Network data

<!-- start rlf-networks -->

_Roseau Load Flow_ ships with a sample of 20 low-voltage and 20 medium-voltage feeder networks. Each network is provided
with its summer and winter load points.

<!-- start representative-networks -->

We also maintain the 150 MV feeders with their downstream LV networks at
https://github.com/RoseauTechnologies/Representative_French_Power_Grids. These networks are the result of the study
[Départs HTA représentatifs pour l'analyse des réseaux de distribution français](https://www.data.gouv.fr/fr/datasets/departs-hta-representatifs-pour-lanalyse-des-reseaux-de-distribution-francais/),
published by [Mines Paris Tech](https://www.minesparis.psl.eu/). The repository also contains the cluster size that
indicates how representative is each network of the French distribution system.

<!-- end representative-networks -->

<!-- end rlf-networks -->

<div align="center">
  <img alt="Catalogue of networks" src="https://github.com/RoseauTechnologies/Roseau_Load_Flow/blob/main/doc/_static/Network/Catalogue.png?raw=True" />
</div>

## Bug reports / Feature requests

For bug reports, feature requests, or questions, please open an issue on
[GitHub](https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues)

## Credits

This software is developed by [Roseau Technologies](https://www.roseautechnologies.com/en).

Follow us on:
[![Linkedin](https://i.sstatic.net/gVE0j.png) LinkedIn](https://www.linkedin.com/company/roseau-technologies/)
[![GitHub](https://i.sstatic.net/tskMh.png) GitHub](https://github.com/RoseauTechnologies)
