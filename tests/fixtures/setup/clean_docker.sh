#!/usr/bin/env bash

if [ $# -lt 2 ]; then
  echo 'Missing arguments, provide "container_name" to clear and "network_name" to create'
  exit 2
fi


containers=$(docker ps -a -q --filter="name=$1")
if [[ ! -z ${containers} ]]; then
  docker stop ${containers}
  docker rm ${containers}
fi
docker volume prune -f

nw_ct=$(docker network ls -q --filter="name=$2" | wc -l)
if [[ ${nw_ct} -eq 0 ]]; then
  docker network create $2
fi

exit 0
