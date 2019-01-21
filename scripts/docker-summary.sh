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
  
  DOCKER_CONTAINER_NO_OK=$(docker ps -aq -f id=${id} -f status=dead && docker ps -aq -f id=${id} -f status=exited && docker ps -aq -f id=${id} -f health=unhealthy)
  [ -n "${DOCKER_CONTAINER_NO_OK}" ] && docker inspect ${id}
done
echo "*******************************************************"
