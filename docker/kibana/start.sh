#!/usr/bin/env bash

set -ex

if [[ -z ${KIBANA_HOST} ]] || [[ -z ${KIBANA_VERSION} ]] || [[ -z ${KIBANA_PORT} ]]; then
  echo "KIBANA_HOST, KIBANA_VERSION and KIBANA_PORT expected"
  exit 2
fi
if [[ -z ${ES_URL} ]]; then
  echo "ES_URL expected"
  exit 2
fi
if [[ -z ${NETWORK} ]]; then
  echo "NETWORK expected"
  exit 2
fi

KIBANA_REGISTRY=${KIBANA_REGISTRY:-docker.elastic.co/kibana/kibana}

docker run -d \
  --name="${KIBANA_HOST}" \
  --network="${NETWORK}" \
  -p ${KIBANA_PORT}:${KIBANA_PORT} \
  -e "network.host=''" \
  -e "transport.host=0.0.0.0"\
  -e "http.host=0.0.0.0"\
  -e "xpack.security.enabled=${KIBANA_XPACK:-true}" \
  -e "elasticsearch.url=${ES_URL}" \
  --rm "${KIBANA_REGISTRY}:${KIBANA_VERSION}"
