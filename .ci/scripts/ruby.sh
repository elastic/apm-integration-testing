#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

if [ -n "${APM_AGENT_RUBY_VERSION}" ]; then
  BUILD_OPTS="${BUILD_OPTS} --ruby-agent-version='${APM_AGENT_RUBY_VERSION#*;}' --ruby-agent-version-state='${APM_AGENT_RUBY_VERSION%;*}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-ruby-rails --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-ruby docker-test-agent-ruby
