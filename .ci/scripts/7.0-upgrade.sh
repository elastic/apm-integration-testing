#!/bin/bash -ex

srcdir=$(dirname "$0")
test -z "$srcdir" && srcdir=.
# shellcheck source=/dev/null
. "${srcdir}/common.sh"

docker build --build-arg GO_AGENT_BRANCH=v1.6.0 --build-arg OPBEANS_GO_BRANCH=v1.6.0 -t localtesting_6.6.2_opbeans-go docker/opbeans/go
docker build --build-arg JAVA_AGENT_VERSION=v1.10.0 -t localtesting_6.6.2_opbeans-java docker/opbeans/java
docker build --build-arg PYTHON_AGENT_VERSION=v5.2.1 -t localtesting_6.6.2_opbeans-python docker/opbeans/python
docker build --build-arg NODE_AGENT_VERSION=v3.0.0 -t localtesting_6.6.2_opbeans-node docker/opbeans/node
docker build --build-arg RUBY_AGENT_VERSION=v3.0.0 -t localtesting_6.6.2_opbeans-ruby docker/opbeans/ruby
docker build --build-arg DOTNET_AGENT_VERSION=1.1.1 -t localtesting_6.6.2_opbeans-dotnet docker/opbeans/dotnet

export REUSE_CONTAINERS="true"
export COMPOSE_ARGS="6.6 --release \
  --no-apm-server-dashboards --no-apm-server-self-instrument \
  --elasticsearch-data-dir '' \
  --no-apm-server-pipeline --all-opbeans --no-kibana"

make start-env docker-compose-wait

# let opbeans apps generate some data
sleep 60

# upgrade elasticsearch, remove all other services
export COMPOSE_ARGS="7.7 --no-apm-server --elasticsearch-data-dir '' --remove-orphans"

# install 6.x* index pattern for v1 tests
docker run --rm --network apm-integration-testing docker.elastic.co/apm/apm-server:6.7.1 apm-server setup --template -e -E setup.template.pattern='apm-6.x*' -E setup.template.name=apm-6.x

make start-env docker-compose-wait test-upgrade
