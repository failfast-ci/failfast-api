FROM python:3.11-slim as build
ENV workdir=/app
RUN mkdir -p $workdir
WORKDIR $workdir
RUN apt-get update
RUN apt-get install -y openssl ca-certificates
RUN apt-get install -y libffi-dev build-essential libssl-dev git rustc cargo
RUN pip install pip -U
RUN pip install poetry -U
COPY poetry.lock $workdir
COPY pyproject.toml $workdir
RUN poetry install --no-root --only=main

RUN rm -rf /root/.cargo
# COPY code later in the layers (after dependencies are installed)
# It builds the containers 2x faster on code change
COPY . $workdir
# Most of dependencies are already installed, it only install the app
RUN poetry install --no-dev
RUN apt-get remove --purge -y libffi-dev build-essential libssl-dev git rustc cargo

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
