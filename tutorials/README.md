# Roseau Load Flow Solver Tutorials

## Overview

Welcome to the _Roseau Load Flow Tutorials_. This series of tutorials provides a comprehensive
overview of the steps needed to model, solve and analyze electrical networks using the _Roseau Load Flow_ solver. The
tutorial is designed for power engineering students or professionals, researchers, consultants, etc. and requires an
intermediate level of Python skills. Whatever your background, this tutorial will be valuable for understanding the
intricacies of the _Roseau Load Flow_ solver.

## Pre-Requisites

Make sure you have installed all the packages as described in the _pyproject.toml_ file to ensure a smooth journey
through the tutorial. Two options exist to achieve this result: the first one using `poetry` and the second one
using `pip`.

### Installation using `poetry`

1. Download all the files in this repository and unzip the folder on your device.
2. Using the terminal, install the package `poetry` in your main environment or in a virtual environment by
   executing the following command: `pip install poetry`.
3. With the environment activated, navigate to your download location in the terminal and run the following
   command: `poetry install`.

### Installation using `pip`

1. Download all the files in this repository and unzip the folder on your device.
2. Using the terminal, install all the requirements using the command `pip install -r requirements.txt`.

## OpenDSS

This directory is designed to help _OpenDSS_ users to use _Roseau Load Flow_.

### Tutorial 1

This tutorial involves modelling a simple LV network and is designed to familiarize the user with the basic workflow
of _Roseau Load Flow (RLF)_. You will learn the following:

1. How to model common network components such as buses, lines, transformers, etc. in _RLF_ as well as RLF-specific
   components.
2. How to build a network and run power flow simulations in _RLF_.
3. How to access different types of results for various network elements

### Tutorial 2

This series of tutorials focuses on the modelling flexibility of _RLF_ as well as benchmarking _RLF_ with _OpenDSS_, a
popular power flow solver. It will also demonstrate the interoperability of RLF with OpenDSS. In this tutorial, you
will learn the following:

1. How to convert OpenDSS parameters into _RLF_ parameters
2. How to model networks with a single-wire earth return systems in _RLF_

## Contributing

We welcome contributions form the community. If you have an idea for a new tutorial, bug fixes or improvements to
existing tutorials, please feel free to submit a pull request.

## Support

If you encounter any issues or have questions, please open an issue on GitHub. We are here to help and ensure that
you have a smooth learning experience.

## License

This repository is licensed under the MIT License.
