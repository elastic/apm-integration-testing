#!/usr/bin/env bash

set -ex

if [[ -z ${PYTHON_AGENT_VERSION} ]] || 
   [[ -z ${PYTHON_AGENT_VERSION_STATE} ]] || 
   [[ -z ${DJANGO_SERVICE_NAME} ]] ||
   [[ -z ${DJANGO_PORT} ]]; then
  echo "PYTHON_AGENT_VERSION, PYTHON_AGENT_VERSION_STATE, DJANGO_SERVICE_NAME and DJANGO_PORT expected."
  exit 2
fi
if [[ -z ${APM_SERVER_URL} ]]; then
  echo "APM_SERVER_URL expected"
  exit 2
fi
if [[ -z ${NETWORK} ]]; then
  echo "NETWORK expected"
  exit 2
fi


echo "PYTHON_AGENT_VERSION: ${PYTHON_AGENT_VERSION}, ${PYTHON_AGENT_VERSION_STATE}"

if [[ ${PYTHON_AGENT_VERSION_STATE} == "release" ]]; then
  if [[ ${PYTHON_AGENT_VERSION} == "latest" ]]; then
    install_cmd="elastic-apm"
  else
    install_cmd="elastic-apm==${PYTHON_AGENT_VERSION}"
  fi
else
  install_cmd="git+https://github.com/elastic/apm-agent-python.git@${PYTHON_AGENT_VERSION}"
fi

docker build --pull -t ${DJANGO_SERVICE_NAME} -f ./docker/python/django/Dockerfile .


docker run -d \
  --name ${DJANGO_SERVICE_NAME} \
  --network=${NETWORK} \
  -p ${DJANGO_PORT}:${DJANGO_PORT} \
  -e DJANGO_SERVICE_NAME=${DJANGO_SERVICE_NAME} \
  -e DJANGO_PORT=${DJANGO_PORT} \
  -e APM_SERVER_URL=${APM_SERVER_URL} \
  --rm "${DJANGO_SERVICE_NAME}" \
  /bin/bash \
  -c "pip install -U ${install_cmd} && 
      python testapp/manage.py runserver 0.0.0.0:${DJANGO_PORT}"
