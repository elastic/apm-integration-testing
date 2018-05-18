#!/usr/bin/env bash

set -ex

if [[ -z ${APM_SERVER_URL} ]]; then
  echo "APM_SERVER_URL expected"
  exit 2
fi
if [[ -z ${NETWORK} ]]; then
  echo "NETWORK expected"
  exit 2
fi

app_name=${GO_NETHTTP_SERVICE_NAME}
port=${GO_NETHTTP_PORT}
start_cmd="/testapp"

docker build --pull -t ${app_name} -f ./docker/go/nethttp/Dockerfile .

docker run -d \
  --name ${app_name} \
  --network=${NETWORK} \
  -e ELASTIC_APM_SERVICE_NAME=${app_name} \
  -e ELASTIC_APM_SERVER_URL=${APM_SERVER_URL} \
  -e ELASTIC_APM_TRANSACTION_IGNORE_NAMES=healthcheck \
  -e ELASTIC_APM_FLUSH_INTERVAL=500ms \
  --rm "${app_name}"
