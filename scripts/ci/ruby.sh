#!/usr/bin/env bash

set -ex

export AGENTS="ruby"
export TEST_CMD="pytest tests/agent/test_ruby.py -v"

make dockerized_tests
