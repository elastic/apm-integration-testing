#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. ${srcdir}/common.sh

if [ -n "${APM_AGENT_RUBY_VERSION}" ]; then
  RUBY_AGENT_VERSION=${APM_AGENT_RUBY_VERSION#*;}
  RUBY_MAJOR_VERSION=${RUBY_AGENT_VERSION%.*}

  ## For 2.x and some other apm-agent-ruby branches let's use the major version to configure
  ## the railsapp docker image with the correct ruby version. By default, it uses latest.
  RE='^[0-9]+$'
  if [[ $RUBY_MAJOR_VERSION =~ $RE ]] ; then
    BUILD_OPTS="${BUILD_OPTS} --ruby-version='${RUBY_MAJOR_VERSION}'"
  fi
  BUILD_OPTS="${BUILD_OPTS} --ruby-agent-version='${RUBY_AGENT_VERSION}' --ruby-agent-version-state='${APM_AGENT_RUBY_VERSION%;*}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --with-agent-ruby-rails --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-ruby docker-test-agent-ruby
