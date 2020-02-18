#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

AGENT=$1
APP=$2
OPBEANS_APP=$3

## TODO: Wait for the changes in the library
if [ "${OPBEANS_APP}" == "nodejs" ] ; then
  OPBEANS_APP=node
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --with-agent-${APP} \
  --with-opbeans-${OPBEANS_APP} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --apm-server-agent-config-poll=1s \
  --force-build --no-xpack-secure"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests "env-agent-${AGENT}"
