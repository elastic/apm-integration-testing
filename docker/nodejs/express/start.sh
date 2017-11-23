#!/usr/bin/env bash

set -ex

if [[ -z ${EXPRESS_APP_NAME} ]] || 
   [[ -z ${EXPRESS_PORT} ]] || 
   [[ -z ${NODEJS_AGENT_VERSION} ]] || 
   [[ -z ${NODEJS_AGENT_VERSION_STATE} ]]; then 
  echo "EXPRESS_APP_NAME, EXPRESS_PORT, NODEJS_AGENT_VERSION and NODEJS_AGENT_VERSION_STATE expected."
  exit 2
fi
if [[ -z ${APM_SERVER_URL} ]]; then
  echo "APM_SERVER_URL expected"
  exit 2
fi
if [[ -z ${NETWORK} ]]; then
  echo "NETWORK expected"
  exit 2
fi


if [[ ${NODEJS_AGENT_VERSION_STATE} == "release" ]]; then
  install_elastic_apm="npm install elastic-apm-node@${NODEJS_AGENT_VERSION}"
else
  install_elastic_apm="npm install elastic/apm-agent-nodejs#${NODEJS_AGENT_VERSION}"
fi

docker build --pull -t ${EXPRESS_APP_NAME} -f ./docker/nodejs/express/Dockerfile .

docker run -d \
  --name ${EXPRESS_APP_NAME} \
  --network=${NETWORK} \
  -p ${EXPRESS_PORT}:${EXPRESS_PORT} \
  -e EXPRESS_APP_NAME=${EXPRESS_APP_NAME} \
  -e EXPRESS_PORT=${EXPRESS_PORT} \
  -e APM_SERVER_URL="${APM_SERVER_URL}" \
  --rm "${EXPRESS_APP_NAME}" \
  /bin/bash \
  -c "${install_elastic_apm} &&
     node app.js"
