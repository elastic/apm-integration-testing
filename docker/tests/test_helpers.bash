#!/usr/bin/env bats

# check dependencies
(
    type docker &>/dev/null || ( echo "docker is not available"; exit 1 )
    type curl &>/dev/null || ( echo "curl is not available"; exit 1 )
)>&2

function cleanup {
	docker kill "$1" &>/dev/null ||:
    docker rm -fv "$1" &>/dev/null ||:
}
