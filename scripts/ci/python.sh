#!/bin/bash -e

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

# github;version -> pip install elastic-apm==git+https://github.com/elastic/apm-agent-python.git@version
# release;latest -> pip install elastic-apm
# release;release -> pip install elastic-apm==version
if [ ! -z "${APM_AGENT_PYTHON_PKG}" ]; then
  APM_AGENT_PYTHON_PKG=${APM_AGENT_PYTHON_PKG/'github;'/'git+https://github.com/elastic/apm-agent-python.git@'}
  APM_AGENT_PYTHON_PKG=${APM_AGENT_PYTHON_PKG/'release;'/'elastic-apm=='}
  export BUILD_OPTS="${BUILD_OPTS} --python-agent-package='${APM_AGENT_PYTHON_PKG}'"
fi

DEFAULT_COMPOSE_ARGS="${ELASTIC_STACK_VERSION:-'master'} ${BUILD_OPTS} --no-apm-server-dashboards --no-kibana --with-agent-python-django --with-agent-python-flask --force-build"
export COMPOSE_ARGS=${COMPOSE_ARGS:-${DEFAULT_COMPOSE_ARGS}}
runTests env-agent-python docker-test-agent-python
