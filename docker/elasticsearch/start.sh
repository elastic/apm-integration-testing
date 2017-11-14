#!/usr/bin/env bash

set -ex

if [[ -z ${ES_NAME} ]] || [[ -z ${ES_VERSION} ]] || [[ -z ${ES_PORT} ]]; then
  echo "ES_NAME, ES_VERSION and ES_PORT expected"
  exit 2
fi
if [[ -z ${NETWORK} ]]; then
  echo "NETWORK expected"
  exit 2
fi

docker run -d \
  --name="${ES_NAME}" \
  --network="${NETWORK}" \
  -p ${ES_PORT}:9200 \
  -e "discovery.type=single-node" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "network.host=''" \
  -e "transport.host=0.0.0.0"\
  -e "http.host=0.0.0.0"\
  -e "xpack.security.enabled=${ES_XPACK:-false}" \
  --rm docker.elastic.co/elasticsearch/elasticsearch:${ES_VERSION}
