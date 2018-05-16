#!/usr/bin/env bash

set -ex

export AGENTS="go"
export TEST_CMD="pytest tests/agent/test_go.py -v"

make dockerized_tests
