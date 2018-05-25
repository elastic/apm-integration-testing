#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, ruby_agent_version and apm_server_version must be provided"
  exit 2
fi

export COMPOSE_ARGS="start $2 --with-agent-ruby-rails --agent-ruby-version=$1  --force-build"
srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
${srcdir}/ruby.sh
