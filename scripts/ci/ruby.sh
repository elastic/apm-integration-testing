#!/bin/bash -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

# APM_AGENT_RUBY_PKG='github;version' -> gem 'elastic-apm', git: 'https://github.com/elastic/apm-agent-ruby.git', branch: version
# APM_AGENT_RUBY_PKG='release;latest' -> gem elastic-apm
# APM_AGENT_RUBY_PKG='release;version' -> gem elastic-apm, version
if [ -n "${APM_AGENT_RUBY_PKG}" ]; then
  BUILD_OPTS="${BUILD_OPTS} --ruby-agent-version='${APM_AGENT_RUBY_PKG#*;}' --ruby-agent-version-state='${APM_AGENT_RUBY_PKG%;*}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-ruby-rails --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-ruby docker-test-agent-ruby
