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
        git clone --depth 1 --branch ${APM_SERVER_VERSION} http://github.com/elastic/apm-server.git
        cd apm-server
        make update apm-server
        ./apm-server -e -d \"*\" -c ../apm-server.yml"
else
  image_name="docker.elastic.co/apm/apm-server:${APM_SERVER_VERSION}"

  if [[ ${APM_SERVER_VERSION_STATE} == "snapshot" ]];then
    registry="https://snapshots.elastic.co/docker/"
    name="apm-server"
    version="${APM_SERVER_VERSION}-SNAPSHOT"
    file_type="tar.gz"
    file="${name}-${version}.${file_type}"
    wget "${registry}${file}"
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
    -v "$(pwd)/docker/apm_server/apm-server.yml:/usr/share/apm-server/apm-server.yml" \
    --rm "${image_name}"
fi
