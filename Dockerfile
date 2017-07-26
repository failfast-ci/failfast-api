FROM python:3.6.2-alpine

ENV workdir=/opt/failfast-ci
RUN apk --no-cache --update add openssl ca-certificates
RUN apk --no-cache --update add --virtual build-dependencies \
    libffi-dev build-base openssl-dev
RUN pip install pip -U
RUN rm -rf $workdir
RUN mkdir -p $workdir
COPY . $workdir
WORKDIR $workdir
RUN pip install gunicorn -U && pip install -e .

CMD ["./run-server"]
