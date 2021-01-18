#!/usr/bin/env bash
set -euo pipefail

# Takes as arguments the apm-server binary path and the apm-server binary file name; 
# and uncompresses it in the right folder inside the elastic-agent container (must be running)

# Path and file name are separated arguments because the former comes from user input, and the later does not
# This is because if the file name comes from the user and is not what elastic agent expects, 
# it will be very hard to debug why it doesn't work

elastic_agent_id=$(docker ps -qf "name=elastic-agent")
sha=$(docker inspect "$elastic_agent_id" | grep org.label-schema.vcs-ref | awk -F ": \"" '{print $2}' | head -c 6)
dst=/usr/share/elastic-agent/data/elastic-agent-"$sha"/install/${2%".tar.gz"}

echo "copying ${1}/${2} to $elastic_agent_id:$dst"
docker exec "$elastic_agent_id" mkdir "$dst"
docker cp "${1}/${2}" "$elastic_agent_id":"$dst"

echo "uncompressing $dst/${2}"
# we need to set the destination folder explicitly to avoid errors in case the user has manually renamed the binary file 
# (ie, after mage package)
docker exec "$elastic_agent_id" tar zxvf "$dst"/${2} -C "$dst" --strip-components 1
docker exec "$elastic_agent_id" rm "$dst"/${2}

