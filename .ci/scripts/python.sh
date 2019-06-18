#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

if [ -n "${APM_AGENT_PYTHON_VERSION}" ]; then
  APM_AGENT_PYTHON_VERSION=${APM_AGENT_PYTHON_VERSION/'github;'/'git+https://github.com/elastic/apm-agent-python.git@'}
  APM_AGENT_PYTHON_VERSION=${APM_AGENT_PYTHON_VERSION/'release;'/'elastic-apm=='}
  if [ "${APM_AGENT_PYTHON_VERSION}" = "elastic-apm==latest" ]; then
    APM_AGENT_PYTHON_VERSION="elastic-apm"
  fi
  BUILD_OPTS="--python-agent-package='${APM_AGENT_PYTHON_VERSION}' ${BUILD_OPTS}"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-python-django --with-agent-python-flask --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-python docker-test-agent-python
