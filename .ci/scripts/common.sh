#!/usr/bin/env bash
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

function stopEnv() {
  make stop-env
}

function runTests() {
  targets=""
  if [ -z "${REUSE_CONTAINERS}" ]; then
    trap "stopEnv" EXIT
    targets="destroy-env"
  fi
  targets="${targets} $*"
  export VENV=${VENV:-${TMPDIR:-/tmp/}venv-$$}
  # shellcheck disable=SC2086
  make ${targets}
}

function prepareAndRunAll() {
  ## This is for the CI
  if [ -d /var/lib/jenkins/.m2/repository ] ; then
    echo "m2 cache folder has been found in the CI worker"
    cp -rf /var/lib/jenkins/.m2/repository docker/java/spring/.m2
    BUILD_OPTS="${BUILD_OPTS} --java-m2-cache"
  else
    echo "m2 cache folder has NOT been found in the CI worker"
  fi

  # export the variables to force the be defined in the Docker container
  export ELASTIC_APM_SECRET_TOKEN=${ELASTIC_APM_SECRET_TOKEN:-"SuPeRsEcReT"}
  export APM_SERVER_URL=${APM_SERVER_URL:-"https://apm-server:8200"}
  export PYTHONHTTPSVERIFY=0
  DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} ${BUILD_OPTS}\
    --no-apm-server-self-instrument \
    --apm-server-enable-tls \
    --no-verify-server-cert  \
    --apm-server-secret-token=${ELASTIC_APM_SECRET_TOKEN} \
    --apm-server-url=${APM_SERVER_URL} \
    --apm-log-level=debug"

  export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
  runTests "$@"
}

function prepareAndRunGoals() {
  DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION} \
    --no-apm-server-self-instrument"
  export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
  runTests "$@"
}

if [ -n "${APM_SERVER_BRANCH}" ]; then
 APM_SERVER_BRANCH_VERSION=${APM_SERVER_BRANCH%;*}
 APM_SERVER_BRANCH_TYPE=${APM_SERVER_BRANCH//$APM_SERVER_BRANCH_VERSION/}
 APM_SERVER_BRANCH_TYPE=${APM_SERVER_BRANCH_TYPE//;/}
 if [ "${APM_SERVER_BRANCH_TYPE}" != "--release" ]; then
  BUILD_OPTS="${BUILD_OPTS} --apm-server-build https://github.com/elastic/apm-server.git@${APM_SERVER_BRANCH_VERSION}"
 else
   ELASTIC_STACK_VERSION="${APM_SERVER_BRANCH_VERSION} --release --apm-server-managed --with-elastic-agent"
 fi
fi

if [ -z "${DISABLE_BUILD_PARALLEL}" ] || [ "${DISABLE_BUILD_PARALLEL}" = "false" ]; then
 BUILD_OPTS="${BUILD_OPTS} --build-parallel"
fi

ELASTIC_STACK_VERSION=${ELASTIC_STACK_VERSION:-"8.8.1"}

echo "ELASTIC_STACK_VERSION=${ELASTIC_STACK_VERSION}"
echo "APM_SERVER_BRANCH_VERSION=${APM_SERVER_BRANCH_VERSION}"
echo "APM_SERVER_BRANCH_TYPE=${APM_SERVER_BRANCH_TYPE}"
echo "BUILD_OPTS=${BUILD_OPTS}"

# Install virtualenv
python3 -m pip install --user virtualenv
