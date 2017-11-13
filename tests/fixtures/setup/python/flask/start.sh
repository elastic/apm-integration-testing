#!/usr/bin/env bash

set -ex

if [[ -z ${FLASK_APP_NAME} ]]; then
  echo "FLASK_APP_NAME is missing"
  exit 2
fi
if [[ -z ${FLASK_PORT} ]]; then
  echo "FLASK_PORT is missing"
  exit 2
fi

apm_server_url="${APM_SERVER_URL:-http://apm-server:8200}"

network=${NETWORK:-apm_test}
./tests/fixtures/setup/clean_docker.sh ${FLASK_APP_NAME} ${network}

docker build --pull -t ${FLASK_APP_NAME} -f ./tests/fixtures/setup/python/flask/Dockerfile .

if [[ -z ${PY_SERVER} ]]; then
  CMD="pip install -Ur requirements.txt &&
       python app.py"
elif [[ ${PY_SERVER} -eq "gunicorn" ]]; then
  CMD="pip install -Ur requirements.txt &&
       pip install gunicorn &&
       gunicorn -w 4 -b 0.0.0.0:${FLASK_PORT} app:app"
fi

docker run -d\
  --name ${FLASK_APP_NAME} \
  --network=${network} \
  -p ${FLASK_PORT}:${FLASK_PORT} \
  -e FLASK_APP_NAME=${FLASK_APP_NAME} \
  -e FLASK_PORT=${FLASK_PORT} \
  -e APM_SERVER_URL=${apm_server_url} \
  --rm "${FLASK_APP_NAME}" \
  /bin/bash \
  -c "${CMD}"
