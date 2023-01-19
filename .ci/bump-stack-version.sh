#!/usr/bin/env bash
#
# Given the stack version this script will bump the version.
#
# This script is executed by the automation we are putting in place
# and it requires the git add/commit commands.
#
# Parameters:
#	$1 -> the version to be bumped. Mandatory.
#	$2 -> whether to create a branch where to commit the changes to.
#		  this is required when reusing an existing Pull Request.
#		  Optional. Default true.
#
set -euo pipefail
MSG="parameter missing."
VERSION=${1:?$MSG}
CREATE_BRANCH=${2:-true}
MINOR_MAJOR_VERSION=${VERSION%-*}

OS=$(uname -s| tr '[:upper:]' '[:lower:]')

if [ "${OS}" == "darwin" ] ; then
	SED="sed -i .bck"
else
	SED="sed -i"
fi

CLI_FILE=scripts/modules/cli.py
echo "Update stack with versions ${VERSION} in ${CLI_FILE}"
# Update patch for master and main
${SED} -E -e "s#('main'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${MINOR_MAJOR_VERSION}'#g" ${CLI_FILE}
${SED} -E -e "s#('master'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${MINOR_MAJOR_VERSION}'#g" ${CLI_FILE}

echo "Commit changes"
if [ "$CREATE_BRANCH" = "true" ]; then
	base=$(git rev-parse --abbrev-ref HEAD | sed 's#/#-#g')
	git checkout -b "update-stack-version-$(date "+%Y%m%d%H%M%S")-${base}"
else
	echo "Branch creation disabled."
fi
git add "${CLI_FILE}"

git diff --staged --quiet || git commit -m "[Automation] Update elastic stack version to ${MINOR_MAJOR_VERSION}"
git --no-pager log -1

echo "You can now push and create a Pull Request"
