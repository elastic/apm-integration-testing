#!/bin/bash -e

DEFAULT_COMPOSE_ARGS="master --with-agent-ruby-rails --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
make stop-env env-agent-ruby docker-test-agent-ruby
