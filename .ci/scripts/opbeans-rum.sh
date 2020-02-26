#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS} \
  --with-opbeans-go \
  --no-apm-server-dashboards \
  --no-apm-server-self-instrument \
  --apm-server-agent-config-poll=1s \
  --force-build --no-xpack-secure"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests "env-agent-go"

## Use the nginx
docker run -d --rm --name=opbeans-frontend \
      --network="apm-integration-testing" \
      -e ELASTIC_APM_JS_BASE_SERVICE_NAME=opbeans-rum \
      -e ELASTIC_APM_JS_BASE_SERVER_URL="http://localtesting_${ELASTIC_STACK_VERSION}_apm-server:8200" \
      -e ELASTIC_OPBEANS_API_SERVER="http://localtesting_${ELASTIC_STACK_VERSION}_opbeans-go:3000"\
      -p 3000:3000 \
      docker.elastic.co/observability-ci/it_opbeans-frontend_nginx

## Test the service is up and running
http_code=$(curl -s -o /dev/null -w "%{http_code}" http://0.0.0.0:3000/dashboard)
if [ "${http_code}" == "200" ] ; then
  docker logs opbeans-frontend | grep '/dashboard'
  docker stop opbeans-frontend || true
else
  echo 'ERROR: service is not listening.'
  exit 1
fi
