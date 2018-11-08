#!/usr/bin/env bash

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

if [ -n "${APM_AGENT_JAVA_PKG}" ]; then
  APM_AGENT_JAVA_PKG=${APM_AGENT_JAVA_PKG/'github;'/''}
  APM_AGENT_JAVA_PKG=${APM_AGENT_JAVA_PKG/'release;'/''}
  APM_AGENT_JAVA_PKG=${APM_AGENT_JAVA_PKG/'commit;'/''}
  BUILD_OPTS="${BUILD_OPTS} --java-agent-package='${APM_AGENT_JAVA_PKG}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-java-spring --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-java docker-test-agent-java
