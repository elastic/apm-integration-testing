#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, nodejs_agent_version and apm_server_version must be provided"
  exit 2
fi

export NODEJS_AGENT_VERSION=$1
export APM_SERVER_VERSION=$2

export AGENTS="nodejs"
export TEST_CMD="pytest tests/agent/test_nodejs.py -v -m version"

python ./scripts/start_services.py
