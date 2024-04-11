---
myst:
  html_meta:
    "description lang=en": |
      Depending on your status, Roseau Load Flow is available with several types of free or paid licences. A trial
       key is also available.
    "description lang=fr": |
      En fonction de votre statut, Roseau Load Flow est disponible avec plusieurs types de licences gratuites ou
       payantes. Une clef d'essai est également disponible.
    "keywords lang=fr": solveur, simulation, réseau, électrique, licence, open-source, gratuit, essai
    "keywords lang=en": simulation, distribution grid, solver, open-source, free, test
og:image: https://www.roseautechnologies.com/wp-content/uploads/2024/04/DSCF0265-scaled.webp
og:image:alt: An engineer uses Roseau Load Flow to perform compute the electric state of a MV/LV transformer
og:title: Free public licence key
og:description: |
  You can try out RLF without registration on a distribution network of up to ten nodes by using the public licence
  key provided below.
---

(license-page)=

# Get and activate your licence

(license-types)=

## Commercial and free licences

This project is partially open source. The source code of this repository is available under the
[BSD 3-Clause License](https://github.com/RoseauTechnologies/Roseau_Load_Flow/blob/main/LICENSE.md).

The solver used in this project is not open source. A license has to be purchased to use it. To
obtain a personal or commercial license, please contact us at
[contact@roseautechnologies.com](mailto:contact@roseautechnologies.com).

For networks with less than 11 buses (up to 10 buses), the license key `A8C6DA-9405FB-E74FB9-C71C3C-207661-V3`
can be used free of charge. For example, this key can be used to follow the getting started guide.

```{note}
Licenses are given **free of charge** for _students and teachers_. Please contact us at
[contact@roseautechnologies.com](mailto:contact@roseautechnologies.com) to get a license key.
```

(license-activation)=

## How to activate the license in your project?

There are two ways to activate the license in your project:

1. Set the environment variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` to the license key. When this
   environment variable is defined, it will automatically be used by the solver to validate the
   license, no further action is required.
   **This is the recommended approach.**
   ```{note}
   If you need help setting an environment variable, refer to the section
   [How to set an environment variable?](license-environment-variable)
   ```
2. Call the function `activate_license` with the license key as argument. This function will
   activate the license for the current session. If you use this approach, it is recommended to
   store the license key in a file and read it from there to avoid hard coding it in your code and
   accidentally committing it to your repository. Example:

   ```python
   from pathlib import Path
   import roseau.load_flow as lf

   lf.activate_license(Path("my_license_key.txt").read_text().strip())

   # Rest of your code here
   ```

   where the file `my_license_key.txt` contains `A8C6DA-9405FB-E74FB9-C71C3C-207661-V3` (replace
   with your license key).

(license-environment-variable)=

## How to set an environment variable?

If you are not sure how to set an environment variable, [this article](https://www.bitecode.dev/p/environment-variables-for-beginners)
has instructions for Windows, MacOS and Linux. The section [Persisting an environment variable](https://www.bitecode.dev/i/121864947/persisting-an-environment-variable)
explains how to make the environment variable persistent on your machine so that you don't have to
set it every time you open a new terminal.

### For Jupyter Notebook users

If you are using a _Jupyter Notebook_, you can follow these instructions to set the environment
variable:

1. Create a file named `.env` in the same directory as you notebook with the following content
   (replace the key with your license key):
   ```bash
   ROSEAU_LOAD_FLOW_LICENSE_KEY="A8C6DA-9405FB-E74FB9-C71C3C-207661-V3"
   ```
2. Add a cell to the beginning of your notebook with the following content and execute it:
   ```ipython3
   %pip install python-dotenv
   %load_ext dotenv
   %dotenv
   ```
   The first line will install the package [python-dotenv](https://pypi.org/project/python-dotenv/)
   if it is not already installed. The next lines will load the extension `dotenv` and load the
   environment variables from the file `.env` in the current directory (created in step 1).

### For VS Code users

If you are using [Visual Studio Code](https://code.visualstudio.com/), you can create a file named
`.env` in your project directory (similar to step 1 for Jupyter) and VS Code will automatically
load the environment variables from this file when you run your code (including when using Jupyter
Notebooks in VS Code).

### For PyCharm users

If you are using [PyCharm](https://www.jetbrains.com/pycharm/), you can add the environment variable
to your _Python Console_ settings as indicated in the screenshot below:

```{image} /_static/2024_01_12_Pycharm_Console_Environment_Variable.png
:alt: Pycharm Console environment variable
:align: center
```
