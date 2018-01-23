FROM golang:latest
RUN set -x && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python-pip virtualenv build-essential && \
    apt-get clean

WORKDIR ${GOPATH}/src/github.com/elastic/
