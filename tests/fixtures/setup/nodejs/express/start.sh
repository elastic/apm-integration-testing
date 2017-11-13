#!/usr/bin/env bash

set -ex

if [[ -z ${EXPRESS_APP_NAME} ]]; then
  echo "EXPRESS_APP_NAME is missing"
  exit 2
fi
if [[ -z ${EXPRESS_PORT} ]]; then
  echo "EXPRESS_PORT is missing"
  exit 2
fi

apm_server_url="${APM_SERVER_URL:-http://apm-server:8200}"

network=${NETWORK:-apm_test}
./tests/fixtures/setup/clean_docker.sh ${EXPRESS_APP_NAME} ${network}


docker build --pull -t ${EXPRESS_APP_NAME} -f ./tests/fixtures/setup/nodejs/express/Dockerfile .
docker run -d \
  --name ${EXPRESS_APP_NAME} \
  --network=${network} \
  -p ${EXPRESS_PORT}:${EXPRESS_PORT} \
  -e EXPRESS_APP_NAME=${EXPRESS_APP_NAME} \
  -e EXPRESS_PORT=${EXPRESS_PORT} \
  -e APM_SERVER_URL=${apm_server_url} \
  --rm "${EXPRESS_APP_NAME}" \
  /bin/bash \
  -c "npm install elastic/apm-agent-nodejs#master
      npm install express
      node app.js"
