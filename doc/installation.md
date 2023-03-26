# Using `pip` #

`roseau_load_flow` is available on [PyPI](https://pypi.org/project/roseau-load-flow/). It can be
installed using pip with:
```console
$ python -m pip install roseau-load-flow
```

`````{tip}
It is recommended to work in a virtual environment to isolate your project. You can create one with:

```console
$ python -m venv venv
```

A folder named `venv` will be created. To activate the virtual environment, run:

````{tab} Windows

```doscon
C:> venv\Scripts\activate
```

````

````{tab} Linux

```console
$ source venv/bin/activate
```

````

````{tab} MacOS

```console
$ . venv/bin/activate
```

````

`````

To upgrade to the latest version (recommended), use:
```console
$ python -m pip install --upgrade roseau-load-flow
```

# Using `conda` #

`roseau_load_flow` is also available on [conda-forge](https://anaconda.org/conda-forge/roseau-load-flow).
It can be installed using conda with:
```console
$ conda install -c conda-forge roseau-load-flow
```

```{tip}
If you use *conda* to manage your project, it is recommended to use the `conda` package manager
instead of `pip`.
```

# Using `docker` #

`roseau_load_flow` provides a *docker image* with all required dependencies pre-installed,
including *Python*. The image runs a *Jupyter* session that you can access in your browser. To
install and run your docker environment, follow the steps corresponding to your operating system
below.

````{tab} Windows

1. Download and install Docker Desktop for Windows, available [here](
   https://www.docker.com/products/docker-desktop/).

   ```{hint}
   During the installation, select "WSL **2**" (WSL = Windows Subsystem for Linux).
   ```

2. Open *Docker Desktop* to start the *Docker Engine*

   ![Docker Desktop](_static/2022_10_20_Installation_2.png)

   ```{note}
   During the first start of the software, it may require to install some extra files to update
   WSL1 to WSL2.
   ```

3. Go to the [Package page](
   https://github.com/RoseauTechnologies/Roseau_Load_Flow/pkgs/container/roseau-load-flow) of
   Roseau Load Flow on GitHub and copy the Docker command to pull the image.

   ![Package](_static/2022_10_20_Installation_1.png)

4. Open a Terminal

   ```{image} _static/2022_10_20_Installation_3.png
   :alt: Terminal
   :width: 15cm
   ```

5. Paste the command line in your terminal to start downloading the Docker image

   ![Package](_static/2022_10_20_Installation_4.png)

6. In the "Images" tab of *Docker Desktop*, the image should be visible. You can click on `Run` to
   start it.

7. Fill the advanced options if you want. It allows you to give a name to the created container,
   and to link folders of your system to the container. You can for instance link the folder
   `Documents` to the directory `/app/Documents/` in the container (as shown below). When done
   click on `Run` to start the container.

   ![Advanced options](_static/2022_10_20_Installation_6.png)

8. The container should start in a few seconds. Open a web browser and navigate to
   [http://localhost:8080](http://localhost:8080) to find the JupyterLab page of the container. A
   basic python environment is set up with the `roseau_load_flow` package already installed.

````

````{tab} Linux

1. Install Docker via the [detailed tutorial](https://docs.docker.com/engine/install/#server)
   written by the Docker team. Follow instructions specific to your platform like [Ubuntu](
   https://docs.docker.com/engine/install/ubuntu/) or [Debian](
   https://docs.docker.com/engine/install/debian/).

2. Go to the [Package page](
   https://github.com/RoseauTechnologies/Roseau_Load_Flow/pkgs/container/roseau-load-flow) of
   Roseau Load Flow on GitHub and copy the Docker command to pull the image.

   ![Package](_static/2022_10_20_Installation_1.png)

3. Paste it in your terminal to start downloading the Docker image

4. Use `docker run` to start a container; for example with version *0.3.0*:
   ```console
   $ docker run -p 8080:8080 --name rlf-test ghcr.io/roseautechnologies/roseau-load-flow:0.3.0
   ```

5. Open a web browser and navigate to [http://localhost:8080](http://localhost:8080) to find the
   JupyterLab page of the container. A basic python environment is set up with the
   `roseau_load_flow` package already installed.

````

<!-- Local Variables: -->
<!-- mode: markdown -->
<!-- coding: utf-8-unix -->
<!-- fill-column: 100 -->
<!-- ispell-local-dictionary: "english" -->
<!-- End: -->
