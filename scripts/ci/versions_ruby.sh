#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, ruby agent version spec and stack version must be provided"
  exit 2
fi

version_state=${1%;*}
version=${1#*;}
stack_args=${2//;/ }

export COMPOSE_ARGS="${stack_args} --with-agent-ruby-rails --ruby-agent-version=${version} --ruby-agent-version-state=${version_state} --force-build --build-parallel"
srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
${srcdir}/ruby.sh
