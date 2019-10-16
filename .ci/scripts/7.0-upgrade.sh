#!/bin/bash -ex

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck source=/dev/null
. "${srcdir}/common.sh"

export COMPOSE_ARGS="6.6 --release --force-build --build-parallel \
  --no-apm-server-dashboards --no-apm-server-self-instrument \
  --elasticsearch-data-dir '' \
  --no-apm-server-pipeline --all-opbeans --no-kibana\
  --opbeans-dotnet-version=1.1.1\
  --opbeans-go-agent-branch=1.x\
  --opbeans-java-agent-branch=v1.10.0\
  --opbeans-node-agent-branch=v3.0.0\
  --opbeans-python-agent-branch=v5.2.1\
  --opbeans-ruby-agent-branch=v3.0.0"
make start-env docker-compose-wait

# let opbeans apps generate some data
sleep 60

# upgrade elasticsearch, remove all other services
export COMPOSE_ARGS="7.0.0 --no-apm-server --elasticsearch-data-dir '' --remove-orphans"

# install 6.x* index pattern for v1 tests
docker run --rm --network apm-integration-testing docker.elastic.co/apm/apm-server:6.7.1 apm-server setup --template -e -E setup.template.pattern='apm-6.x*' -E setup.template.name=apm-6.x

make start-env docker-compose-wait test-upgrade
