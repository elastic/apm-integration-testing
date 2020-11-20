#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

AGENT=$1
APP=$2
APM_DEBUG=""
if [ "${AGENT}" != "python" ]; then
  APM_DEBUG="--apm-log-level=debug"
fi

## This is for the CI
if [ -d /var/lib/jenkins/.m2/repository ] ; then
  cp -rf /var/lib/jenkins/.m2/repository docker/java/spring/.m2
  BUILD_OPTS="${BUILD_OPTS} --java-m2-cache"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --with-agent-${APP} \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --apm-server-agent-config-poll=1s \
  --force-build --no-xpack-secure \
  ${APM_DEBUG}"

export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests "env-agent-${AGENT}" "docker-test-agent-${AGENT}"
