#!/usr/bin/env bash
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

if [ -n "${APM_AGENT_DOTNET_VERSION}" ]; then
  EXTRA_OPTS=${APM_AGENT_DOTNET_VERSION/'github;'/'--dotnet-agent-version='}
  EXTRA_OPTS=${EXTRA_OPTS/'release;'/'--dotnet-agent-release='}
  EXTRA_OPTS=${EXTRA_OPTS/'commit;'/'--dotnet-agent-version='}
  BUILD_OPTS="${BUILD_OPTS} ${EXTRA_OPTS}"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --no-kibana --with-agent-dotnet \
  --force-build \
  --no-xpack-secure \
  --apm-log-level=debug"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-dotnet docker-test-agent-dotnet
