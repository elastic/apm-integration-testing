#!/usr/bin/env bash

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

DEFAULT_COMPOSE_ARGS="master --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-java-spring --force-build --build-parallel"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-java docker-test-agent-java
