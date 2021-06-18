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
# Update patch.
${SED} -E -e "s#('${MINOR_MAJOR_RELEASE_VERSION}'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
# Create a new minor release entry
if grep -q "${MINOR_MAJOR_RELEASE_VERSION}" ${CLI_FILE} ; then
	echo "No required changes in the ${CLI_FILE}"
else
	TEMP_FILE=$(mktemp)
	${SED} -E -e "s#(.*'master'.*)#        '${MINOR_MAJOR_RELEASE_VERSION}': '${RELEASE_VERSION}',£\1#g" ${CLI_FILE}
	tr '£' '\n' < ${CLI_FILE} > "$TEMP_FILE" && mv "$TEMP_FILE" ${CLI_FILE}
fi
git add "${CLI_FILE}"

APM_SERVER_FILE=tests/versions/apm_server.yml
echo "Update stack with versions ${RELEASE_VERSION} in ${APM_SERVER_FILE}"
if grep -q 'master' ${APM_SERVER_FILE} ; then
	echo "No required changes in the ${APM_SERVER_FILE}"
else
	if grep -q "${MINOR_MAJOR_RELEASE_VERSION}" ${APM_SERVER_FILE} ; then
		echo "${MINOR_MAJOR_RELEASE_VERSION} already exists."
	else
		TEMP_FILE=$(mktemp)
		${SED} -E -e "s#(  - '7.x')#\1|  - '${MINOR_MAJOR_RELEASE_VERSION};--release'#g" ${APM_SERVER_FILE}
		tr '|' '\n' < ${APM_SERVER_FILE} > "$TEMP_FILE" && mv "$TEMP_FILE" ${APM_SERVER_FILE}
	fi
fi
git add "${APM_SERVER_FILE}"

SCRIPT_COMMON=.ci/scripts/common.sh
echo "Update stack with versions ${RELEASE_VERSION} in ${SCRIPT_COMMON}"
# Update patch.
${SED} -E -e 's#^(ELASTIC_STACK_VERSION=\$\{ELASTIC_STACK_VERSION:-)(.*)\}#\1'"'${RELEASE_VERSION}'"'\}#g' "${SCRIPT_COMMON}"
git add "${SCRIPT_COMMON}"

## Update EC and ECK pipelines accordingly
for FILE in ".ci/integrationTestEC.groovy" ".ci/integrationTestECK.groovy" ; do
  echo "Update stack with versions ${RELEASE_VERSION} in ${FILE}"
  ${SED} -E -e "s#(values '7.x',) '[0-9]+\.[0-9]+\.[0-9]+'#\1 '${RELEASE_VERSION}'#g" "${FILE}"
  git add "${FILE}"
done

git diff --staged --quiet || git commit -m "[Automation] Update elastic stack release version to ${RELEASE_VERSION}"
git --no-pager log -1

echo "You can now push and create a Pull Request"
