#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, python_agent_version and apm_server_version must be provided"
  exit 2
fi

export PYTHON_AGENT_VERSION=$1
export APM_SERVER_VERSION=$2

export AGENTS="python"
export TEST_CMD="pytest tests/agent/test_python.py -v -m version"

python ./scripts/start_services.py
