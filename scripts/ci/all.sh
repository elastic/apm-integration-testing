#!/bin/bash -e

DEFAULT_COMPOSE_ARGS="master --with-agent-go-net-http --with-agent-nodejs-express --with-agent-python-django --with-agent-python-flask --with-agent-ruby-rails --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
make stop-env env-agent-all docker-test-all
