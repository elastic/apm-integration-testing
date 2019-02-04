#!/usr/bin/env bash
set -exuo pipefail

mkdir -p docker-info
cd docker-info

docker ps -a &> docker-containers.txt

DOCKER_IDS=$(docker ps -aq)

for id in ${DOCKER_IDS}
do
  docker ps -af id=${id} --no-trunc &> ${id}-cmd.txt
  docker logs ${id} &> ${id}.log
  docker inspect ${id} &> ${id}-inspect.json
done
