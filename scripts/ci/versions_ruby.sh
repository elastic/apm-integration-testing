#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, ruby_agent_version and apm_server_version must be provided"
  exit 2
fi

export ruby_AGENT_VERSION=$1
export APM_SERVER_VERSION=$2

export AGENTS="ruby"
export TEST_CMD="pytest tests/agent/test_ruby.py -v -m version"

make dockerized_tests
