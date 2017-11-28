#!/usr/bin/env bash

set -ex 

python scripts/wait_until_services_running.py ${URLS}
./scripts/run_test_cmd.sh
