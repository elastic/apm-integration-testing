#!/usr/bin/env bash
#
# It replaces environment variables values on a folder in a directory.
# It ignores some enviroment variables defined in IGNORE var,
# some boolean values, and any value with less than 4 characters.

FOLDER=${1:-"."}
IGNORE=("PATH" "HOME" "USER" "JAVA_HOME" "MAVEN_HOME" "TMPDIR" "JENKINS_HOME" "JENKINS_URL" "BUILD_NUMBER" "BRANCH_NAME" "GIT_COMMIT" "GIT_SHA" "GIT_BRANCH")
for i in $(env);
do
  V=${i#*=};
  K=${i%=*};

  if [ -z "${V}" ]; then
    continue
  fi

  # shellcheck disable=SC2076
  if [[ " ${IGNORE[*]} " =~ " ${K} " ]]; then
      continue
  fi

  shopt -s nocasematch
  if [ "${V}" == "true" ] || [ "${V}" == "false" ]; then
    continue
  fi

  if [ "${V}" == "on" ] || [ "${V}" == "off" ]; then
    continue
  fi

  if [ "${V}" == "yes" ] || [ "${V}" == "no" ]; then
    continue
  fi

  if [ "${#V}" -le 3 ]; then
    continue
  fi
  shopt -u nocasematch

  V=${V//#/.}
  V=${V//\\/.}
  V=${V//\*/.}
  V=${V//\?/.}
  find "${FOLDER}" -type f -exec sed -i '' -e "s#${V}#--#g" {} \;
done
