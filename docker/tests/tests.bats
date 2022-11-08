#!/usr/bin/env bats
# shellcheck disable=SC2031,SC2030

load 'test_helper/bats-support/load'
load 'test_helper/bats-assert/load'
load test_helpers

CONTAINER="it_${DOCKERFILE//\//-}"
IMAGE="docker.elastic.co/observability-ci/${CONTAINER}"

@test "${DOCKERFILE} - build image" {
	cd "$BATS_TEST_DIRNAME/.."
	# Simplify the makefile as it does fail with '/bin/sh: 1: Bad substitution' in the CI
	if [ ! -e "${DOCKERFILE}" ] ; then
		DOCKERFILE="${DOCKERFILE//-//}"
	fi
	run docker build --rm -t "${IMAGE}" "${DOCKERFILE}"
	assert_success
}

@test "${DOCKERFILE} - clean test containers" {
	cleanup "$CONTAINER"
}

@test "${DOCKERFILE} - create test container" {
	run docker run -d --name "$CONTAINER" -P "${IMAGE}"
	assert_success
}

@test "${DOCKERFILE} - test container with 0 as exitcode" {
	if [ "${DOCKERFILE}" = "opbeans-go" ]; then
		skip "${DOCKERFILE} does require some other docker services."
	fi
	sleep 1
	run docker inspect -f '{{.State.ExitCode}}' "$CONTAINER"
	assert_output '0'
}

@test "${DOCKERFILE} - clean test containers afterwards" {
	cleanup "$CONTAINER"
}
