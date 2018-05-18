#!/bin/bash -e

DEFAULT_COMPOSE_ARGS="master --with-agent-go-net-http --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
make stop-env env-agent-go docker-test-agent-go
