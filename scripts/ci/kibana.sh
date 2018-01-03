#!/usr/bin/env bash -ex

export TEST_CMD="pytest tests/kibana/test_integration.py -v"
export TEST_KIBANA=1

make dockerized_tests
