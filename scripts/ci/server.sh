#!/usr/bin/env bash

set -ex

export TEST_CMD="pytest tests/server/ -v"

python ./scripts/start_services.py
