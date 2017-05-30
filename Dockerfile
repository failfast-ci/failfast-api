FROM registry.gitlab.com/failfast-ci/hub2lab-hook:v0.1.4

ARG version=0.2.7
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
