#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
<<<<<<< HEAD
# shellcheck disable=SC1090,SC1091
. "${srcdir}/common.sh"

if [ -n "${APM_AGENT_PHP_VERSION}" ]; then
  EXTRA_OPTS=${APM_AGENT_PHP_VERSION/'github;'/'--php-agent-version='}
  EXTRA_OPTS=${EXTRA_OPTS/'release;'/'--php-agent-release='}
  EXTRA_OPTS=${EXTRA_OPTS/'commit;'/'--php-agent-version='}
  BUILD_OPTS="${BUILD_OPTS} ${EXTRA_OPTS}"
fi

=======
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

>>>>>>> bc74219 (add basic PHP agent integration tests (#863))
DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --with-agent-php-apache \
  --apm-server-agent-config-poll=1s \
  --force-build \
<<<<<<< HEAD
  --no-kibana \
=======
>>>>>>> bc74219 (add basic PHP agent integration tests (#863))
  --no-xpack-secure"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-php docker-test-agent-php
