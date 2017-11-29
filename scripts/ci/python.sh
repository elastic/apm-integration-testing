#!/usr/bin/env bash

set -ex

export AGENTS="python"
export TEST_CMD="pytest tests/agent/test_python.py -v"

make dockerized_tests
