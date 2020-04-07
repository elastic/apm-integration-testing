#!/usr/bin/env bash
set -e

gitUrl=$(git remote get-url origin)
commit=$(git rev-parse HEAD)

echo "Let's generate the details to help to reproduce it locally ..."
echo ""
echo ""

echo "# Let's clone the repo"
echo "git clone ${gitUrl} .apm-its"
echo "cd .apm-its"
echo "git checkout ${commit}"
echo ""
echo "# Let's run the apm-integration testing for ${NAME}"
echo "export ELASTIC_STACK_VERSION=${ELASTIC_STACK_VERSION}"
echo "export BUILD_OPTS=${BUILD_OPTS}"
echo ".ci/scripts/${NAME}.sh"
echo ""
echo "# Let's save the docker log output as files"
echo "./scripts/docker-get-logs.sh '${NAME}' || echo 'Failed to get Docker logs'"
echo "make stop-env || echo 'Failed to stop the environment'"
echo ""
echo "# Logs are now stored in the below location docker-info/${NAME}"
echo "cd docker-info/${NAME}"
echo "ls -ltrh"
