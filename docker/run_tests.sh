#!/usr/bin/env bash

set -e

name='apm-testing'

docker build --pull -t ${name} .

docker run \
  --name=${name} \
  --network=${NETWORK} \
  --security-opt seccomp=unconfined \
  -e ES_URL=${ES_URL} \
  -e KIBANA_URL=${KIBANA_URL} \
  -e APM_SERVER_URL=${APM_SERVER_URL} \
  -e EXPRESS_APP_NAME=${EXPRESS_APP_NAME} \
  -e EXPRESS_URL=${EXPRESS_URL} \
  -e FLASK_SERVICE_NAME=${FLASK_SERVICE_NAME} \
  -e FLASK_URL=${FLASK_URL} \
  -e DJANGO_SERVICE_NAME=${DJANGO_SERVICE_NAME} \
  -e DJANGO_URL=${DJANGO_URL} \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e URLS=${URLS} \
  -e TEST_CMD="${TEST_CMD}" \
  --rm "${name}" \
  /bin/bash \
  -c "make tests"
