#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

AGENT=$1
APP=$2

## Default flags
FLAG="--with-agent-${APP} --with-opbeans-${APP}"

## No opbeans for the python-django
if [ "${APP}" == "python-django" ] ; then
  FLAG="--with-agent-${APP}"
## No opbeans for the go-net-http
elif [ "${APP}" == "go-net-http" ] ; then
  FLAG="--with-agent-${APP}"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  ${FLAG} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --apm-server-agent-config-poll=1s \
  --force-build --no-xpack-secure"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests "env-agent-${AGENT}"
