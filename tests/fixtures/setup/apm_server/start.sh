#!/usr/bin/env bash

set -ex

if [[ -z ${APM_SERVER_VERSION} ]]; then
  echo "APM_SERVER_VERSION is missing"
  exit 2
fi
if [[ -z ${APM_SERVER_PORT} ]]; then
  echo "APM_SERVER_PORT is missing"
  exit 2
fi
es_host="${ES_HOST:-elasticsearch}"
es_port="${ES_PORT:-9200}"
name="${APM_SERVER_NAME:-apm-server}" 
network=${NETWORK:-apm_test}

./tests/fixtures/setup/clean_docker.sh ${name} ${network}


if [[ ${APM_SERVER_VERSION} == "master" ]];then
  docker build -f 'tests/fixtures/setup/apm_server/Dockerfile' -t ${name} .
  docker run -d \
    --name "${name}" \
    --network "${network}" \
    -p ${APM_SERVER_PORT}:${APM_SERVER_PORT} \
    --rm "${name}" \
    /bin/bash \
    -c "rm -rf apm-server
        git clone http://github.com/elastic/apm-server.git
        cd apm-server
        make update apm-server
        echo "starting.."
        ./apm-server \
          -E apm-server.host=0.0.0.0:${APM_SERVER_PORT}\
          -E output.elasticsearch.hosts=[${es_host}:${es_port}]"
else
  #TODO: pass in config options
  docker run -d \
    --name "${name}" \
    --network "${network}" \
    -p ${APM_SERVER_PORT}:${APM_SERVER_PORT} \
    --rm "docker.elastic.co/apm/apm-server:${APM_SERVER_VERSION}"
fi
