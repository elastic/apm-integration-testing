#!/usr/bin/env bash
#
# The script check the content of the file "scripts/modules/cli.py"
# - if different than $1 and DRY_RUN is set to:
#   - "false" then it updates it with the value of $1
#   - "true" then it only reports the value of $1
# - otherwise it exits without any value reported
#
# Parameters:
#	$1 -> the release version to be bumped. Mandatory.
#

CLI_FILE=scripts/modules/cli.py
RELEASE_VERSION=${1:?$MSG}
MINOR_MAJOR_RELEASE_VERSION=${RELEASE_VERSION%.*}

OS=$(uname -s| tr '[:upper:]' '[:lower:]')

if [ "${OS}" == "darwin" ] ; then
	SED="sed -i .bck"
else
	SED="sed -i"
fi

if grep -q "'${RELEASE_VERSION}'" ${CLI_FILE} ; then
  ## No change
  # early return with no output
  exit 0
else
  if test "$DRY_RUN" == "false" ; then
    ## Value changed to $1" - NO dry run
    # do something such as writing a file here
    ${SED} -E -e "s#('${MINOR_MAJOR_RELEASE_VERSION}'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
  fi
  # Report on stdout
  sed -E -e "s#('${MINOR_MAJOR_RELEASE_VERSION}'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
  exit 0
fi
