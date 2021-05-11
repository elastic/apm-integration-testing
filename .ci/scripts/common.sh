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

if [ -n "${APM_SERVER_BRANCH}" ]; then
 APM_SERVER_BRANCH_VERSION=${APM_SERVER_BRANCH%;*}
 APM_SERVER_BRANCH_TYPE=${APM_SERVER_BRANCH//$APM_SERVER_BRANCH_VERSION/}
 APM_SERVER_BRANCH_TYPE=${APM_SERVER_BRANCH_TYPE//;/}
 if [ "${APM_SERVER_BRANCH_TYPE}" != "--release" ]; then
  BUILD_OPTS="${BUILD_OPTS} --apm-server-build https://github.com/elastic/apm-server.git@${APM_SERVER_BRANCH_VERSION}"
 else
   ELASTIC_STACK_VERSION="${APM_SERVER_BRANCH_VERSION} --release"
 fi
fi

if [ -z "${DISABLE_BUILD_PARALLEL}" ] || [ "${DISABLE_BUILD_PARALLEL}" = "false" ]; then
 BUILD_OPTS="${BUILD_OPTS} --build-parallel"
fi

<<<<<<< HEAD
ELASTIC_STACK_VERSION=${ELASTIC_STACK_VERSION:-'7.10'}
=======
ELASTIC_STACK_VERSION=${ELASTIC_STACK_VERSION:-'7.12.2'}
>>>>>>> b5ae4e8... feat: update the common.sh script with the current stack version (#1141)

echo "ELASTIC_STACK_VERSION=${ELASTIC_STACK_VERSION}"
echo "APM_SERVER_BRANCH_VERSION=${APM_SERVER_BRANCH_VERSION}"
echo "APM_SERVER_BRANCH_TYPE=${APM_SERVER_BRANCH_TYPE}"
echo "BUILD_OPTS=${BUILD_OPTS}"
