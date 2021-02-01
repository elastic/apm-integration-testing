#!/usr/bin/env bash
# This script is in charge to read the latest go version supported in apm-server and upgrade its references
# The contract will be always:
#  1) Gather the go version from the upstream
#  2) Update the references
#  3) Commit changes

GO_VERSION=$(curl -s https://raw.githubusercontent.com/elastic/apm-server/master/.go-version)

sed -i.bck "s#go_version=.*#go_version=${GO_VERSION}#g" docker/apm-server/Dockerfile
git add docker/apm-server/Dockerfile
git commit -m "Bump Go version '${GO_VERSION}'"

# The push is now delegated to the executor of this script.
