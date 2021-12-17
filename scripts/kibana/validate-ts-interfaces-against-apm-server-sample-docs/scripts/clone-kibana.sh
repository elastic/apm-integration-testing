#!/usr/bin/env bash
set -e

OWNER=${1:-elastic}
BRANCH=${2:-main}

echo "Cloning Kibana: ${OWNER}:${BRANCH}"

cd ./tmp
git clone --quiet --depth 1 -b "${BRANCH}" "https://github.com/${OWNER}/kibana.git"

### In 7.7 files moved around.
### The below section keeps backward compatibility.
oldLocation=./kibana/x-pack/legacy/plugins/apm/typings/es_schemas
newLocation=./kibana/x-pack/plugins/apm/typings/es_schemas
location=${oldLocation}
if [ -d "${newLocation}" ] ; then
   location=${newLocation}
fi
mv "${location}" ./apm-ui-interfaces
rm -rf kibana
