#!/usr/bin/env bash
set -euo pipefail

echo "***************Docker Containers Summary***************"
docker ps -a

DOCKER_IDS=$(docker ps -aq)

for id in ${DOCKER_IDS}
do
  echo "***************Docker Container ${id}***************"
  docker ps -af id=${id} --no-trunc
  docker logs ${id} | tail -n 10 || echo "It is not possible to grab the logs of ${id}"
done
echo "*******************************************************"
