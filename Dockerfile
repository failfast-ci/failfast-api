FROM python:3.12 as build
ENV workdir=/app
RUN mkdir -p $workdir
WORKDIR $workdir
RUN apt-get update
RUN apt-get install -y openssl ca-certificates git libssl-dev
RUN apt-get install -y rustc cargo
RUN pip install pip -U
COPY requirements.txt $workdir
RUN pip install -r requirements.txt -U
run pip install gunicorn -U
RUN apt-get remove --purge -y libffi-dev build-essential libssl-dev rustc cargo
RUN rm -rf /root/.cargo

COPY . $workdir
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
CMD ["./run-server.sh"]
