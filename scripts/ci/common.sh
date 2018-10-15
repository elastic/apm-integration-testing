#!/usr/bin/env bash
function stopEnv() {
  make stop-env
}

function runTests() {
  targets=""
  if [ -z "${REUSE_CONTAINERS}" ]; then
    trap "stopEnv" EXIT
    targets="destroy-env"
  fi
  targets="${targets} $@"
  export VENV=${VENV:-${TMPDIR:-/tmp/}venv-$$}
  make ${targets}
}

if [ ! -z "${APM_SERVER_BRANCH}" ]; then
  export BUILD_OPTS="${BUILD_OPTS} --apm-server-build https://github.com/elastic/apm-server.git@${APM_SERVER_BRANCH}"
fi

if [ -z "${DISABLE_BUILD_PARALLEL}" ]; then
  export BUILD_OPTS="${BUILD_OPTS} --build-parallel"
fi

# assume we're under CI if BUILD_NUMBER is set
if [ -n "${BUILD_NUMBER}" ]; then
  # kill any running containers under CI
  docker ps -aq | xargs -t docker rm -f || true
fi
