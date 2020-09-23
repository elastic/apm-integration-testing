#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

if [ -n "${APM_AGENT_PYTHON_VERSION}" ]; then
  APM_AGENT_PYTHON_VERSION=${APM_AGENT_PYTHON_VERSION/'github;'/'git+https://github.com/elastic/apm-agent-python.git@'}
  APM_AGENT_PYTHON_VERSION=${APM_AGENT_PYTHON_VERSION/'release;'/'elastic-apm=='}
  if [ "${APM_AGENT_PYTHON_VERSION}" = "elastic-apm==latest" ]; then
    APM_AGENT_PYTHON_VERSION="elastic-apm"
  fi
  BUILD_OPTS="${BUILD_OPTS} --python-agent-package='${APM_AGENT_PYTHON_VERSION}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --with-agent-python-django \
  --with-agent-python-flask \
  --apm-server-agent-config-poll=1s \
  --force-build \
  --no-xpack-secure \
  --apm-log-level=debug"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-python docker-test-agent-python
