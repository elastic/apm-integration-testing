#!/bin/bash -ex

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.
. ${srcdir}/common.sh

export COMPOSE_ARGS="6.6 --no-apm-server-dashboards --no-apm-server-self-instrument --apm-server-count 2 --apm-server-tee --elasticsearch-data-dir '' --all --no-kibana"
make start-env docker-compose-wait

# let opbeans apps generate some data
sleep 10

# upgrade elasticsearch, remove all other services
export COMPOSE_ARGS="master --no-apm-server --elasticsearch-data-dir '' --no-kibana --remove-orphans"
make start-env docker-compose-wait test-upgrade
