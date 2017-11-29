#!/usr/bin/env bash

set -ex

export TEST_CMD="pytest tests/server/ -v"

make dockerized_tests
