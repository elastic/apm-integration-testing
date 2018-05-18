#!/bin/bash -e

DEFAULT_COMPOSE_ARGS="master --with-agent-python-django --with-agent-python-flask --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
make stop-env env-agent-python docker-test-agent-python
