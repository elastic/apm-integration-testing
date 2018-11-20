#!/usr/bin/env bash
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

if [ -n "${APM_AGENT_JAVA_VERSION}" ]; then
  APM_AGENT_JAVA_VERSION=${APM_AGENT_JAVA_VERSION/'github;'/''}
  APM_AGENT_JAVA_VERSION=${APM_AGENT_JAVA_VERSION/'release;'/''}
  APM_AGENT_JAVA_VERSION=${APM_AGENT_JAVA_VERSION/'commit;'/''}
  BUILD_OPTS="${BUILD_OPTS} --java-agent-version='${APM_AGENT_JAVA_VERSION}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-java-spring --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-java docker-test-agent-java
