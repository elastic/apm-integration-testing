#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

AGENT=$1
APP=$2
DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --with-agent-${APP} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-${AGENT} docker-test-agent-${AGENT}
