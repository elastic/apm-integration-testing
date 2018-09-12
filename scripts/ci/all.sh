#!/bin/bash -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

DEFAULT_COMPOSE_ARGS="master --no-apm-server-dashboards --with-agent-rumjs --with-agent-go-net-http --with-agent-nodejs-express --with-agent-python-django --with-agent-python-flask --with-agent-ruby-rails --with-agent-java-spring --force-build --build-parallel"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-all docker-test-all
