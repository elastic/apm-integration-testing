#!/usr/bin/env bash
#
# Given the stack version this script will bump the release version.
#
# This script is executed by the automation we are putting in place
# and it requires the git add/commit commands.
#
# Parameters:
#	$1 -> the release version to be bumped. Mandatory.
#
set -euo pipefail
MSG="parameter missing."
RELEASE_VERSION=${1:?$MSG}
MINOR_MAJOR_RELEASE_VERSION=${RELEASE_VERSION%.*}

OS=$(uname -s| tr '[:upper:]' '[:lower:]')

if [ "${OS}" == "darwin" ] ; then
	SED="sed -i .bck"
else
	SED="sed -i"
fi

CLI_FILE=scripts/modules/cli.py
echo "Update stack with versions ${RELEASE_VERSION} in ${CLI_FILE}"
# Update patch for major.minor
${SED} -E -e "s#('${MINOR_MAJOR_RELEASE_VERSION}'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
# Update patch for master and main
${SED} -E -e "s#('main'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
${SED} -E -e "s#('master'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
# Create a new minor release entry
if grep -q "'${MINOR_MAJOR_RELEASE_VERSION}'" ${CLI_FILE} ; then
	echo "No required changes in the ${CLI_FILE}"
else
	TEMP_FILE=$(mktemp)
	${SED} -E -e "s#(.*'main'.*)#        '${MINOR_MAJOR_RELEASE_VERSION}': '${RELEASE_VERSION}',£\1#g" ${CLI_FILE}
	tr '£' '\n' < ${CLI_FILE} > "$TEMP_FILE" && mv "$TEMP_FILE" ${CLI_FILE}
fi
git add "${CLI_FILE}"

SCRIPT_COMMON=.ci/scripts/common.sh
echo "Update stack with versions ${RELEASE_VERSION} in ${SCRIPT_COMMON}"
# Update patch.
${SED} -E -e 's#^(ELASTIC_STACK_VERSION=\$\{ELASTIC_STACK_VERSION:-)(.*)\}#\1'"'${RELEASE_VERSION}'"'\}#g' "${SCRIPT_COMMON}"
git add "${SCRIPT_COMMON}"

git diff --staged --quiet || git commit -m "[Automation] Update elastic stack release version to ${RELEASE_VERSION}"
git --no-pager log -1

echo "You can now push and create a Pull Request"
