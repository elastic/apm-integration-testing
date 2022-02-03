#!/usr/bin/env bash
# This script is in charge to read the latest go version supported in apm-server and upgrade its references
# The contract will be always:
#  1) Gather the go version from the upstream
#  2) Update the references
#  3) Commit changes

set -euo pipefail

OS=$(uname -s| tr '[:upper:]' '[:lower:]')

if [ "${OS}" == "darwin" ] ; then
	SED="sed -i .bck"
else
	SED="sed -i"
fi

<<<<<<< HEAD
### Queries to the 7.x branch
GO_VERSION=$(curl -s https://raw.githubusercontent.com/elastic/apm-server/7.17/.go-version)
=======
GO_VERSION=$(curl -s https://raw.githubusercontent.com/elastic/apm-server/main/.go-version)
>>>>>>> 53053bd (apm-server: main (#1397))

echo "Update go version ${GO_VERSION}"
${SED} -E -e "s#go_version=.*#go_version=${GO_VERSION}#g" docker/apm-server/Dockerfile

git add docker/apm-server/Dockerfile
git diff --staged --quiet || git commit -m "[Automation] Update go release version to ${GO_VERSION}"
git --no-pager log -1

echo "You can now push and create a Pull Request"
