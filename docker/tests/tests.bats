#!/usr/bin/env bats

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'
load test_helpers

IMAGE="apm-integration-testing-tests-${DOCKERFILE//\//-}"
CONTAINER="apm-integration-testing-tests-${DOCKERFILE//\//-}"

@test "${DOCKERFILE} - build image" {
	cd $BATS_TEST_DIRNAME/..
	# Simplify the makefile as it does fail with '/bin/sh: 1: Bad substitution' in the CI
	if [ ! -e ${DOCKERFILE} ] ; then
		DOCKERFILE="${DOCKERFILE//-/\/}"
	fi
	run docker build -t ${IMAGE} ${DOCKERFILE}
	assert_success
}

@test "${DOCKERFILE} - clean test containers" {
	cleanup $CONTAINER
}

@test "${DOCKERFILE} - create test container" {
	run docker run -d --name $CONTAINER -P ${IMAGE}
	assert_success
}

@test "${DOCKERFILE} - test container is running" {
	sleep 1
	run docker inspect -f {{.State.Running}} $CONTAINER
	assert_output --partial 'true'
}

@test "${DOCKERFILE} - clean test containers" {
	cleanup $CONTAINER
}
