#!/bin/bash -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

# github;version -> npm install elastic/apm-agent-nodejs#version
# release;version -> npm install elastic-apm-node@version
if [ -n "${APM_AGENT_NODEJS_PKG}" ]; then
  APM_AGENT_NODEJS_PKG=${APM_AGENT_NODEJS_PKG/'github;'/'elastic/apm-agent-nodejs#'}
  APM_AGENT_NODEJS_PKG=${APM_AGENT_NODEJS_PKG/'release;'/'elastic-apm-node@'}
  BUILD_OPTS="${BUILD_OPTS} --nodejs-agent-package='${APM_AGENT_NODEJS_PKG}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-nodejs-express --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-nodejs docker-test-agent-nodejs
