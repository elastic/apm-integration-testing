#!/usr/bin/env bash
set -exuo pipefail

echo "***************Docker Containers Summary***************"
docker ps -a

DOCKER_IDS=$(docker ps -aq)

for id in ${DOCKER_IDS}
do
  echo "***************Docker Container ${id}***************"
  docker ps -af id=${id} --no-trunc
  docker logs ${id}
  docker ps -aq -f id=${id} -f status=dead -f status=exited -f health=unhealthy|xargs -n1 -t docker inspect
done
echo "*******************************************************"
