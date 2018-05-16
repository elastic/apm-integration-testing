#!/usr/bin/env bash

set -ex 

export AGENTS="nodejs,python,ruby,go"
export TEST_CMD="pytest -v"
export TEST_KIBANA=1

make dockerized_tests
