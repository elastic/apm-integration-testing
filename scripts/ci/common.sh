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
