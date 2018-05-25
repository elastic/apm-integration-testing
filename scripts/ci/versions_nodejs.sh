#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, node js agent version spec and stack version must be provided"
  exit 2
fi

version_type=${1%;*}
version=${1#*;}
stack_version=$2

# use latest release by default
node_js_pkg="elastic-apm-node@${version}"
if [ "${version_type}" == github ]; then
    node_js_pkg="elastic/apm-agent-nodejs#${version}"
fi

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

DEFAULT_COMPOSE_ARGS="$2 --no-kibana --with-agent-nodejs-express --nodejs-agent-package='${node_js_pkg}' --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-nodejs docker-test-agent-nodejs-version
