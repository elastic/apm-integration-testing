#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

REUSE_CONTAINERS=1
srcdir=$(dirname "${0}")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"

prepareAndRunGoals test-docker-bump