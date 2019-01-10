#!/usr/bin/env bash
set -exuo pipefail

echo "***************Docker Containers Summary***************"
docker ps -a --no-trunc

DOCKER_IDS=$(docker ps -aq)

for id in ${DOCKER_IDS}
do
  echo "***************Docker Container ${id}***************"
  docker ps -af id=${id}
  docker logs ${id}
  docker inspect ${id}
done
echo "*******************************************************"
