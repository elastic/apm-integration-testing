#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

APM_SECRET_TOKEN=${APM_SECRET_TOKEN:-"SuPeRsEcReT"}

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS}\
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --with-agent-rumjs \
  --with-agent-dotnet \
  --with-agent-go-net-http \
  --with-agent-nodejs-express \
  --with-agent-ruby-rails \
  --with-agent-java-spring \
  --with-agent-python-django \
  --with-agent-python-flask \
  --force-build \
  --no-xpack-secure \
  --apm-server-enable-tls \
  --no-verify-server-cert \
  --apm-server-secret-token=SuPeRsEcReT"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
PYTHONHTTPSVERIFY=0 APM_SERVER_URL="https://apm-server:8200" runTests env-agent-all docker-test-all
