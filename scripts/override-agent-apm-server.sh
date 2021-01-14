#!/usr/bin/env bash
set -euo pipefail

# takes as argument the apm-server binary file
# it is expected that the checksum exists with the same name with and a ".sha512" postfix

elastic_agent_id=$(docker ps -qf "name=elastic-agent")
sha=$(docker inspect "$elastic_agent_id" | grep org.label-schema.vcs-ref | awk -F ": \"" '{print $2}' | head -c 6)
dst=/usr/share/elastic-agent/data/elastic-agent-"$sha"/downloads/
echo "copying ${1} and its sha512 to $elastic_agent_id:$dst"
docker cp "${1}" "$elastic_agent_id":"$dst"
docker cp "${1}".sha512 "$elastic_agent_id":"$dst"
