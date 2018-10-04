#!/bin/bash -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

DEFAULT_COMPOSE_ARGS="master --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-python-django --with-agent-python-flask --force-build --build-parallel"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-python docker-test-agent-python
