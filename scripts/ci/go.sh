#!/bin/bash -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

# version -> go get github.com/elastic/apm-agent-go && cd $GOPATH/src/github.com/elastic/apm-agent-go && git checkout -b ${go_agent_version} && cd -
if [ -n "${APM_AGENT_GO_PKG}" ]; then
  APM_AGENT_GO_PKG=${APM_AGENT_GO_PKG/'github;'/''}
  APM_AGENT_GO_PKG=${APM_AGENT_GO_PKG/'release;'/''}
  BUILD_OPTS="${BUILD_OPTS} --go-agent-package='${APM_AGENT_GO_PKG}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-go-net-http --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}

runTests env-agent-go docker-test-agent-go
