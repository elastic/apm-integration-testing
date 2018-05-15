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

start_server="./apm-server -e -d \"*\" \
  -E apm-server.host=0.0.0.0:8200 \
  -E apm-server.concurrent_requests=1000 \
  -E setup.kibana.host=${KIBANA_HOST}:${KIBANA_PORT} \
  -E output.elasticsearch.hosts=[${ES_HOST}:${ES_PORT}] \
  -E apm-server.frontend.enabled=true"

if [[ ${APM_SERVER_VERSION_STATE} == "github" ]];then
  docker build -f 'docker/apm_server/Dockerfile' -t ${APM_SERVER_NAME}:${APM_SERVER_VERSION} .
  docker run -d \
    --name="${APM_SERVER_NAME}" \
    --network="${NETWORK}" \
    -p ${APM_SERVER_PORT}:8200 \
    -e "ES_HOST=${ES_HOST}" \
    -e "ES_PORT=${ES_PORT}" \
    --rm "${APM_SERVER_NAME}:${APM_SERVER_VERSION}" \
    /bin/bash \
    -c "rm -rf apm-server
        git clone --depth 1 --branch ${APM_SERVER_VERSION} https://github.com/elastic/apm-server.git
        cd apm-server
        make update apm-server
        ${start_server}"
else
  image_name="docker.elastic.co/apm/apm-server:${APM_SERVER_VERSION}"

  if [[ ${APM_SERVER_VERSION_STATE} == "snapshot" ]];then
    registry="https://snapshots.elastic.co/docker/"
    name="apm-server"
    version="${APM_SERVER_VERSION}-SNAPSHOT"
    file_type="tar.gz"
    file="${name}-${version}.${file_type}"
    curl -sSLO "${registry}${file}"
    docker load -i "${file}"
    rm "${file}"
    image_name="docker.elastic.co/apm/${name}:${version}"
  fi

  docker run -d \
    --name="${APM_SERVER_NAME}" \
    --network="${NETWORK}" \
    -p ${APM_SERVER_PORT}:8200 \
    -e "ES_HOST=${ES_HOST}" \
    -e "ES_PORT=${ES_PORT}" \
    --rm "${image_name}" \
    /bin/bash \
    -c "${start_server}" 
fi
