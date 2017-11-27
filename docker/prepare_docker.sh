#!/usr/bin/env bash

set -x

containers=$(docker ps -a -q)
if [[ ! -z ${containers} ]]; then
  docker stop ${containers}
  docker rm ${containers}
fi
docker volume prune -f

set -e

if [[ ! -z ${NETWORK} ]]; then
  nw_ct=$(docker network ls -q --filter="name=${NETWORK}" | wc -l)
  if [[ ${nw_ct} -eq 0 ]]; then
    docker network create ${NETWORK}
  fi
fi
