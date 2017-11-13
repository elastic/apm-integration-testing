#!/usr/bin/env bash

set -ex

if [[ -z ${KIBANA_VERSION} ]]; then
  echo "Environment variable KIBANA_VERSION missing"
  exit 2
fi
if [[ -z ${KIBANA_PORT} ]]; then
  echo "Environment variable KIBANA_PORT missing"
  exit 2
fi

name="${KIBANA_NAME:-kibana}" 
xpack="${KIBANA_XPACK:-false}" 
es_url="${ES_URL:-http://localhost:9200}"
network=${NETWORK:-apm_test}

echo ${es_url}

./tests/fixtures/setup/clean_docker.sh ${name} ${network}


docker run -d \
  --name=${name} \
  --network="apm_test" \
  -p ${KIBANA_PORT}:${KIBANA_PORT} \
  -e "network.host=''" \
  -e "transport.host=0.0.0.0"\
  -e "http.host=0.0.0.0"\
  -e "xpack.security.enabled=${xpack}" \
  -e "elasticsearch.url=${es_url}" \
  --rm docker.elastic.co/kibana/kibana:${KIBANA_VERSION}
