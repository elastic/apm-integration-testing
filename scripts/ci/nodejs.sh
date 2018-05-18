#!/bin/bash -e

DEFAULT_COMPOSE_ARGS="master --with-agent-nodejs-express --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
make stop-env env-agent-nodejs docker-test-agent-nodejs
