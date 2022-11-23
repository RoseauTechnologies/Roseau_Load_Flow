# Using `docker`

`roseau_load_flow` provides a *docker* image with all required dependencies to run the software,
including *Python*, installed in the environment. The image runs a *Jupyter* session that you
can access in your browser. To install and run your docker environment, follow the steps that
correspond to your operating system below.

## On Windows

1. Download and install Docker Desktop for Windows available [here](
   https://www.docker.com/products/docker-desktop/).

   ```{hint}
   During the installation, select "WSL **2**" (WSL = Windows Subsystem for Linux).
   ```

2. Open Docker Desktop to start the Docker Engine

   ![Docker Desktop](_static/2022_10_20_Installation_2.png)

   ```{note}
   During the first start of the software, it may require to install some extra file to update WSL1 to WSL2.
   ```

3. Go to the Package page of the GitHub repository available [here](
   https://github.com/RoseauTechnologies/Roseau_Load_Flow/pkgs/container/roseau-load-flow)

4. Copy the Docker command line

   ![Package](_static/2022_10_20_Installation_1.png)

5. Open a Terminal

   ```{image} _static/2022_10_20_Installation_3.png
   :alt: Terminal
   :width: 15cm
   ```

6. Paste the command line in your terminal to start downloading the Docker image

   ![Package](_static/2022_10_20_Installation_4.png)

7. In the "Images" tab of Docker Desktop, the image should be visible. You can click on "Run" to
   start it.

8. Fill the advanced options if you want. It allows you to give a name to the created container,
   and to link folders of your system to the container. You can by instance (as depicted below)
   link the folder `Documents` to the container directory `/app/Documents/`. Then click on `Run`.

   ![Advanced options](_static/2022_10_20_Installation_6.png)

9. The container should start in a few second. Open your web browser and go to
   [http://localhost:8080](http://localhost:8080) to find the interface of the JupyterLab of the
   container. A basic python environment is already installed with the `roseau_load_flow` package
   already installed.

## On Linux

1. Install Docker via the [detailed tutorial](https://docs.docker.com/engine/install/#server)
   written by the Docker team. Follow instructions specific to your platform like
   [Ubuntu](https://docs.docker.com/engine/install/ubuntu/) or
   [Debian](https://docs.docker.com/engine/install/debian/).

2. Go to the Package page of the GitHub repository available [here](
   https://github.com/RoseauTechnologies/Roseau_Load_Flow/pkgs/container/roseau-load-flow)

3. Copy the Docker command line

   ![Package](_static/2022_10_20_Installation_1.png)

4. Paste it in your terminal to start downloading the Docker image

5. Use docker run to start a container. The most simple command to do that can be (with version 0.2.1):
   ```console
   $ docker run -p 8080:8080 --name rlf-test ghcr.io/roseautechnologies/roseau-load-flow:0.2.1
   ```

6. Open your web browser and go to [http://localhost:8080](http://localhost:8080) to find the
   interface of the JupyterLab of the container.
   A basic python environment is already installed with the `roseau_load_flow` package already installed.

# Using `pip`

If you desire to install the `roseau_load_flow` package via pip, please go the release page of the
GitHub repository [here](https://github.com/RoseauTechnologies/Roseau_Load_Flow/releases/) and
download the latest available *Wheel* (Click on the file that ends with `.whl`). It can then be
installed via the following command (here, the installed version is 0.2.1):

```console
$ python -m pip install <PATH TO THE FILE roseau_load_flow-0.2.1-py3-none-any.whl>
```

```{note}
Always install the latest version available which is conveniently marked *latest* by GitHub as
shown here:

![GitHub Latest Release](_static/2022_11_23_GH_Latest_Release.png)
```