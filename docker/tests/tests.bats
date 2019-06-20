#!/usr/bin/env bats

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'
load test_helpers

IMAGE="apm-integration-testing-tests-${DOCKERFILE}"
CONTAINER="apm-integration-testing-tests-${DOCKERFILE}"

@test "build image" {
	cd $BATS_TEST_DIRNAME/..
	docker build -t ${IMAGE} ${DOCKERFILE}
}

@test "clean test containers" {
	cleanup $CONTAINER
}

@test "create test container" {
	run docker run -d --name $CONTAINER -P ${IMAGE}
	assert_success
}

@test "test container is running" {
	sleep 1
	run docker inspect -f {{.State.Running}} $CONTAINER
	assert_output --partial 'true'
}

@test "clean test containers" {
	cleanup $CONTAINER
}
