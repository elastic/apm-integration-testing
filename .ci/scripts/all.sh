#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} --no-apm-server-dashboards --no-apm-server-self-instrument --with-agent-nodejs-express --with-agent-python-django --with-agent-python-flask --with-agent-ruby-rails --force-build --nodejs-agent-package='elastic-apm-node@1.x' --python-agent-package='git+https://github.com/elastic/apm-agent-python.git@3.x' --ruby-agent-version-state=github  --ruby-agent-version=1.x"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-all docker-test-all
