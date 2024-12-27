---
myst:
  html_meta:
    "description lang=en": |
      Depending on your status, Roseau Load Flow is available with several types of free or paid licenses. A trial
       key is also available.
    "description lang=fr": |
      En fonction de votre statut, Roseau Load Flow est disponible avec plusieurs types de licences gratuites ou
       payantes. Une clef d'essai est également disponible.
    "keywords lang=fr": solveur, simulation, réseau, électrique, licence, open-source, gratuit, essai
    "keywords lang=en": simulation, distribution grid, solver, license, open-source, free, test
og:image: https://www.roseautechnologies.com/wp-content/uploads/2024/04/DSCF0265-scaled.webp
og:image:alt: An engineer uses Roseau Load Flow to perform compute the electric state of a MV/LV transformer
og:title: Free public license key
og:description: |
  You can try out RLF without registration on a distribution network of up to ten nodes by using the public license
  key provided below.
---

(license-page)=

# Get and activate your license

This project is partially open source. The source code of the Python interface is available on
[GitHub](https://github.com/RoseauTechnologies/Roseau_Load_Flow) under the
[BSD 3-Clause License](https://github.com/RoseauTechnologies/Roseau_Load_Flow/blob/main/LICENSE.md).
The solver used in this project is not open source. You need a valid license key to use it.

(license-types)=

## Types of licenses

### Trial license (free)

The license key **`A8C6DA-9405FB-E74FB9-C71C3C-207661-V3`** can be used with networks containing up
to 10 buses. For example, this key can be used to follow the tutorials in this documentation or for
personal projects. This key is valid indefinitely.

### Academic license (free)

_Students and teachers_ are eligible for **free unlimited licenses** to use in academic projects.
Please reach out to us at [contact@roseautechnologies.com](mailto:contact@roseautechnologies.com) to
obtain your free license key. The license key will be valid for one year and can be renewed.

### Commercial license (paid)

For other commercial or personal use, a license has to be purchased. Please contact us at
[contact@roseautechnologies.com](mailto:contact@roseautechnologies.com) to obtain a personalized
license.

(license-activation)=

## How to activate the license in your project?

There are two ways to activate the license in your project:

### Via environment variables (recommended)

Set the environment variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` to the license key. When this environment
variable is defined, it will automatically be used by the solver to validate the license, no further
action is required.

Please refer to the [How to set an environment variable?](license-environment-variable) section below
if you need help setting an environment variable.

### Using the `activate_license` function

Call the function `activate_license` with the license key as argument. This function will activate
the license for the current session. If you use this approach, it is recommended to store the
license key in a file and read it from there to avoid hard coding it in your code and accidentally
committing it to your repository. Example:

```python
from pathlib import Path
import roseau.load_flow as rlf

rlf.activate_license(Path("my_license_key.txt").read_text().strip())

# Rest of your code here
```

where the file `my_license_key.txt` contains `A8C6DA-9405FB-E74FB9-C71C3C-207661-V3` (replace
with your license key).

```{important}
Do not share your license key with others. The license key is personal and should not be shared
publicly. If you use a version control system like _Git_, make sure to exclude the file containing
the license key from versioning by adding it to your `.gitignore` file.
```

(license-environment-variable)=

## How to set an environment variable?

If you are not sure how to set an environment variable, [this article](https://www.bitecode.dev/p/environment-variables-for-beginners)
has instructions for Windows, macOS and Linux. The section [Persisting an environment variable](https://www.bitecode.dev/i/121864947/persisting-an-environment-variable)
explains how to make the environment variable persistent on your machine so that you don't have to
set it every time you open a new terminal.

### For Google Colab users

The "Secrets" feature in Google Colab is very useful for defining local variables. In the left panel, open the 'Secrets' section. Create a new variable called `ROSEAU_LOAD_FLOW_LICENSE_KEY`, with the value being your license key. This variable is personal to you, and the toggle will allow you to enable access to the license key for notebooks of your choice.

```{image} /_static/2024_09_16_Google_Colab_Environment_Variable.png
:alt: Google Colab environment variable
:align: center
```

To set the environment variable, add the following in a cell at the beginning of your notebook:

```
from google.colab import userdata
os.environ['ROSEAU_LOAD_FLOW_LICENSE_KEY'] = userdata.get('ROSEAU_LOAD_FLOW_LICENSE_KEY')
```

### For Jupyter Notebook users

If you are using a _Jupyter Notebook_, you can follow these instructions to set the environment
variable:

1. Create a file named `.env` in the same directory as you notebook with the following content
   (replace the key with your license key):
   ```bash
   ROSEAU_LOAD_FLOW_LICENSE_KEY="A8C6DA-9405FB-E74FB9-C71C3C-207661-V3"
   ```
2. Add a cell to the beginning of your notebook with the following content and execute it:
   ```ipython
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
