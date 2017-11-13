#!/usr/bin/env bash

containers=$(docker ps -a -q)
if [[ ! -z ${containers} ]]; then
  docker stop ${containers}
  docker rm ${containers}
fi
docker volume prune -f

if [[ ! -z ${NETWORK} ]]; then
  docker network rm ${NETWORK}
fi

exit 0
