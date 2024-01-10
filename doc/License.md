(license)=

# License

This project is partially open source. The source code of this repository is available under the
[BSD 3-Clause License](https://github.com/RoseauTechnologies/Roseau_Load_Flow/blob/main/LICENSE.md).

The solver used in this project is not open source. A license has to be purchased to use it. To get a license, please contact us at contact@roseautechnologies.com.

```{note}
Licenses are given **free of charge** for _students and teachers_. Please contact us at
contact@roseautechnologies.com to get a license key.
```

(license-activation)=

## How to activate the license in your project

There are two ways to activate the license in your project:

1. Set the environment variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` to the license key. When this
   environment variable is defined, it will be automatically used by the solver to validate the
   license, no further action is required.
   **This is the recommended approach.**
2. Call the function `activate_license` with the license key as argument. This function will
   activate the license for the current session. If you use this approach, it is recommended to
   store the license key in a file and read it from there to avoid hardcoding it in your code and
   accidentally committing it to your repository. Example:

   ```python
   import roseau.load_flow as lf

   with open("my_license_key.txt", "r") as f:
       license_key = f.read().strip()
   lf.activate_license(license_key)

   # Rest of your code here
   ```
