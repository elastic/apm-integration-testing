#!/usr/bin/env bash

set -ex 

#export AGENTS="python,nodejs"
export AGENTS="nodejs,python"
export TEST_CMD="pytest"
python ./scripts/start_services.py
