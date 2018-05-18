#!/usr/bin/env bash

set -e

name='apm-testing'

docker build --pull -t ${name} .

docker run \
  --name=${name} \
  --network=${NETWORK} \
  --security-opt seccomp=unconfined \
  -e ES_URL \
  -e KIBANA_URL \
  -e APM_SERVER_URL \
  -e EXPRESS_APP_NAME \
  -e EXPRESS_URL \
  -e FLASK_SERVICE_NAME \
  -e FLASK_URL \
  -e DJANGO_SERVICE_NAME \
  -e DJANGO_URL \
  -e RAILS_SERVICE_NAME \
  -e RAILS_URL \
  -e GO_NETHTTP_SERVICE_NAME \
  -e GO_NETHTTP_URL \
  -e URLS \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e TEST_CMD="${TEST_CMD}" \
  --rm "${name}" \
  /bin/bash \
  -c "make tests"
