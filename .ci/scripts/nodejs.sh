#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

if [ -n "${APM_AGENT_NODEJS_VERSION}" ]; then
  APM_AGENT_NODEJS_VERSION=${APM_AGENT_NODEJS_VERSION/'github;'/'elastic/apm-agent-nodejs#'}
  APM_AGENT_NODEJS_VERSION=${APM_AGENT_NODEJS_VERSION/'release;'/'elastic-apm-node@'}
  BUILD_OPTS="${BUILD_OPTS} --nodejs-agent-package='${APM_AGENT_NODEJS_VERSION}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --no-apm-server-self-instrument \
  --with-agent-nodejs-express \
  --force-build \
  --apm-log-level=debug"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-nodejs docker-test-agent-nodejs
