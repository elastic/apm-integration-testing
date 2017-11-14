#!/usr/bin/env bash

set -ex

export AGENTS="nodejs"
export TEST_CMD="pytest tests/agent/test_nodejs.py -v"

python ./scripts/start_services.py
