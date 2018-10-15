#!/usr/bin/env bash

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

# version -> curl -L https://github.com/elastic/apm-agent-java/archive/${version}.tar.gz
if [ ! -z "${APM_AGENT_JAVA_PKG}" ]; then
  export BUILD_OPTS="${BUILD_OPTS} --java-agent-package='${APM_AGENT_JAVA_PKG}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION:-'master'} ${BUILD_OPTS} --no-apm-server-self-instrument --no-apm-server-dashboards --no-kibana --with-agent-java-spring --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-java docker-test-agent-java
