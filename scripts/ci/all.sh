#!/usr/bin/env bash

set -ex 

#export AGENTS="python,nodejs"
export AGENTS="nodejs,python"
export TEST_CMD="pytest -v"
export TEST_KIBANA=1

make dockerized_tests
