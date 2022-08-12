#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

export REUSE_CONTAINERS=1
srcdir=$(dirname "${0}")
test -z "$srcdir" && srcdir=.
# shellcheck disable=SC1090
. "${srcdir}/common.sh"
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

prepareAndRunGoals test-docker-bump
