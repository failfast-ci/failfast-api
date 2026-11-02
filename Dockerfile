FROM python:3.12 as build
ENV workdir=/app
RUN mkdir -p $workdir
WORKDIR $workdir
RUN apt-get update
RUN apt-get install -y openssl ca-certificates git libssl-dev
RUN apt-get install -y rustc cargo
COPY requirements.txt $workdir/
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN apt-get remove --purge -y libffi-dev build-essential libssl-dev rustc cargo
RUN rm -rf /root/.cargo

COPY . $workdir
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
CMD ["./run-server.sh"]
