FROM python:3.10-slim-bullseye as build

# Set the working directory to /app
WORKDIR /app

# Set some environment variables
ENV POETRY_HOME=/poetry PATH=/poetry/bin:${PATH} PYTHONUNBUFFERED=1

# Install some packages
RUN apt update && apt install --no-install-recommends -yq curl make pandoc

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy the code into the container
COPY . /app/

# Install any needed packages specified in poetry.lock
# Configure poetry
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --without dev,test --with doc

# Build a wheel the documentation
RUN poetry build && cd doc/ && SPHINXBUILD="poetry run sphinx-build" make html && cd ..

FROM python:3.10-slim-bullseye as run

# Set the working directory to /app
WORKDIR /app

ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:${PATH}" PORT=8080

# Install node js to allow extension installation
RUN apt update && apt install --no-install-recommends -yq curl
RUN apt update && \
    apt install --no-install-recommends -yq curl && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash -

RUN apt update && \
    apt install --no-install-recommends -yq nodejs \
    && apt upgrade -yq \
    && apt clean \
    && rm /var/lib/apt/lists/*_*

# Copy the virtualenv
COPY --from=build /app/.venv/ .venv/
COPY --from=build /app/dist/*.whl ./

# Install Jupyter lab
RUN pip3 install -U $(ls roseau_load_flow-*.whl | sort -Vr | head -n 1) pip jupyterlab jupyterlab-language-pack-fr-FR \
    && rm roseau_load_flow-*.whl

# COPY the documentation, the noteboks and the data
COPY --from=build /app/build/html/ doc/
COPY ./doc/notebooks/ .
COPY ./data/ data/

# Run app.py when the container launches
ENTRYPOINT jupyter lab --allow-root --ServerApp.allow_origin='*' --ip=0.0.0.0 --port ${PORT} --no-browser --ServerApp.token=''
