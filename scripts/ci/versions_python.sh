#!/usr/bin/env bash

set -ex

if [ $# -lt 2 ]; then
  echo "Argument missing, python_agent_version and apm_server_version must be provided"
  exit 2
fi

version_type=${1%;*}
version=${1#*;}
stack_version=$2

# use release version by default
python_pkg="elastic-apm==${version}"
if [[ ${version_type} == github ]]; then
  python_pkg="git+https://github.com/elastic/apm-agent-python.git@${version}"
else
  if [[ ${version} == latest ]]; then
    python_pkg="elastic-apm"
  fi
fi

export COMPOSE_ARGS="$2 --no-kibana --with-agent-python-django --with-agent-python-flask --python-agent-package='${python_pkg}' --force-build"
srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
${srcdir}/python.sh
