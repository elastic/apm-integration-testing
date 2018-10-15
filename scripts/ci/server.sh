#!/bin/bash -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION:-'master'} ${BUILD_OPTS} --no-apm-server-dashboards --no-kibana"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-server docker-test-server
