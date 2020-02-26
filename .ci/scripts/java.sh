#!/usr/bin/env bash
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

if [ -n "${APM_AGENT_JAVA_VERSION}" ]; then
  EXTRA_OPTS=${APM_AGENT_JAVA_VERSION/'github;'/'--java-agent-version='}
  EXTRA_OPTS=${EXTRA_OPTS/'release;'/'--java-agent-release='}
  EXTRA_OPTS=${EXTRA_OPTS/'commit;'/'--java-agent-version='}
  BUILD_OPTS="${BUILD_OPTS} ${EXTRA_OPTS}"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --no-kibana \
  --with-agent-java-spring \
  --force-build \
  --no-xpack-secure"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-java docker-test-agent-java
