FROM python:3.5

ARG version=0.1.1
ARG workdir=/opt/failfast-ci
RUN apt-get update -y
RUN apt-get install bash openssl ca-certificates git wget -y
RUN pip install pip -U
RUN pip install jsonnet -U
RUN rm -rf $workdir
RUN mkdir -p $workdir
ADD . $workdir
WORKDIR $workdir
RUN pip install gunicorn -U && pip install -e .

CMD ["./run-server"]
