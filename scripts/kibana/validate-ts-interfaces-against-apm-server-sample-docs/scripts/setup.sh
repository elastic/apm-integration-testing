#!/usr/bin/env bash

rm -rf tmp
mkdir tmp
mkdir tmp/apm-server-docs

# download apm server samples
yarn ts-node ./scripts/download-sample-docs.ts "$1" "$2"

# Clone kibana and copy ts interfaces
./scripts/clone-kibana.sh "$3" "$4"
