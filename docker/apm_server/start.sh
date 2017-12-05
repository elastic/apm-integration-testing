#!/usr/bin/env bash

set -ex

if [[ -z ${APM_SERVER_VERSION} ]] || 
   [[ -z ${APM_SERVER_VERSION_STATE} ]] || 
   [[ -z ${APM_SERVER_PORT} ]] || 
   [[ -z ${APM_SERVER_NAME} ]]; then
  echo "APM_SERVER_VERSION, APM_SERVER_VERSION_STATE, APM_SERVER_NAME and APM_SERVER_PORT expected"
  exit 2
fi
if [[ -z ${ES_HOST} ]] || [[ -z ${ES_PORT} ]]; then
  echo "ES_HOST and ES_PORT expected"
  exit 2
fi
if [[ -z ${NETWORK} ]]; then
  echo "NETWORK expected"
  exit 2
fi

echo "APM_SERVER_VERSION: ${APM_SERVER_VERSION}, ${APM_SERVER_VERSION_STATE}"

if [[ ${APM_SERVER_VERSION_STATE} != "release" ]];then
  docker build -f 'docker/apm_server/Dockerfile' -t ${APM_SERVER_NAME} .
  docker run -d \
    --name="${APM_SERVER_NAME}" \
    --network="${NETWORK}" \
    -p ${APM_SERVER_PORT}:8200 \
    -e "ES_HOST=${ES_HOST}" \
    -e "ES_PORT=${ES_PORT}" \
    --rm "${APM_SERVER_NAME}" \
    /bin/bash \
    -c "rm -rf apm-server
        git clone http://github.com/elastic/apm-server.git
        cd apm-server
        git checkout ${APM_SERVER_VERSION}
        make update apm-server 
        ./apm-server -e -d \"*\" -c ../apm-server.yml"
else
  docker run -d \
    --name="${APM_SERVER_NAME}" \
    --network="${NETWORK}" \
    -p ${APM_SERVER_PORT}:8200 \
    -e "ES_HOST=${ES_HOST}" \
    -e "ES_PORT=${ES_PORT}" \
    -v "$(pwd)/docker/apm_server/apm-server.yml:/usr/share/apm-server/apm-server.yml" \
    --rm "docker.elastic.co/apm/apm-server:${APM_SERVER_VERSION}"
fi
