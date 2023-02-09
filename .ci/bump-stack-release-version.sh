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

    if grep -q "'${MINOR_MAJOR_RELEASE_VERSION}':" ${CLI_FILE} ; then
      ## Update new major.minor.patch
      ${SED} -E -e "s#('${MINOR_MAJOR_RELEASE_VERSION}'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
    else
      ## Add new major.minor
      ${SED} -E -e "s&(# UPDATECLI_AUTOMATION.*)&'${MINOR_MAJOR_RELEASE_VERSION}': '${RELEASE_VERSION}',\n        \1&g" ${CLI_FILE}
    fi
  fi

  # Report on stdout
  if grep -q "'${MINOR_MAJOR_RELEASE_VERSION}':" ${CLI_FILE} ; then
      ## Update new major.minor.patch
    sed -E -e "s#('${MINOR_MAJOR_RELEASE_VERSION}'): '[0-9]+\.[0-9]+\.[0-9]'#\1: '${RELEASE_VERSION}'#g" ${CLI_FILE}
  else
    ## Add new major.minor
    sed -E -e "s&(# UPDATECLI_AUTOMATION.*)&'${MINOR_MAJOR_RELEASE_VERSION}': '${RELEASE_VERSION}',\n        \1&g" ${CLI_FILE}
  fi
  exit 0
fi
