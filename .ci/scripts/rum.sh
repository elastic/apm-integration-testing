#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

if [ -n "${APM_AGENT_RUM_VERSION}" ]; then
  APM_AGENT_RUM_VERSION=${APM_AGENT_RUM_VERSION/'github;'/''}
  APM_AGENT_RUM_VERSION=${APM_AGENT_RUM_VERSION/'release;'/''}
  APM_AGENT_RUM_VERSION=${APM_AGENT_RUM_VERSION/'commit;'/''}
  BUILD_OPTS="--rum-agent-branch='${APM_AGENT_RUM_VERSION}' ${BUILD_OPTS}"
fi

#--with-agent-python-django
DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-rumjs --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-rum docker-test-agent-rum
