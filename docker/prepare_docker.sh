#!/usr/bin/env bash

containers=$(docker ps -a -q)
if [[ ! -z ${containers} ]]; then
  docker stop ${containers}
fi
docker volume prune -f

set -ex

if [[ ! -z ${NETWORK} ]]; then
  nw_ct=$(docker network ls -q --filter="name=${NETWORK}" | wc -l)
  if [[ ${nw_ct} -eq 0 ]]; then
    docker network create ${NETWORK}
  fi
fi
