#!/usr/bin/env bash

set -ex 

name='apm-testing'

docker build --pull -t ${name} .

docker run -it \
  --name=${name} \
  --network=${NETWORK} \
  -e ES_URL=${ES_URL} \
  -e KIBANA_URL=${KIBANA_URL} \
  -e APM_SERVER_URL=${APM_SERVER_URL} \
  -e EXPRESS_APP_NAME=${EXPRESS_APP_NAME} \
  -e EXPRESS_URL=${EXPRESS_URL} \
  -e FLASK_APP_NAME=${FLASK_APP_NAME} \
  -e FLASK_URL=${FLASK_URL} \
  -e GUNICORN_APP_NAME=${GUNICORN_APP_NAME} \
  -e GUNICORN_URL=${GUNICORN_URL} \
  -e DJANGO_APP_NAME=${DJANGO_APP_NAME} \
  -e DJANGO_URL=${DJANGO_URL} \
  -e PYTHONDONTWRITEBYTECODE=1 \
  --rm "${name}" \
  /bin/bash \
  -c "python docker/wait_until_services_running.py ${URLS}
      #TODO: add handling when exception occured
      ${TEST_CMD}"
