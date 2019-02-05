#!/usr/bin/env bash
set -exuo pipefail

STEP=${1:""}

mkdir -p docker-info${STEP}
cd docker-info${STEP}

docker ps -a &> docker-containers.txt

DOCKER_IDS=$(docker ps -aq)

for id in ${DOCKER_IDS}
do
  docker ps -af id=${id} --no-trunc &> ${id}-cmd.txt
  docker logs ${id} &> ${id}.log
  docker inspect ${id} &> ${id}-inspect.json
done
