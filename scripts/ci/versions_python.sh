#!/usr/bin/env bash

set -ex

export AGENTS="python"
export TEST_CMD="pytest tests/agent/test_python.py -v -m version"

python ./scripts/start_services.py
