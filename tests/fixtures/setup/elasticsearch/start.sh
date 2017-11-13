#!/usr/bin/env bash

set -ex

if [[ -z ${ES_VERSION} ]]; then
  echo "ES_VERSION is missing"
  exit 2
fi
if [[ -z ${ES_PORT} ]]; then
  echo "ES_PORT is missing"
  exit 2
fi
name="${ES_NAME:-elasticsearch}" 
xpack="${ES_XPACK:-false}" 
network=${NETWORK:-apm_test}

./tests/fixtures/setup/clean_docker.sh ${name} ${network}

docker run -d \
  --name "${name}" \
  --network "${network}" \
  -p ${ES_PORT}:${ES_PORT} \
  -e "discovery.type=single-node" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "network.host=''" \
  -e "transport.host=0.0.0.0"\
  -e "http.host=0.0.0.0"\
  -e "xpack.security.enabled=${xpack}" \
  --rm docker.elastic.co/elasticsearch/elasticsearch:${ES_VERSION}
