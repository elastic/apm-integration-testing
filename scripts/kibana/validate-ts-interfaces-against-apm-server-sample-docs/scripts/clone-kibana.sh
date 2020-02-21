#!/usr/bin/env bash
set -e

OWNER=${1:-elastic}
BRANCH=${2:-master}

echo "Cloning Kibana: ${OWNER}:${BRANCH}"

cd ./tmp || true
git clone --quiet --depth 1 -b "${BRANCH}" "https://github.com/${OWNER}/kibana.git"
mv ./kibana/x-pack/plugins/apm/typings/es_schemas ./apm-ui-interfaces
rm -rf kibana
