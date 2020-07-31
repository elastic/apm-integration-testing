#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

if [ -n "${APM_AGENT_GO_VERSION}" ]; then
  APM_AGENT_GO_VERSION=${APM_AGENT_GO_VERSION/'github;'/''}
  APM_AGENT_GO_VERSION=${APM_AGENT_GO_VERSION/'release;'/''}
  APM_AGENT_GO_VERSION=${APM_AGENT_GO_VERSION/'commit;'/''}
  BUILD_OPTS="${BUILD_OPTS} --go-agent-version='${APM_AGENT_GO_VERSION}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --no-kibana \
  --with-agent-go-net-http \
  --force-build \
  --no-xpack-secure \
  --apm-log-level debug"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}

runTests env-agent-go docker-test-agent-go
