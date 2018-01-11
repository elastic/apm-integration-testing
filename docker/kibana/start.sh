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


image_name="docker.elastic.co/kibana/kibana:${KIBANA_VERSION}"

if [[ ${KIBANA_VERSION_STATE} == "snapshot" ]]; then
  registry="https://snapshots.elastic.co/docker/"
  name="kibana"
  version="${KIBANA_VERSION}-SNAPSHOT"
  file_type="tar.gz"
  file="${name}-${version}.${file_type}"
  wget "${registry}${file}"
  docker load -i "${file}"
  rm "${file}"
  image_name="docker.elastic.co/kibana/${name}:${version}"
fi
docker run -d \
  --name="${KIBANA_HOST}" \
  --network="${NETWORK}" \
  -p ${KIBANA_PORT}:${KIBANA_PORT} \
  -e "network.host=''" \
  -e "transport.host=0.0.0.0"\
  -e "http.host=0.0.0.0"\
  -e "xpack.security.enabled=${KIBANA_XPACK:-false}" \
  -e "elasticsearch.url=${ES_URL}" \
  --rm "${image_name}"
