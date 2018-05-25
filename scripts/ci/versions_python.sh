#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, python_agent_version and apm_server_version must be provided"
  exit 2
fi

export COMPOSE_ARGS="start $2 --with-agent-python-django --with-agent-python-flask --agent-python-version=$1  --force-build"
srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
${srcdir}/python.sh
