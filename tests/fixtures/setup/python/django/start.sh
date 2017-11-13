#!/usr/bin/env bash

set -ex

if [[ -z ${DJANGO_APP_NAME} ]]; then
  echo "DJANGO_APP_NAME is missing"
  exit 2
fi
if [[ -z ${DJANGO_PORT} ]]; then
  echo "DJANGO_PORT is missing"
  exit 2
fi

apm_server_url="${APM_SERVER_URL:-http://apm-server:8200}"

network=${NETWORK:-apm_test}
./tests/fixtures/setup/clean_docker.sh ${DJANGO_APP_NAME} ${network}

docker build --pull -t ${DJANGO_APP_NAME} -f ./tests/fixtures/setup/python/django/Dockerfile .
docker run -d \
  --name ${DJANGO_APP_NAME} \
  --network=${network} \
  -p ${DJANGO_PORT}:${DJANGO_PORT} \
  -e DJANGO_APP_NAME=${DJANGO_APP_NAME} \
  -e DJANGO_PORT=${DJANGO_PORT} \
  -e APM_SERVER_URL=${apm_server_url} \
  --rm "${DJANGO_APP_NAME}" \
  /bin/bash \
  -c "pip install -Ur requirements.txt
      python testapp/manage.py runserver 0.0.0.0:${DJANGO_PORT}"
