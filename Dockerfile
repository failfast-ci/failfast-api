# FROM python:3.6.2-alpine
FROM registry.gitlab.com/failfast-ci/hub2lab-hook:v0.3.0

ENV workdir=/opt/failfast-ci
RUN apk --no-cache --update add openssl ca-certificates
RUN apk --no-cache add --virtual build-dependencies \
    libffi-dev build-base openssl-dev bash git
RUN pip install -U pip && pip install setuptools -U
RUN rm -rf $workdir
RUN mkdir -p $workdir
COPY . $workdir
WORKDIR $workdir
RUN pip install gunicorn -U && pip install -e .

CMD ["./run-server.sh"]
