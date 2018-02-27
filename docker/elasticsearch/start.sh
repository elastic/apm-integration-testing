#!/usr/bin/env bash

set -ex

if [[ -z ${ES_NAME} ]] || 
   [[ -z ${ES_VERSION} ]] || 
   [[ -z ${ES_VERSION_STATE} ]] || 
   [[ -z ${ES_PORT} ]]; then
  echo "ES_NAME, ES_VERSION, ES_VERSION_STATE and ES_PORT expected"
  exit 2
fi
if [[ -z ${NETWORK} ]]; then
  echo "NETWORK expected"
  exit 2
fi

image_name="docker.elastic.co/elasticsearch/elasticsearch:${ES_VERSION}"

if [[ ${ES_VERSION_STATE} == "snapshot" ]]; then
  registry="https://snapshots.elastic.co/docker/"
  name="elasticsearch"
  version="${ES_VERSION}-SNAPSHOT"
  file_type="tar.gz"
  file="${name}-${version}.${file_type}"
  curl -sSLO "${registry}${file}"
  docker load -i "${file}"
  rm "${file}"
  image_name="docker.elastic.co/elasticsearch/${name}:${version}"
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
  --rm "${image_name}"
