#!/usr/bin/env bash

set -ex

if [[ -z ${PYTHON_AGENT_VERSION} ]] || 
   [[ -z ${PYTHON_AGENT_VERSION_STATE} ]] ||
   [[ -z ${FLASK_SERVICE_NAME} ]] ||
   [[ -z ${FLASK_PORT} ]]; then
  echo "PYTHON_AGENT_VERSION, PYTHON_AGENT_VERSION_STATE, FLASK_SERVICE_NAME and FLASK_PORT expected."
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

docker build --pull -t ${FLASK_SERVICE_NAME} -f ./docker/python/flask/Dockerfile .

docker run -d \
  --name ${FLASK_SERVICE_NAME} \
  --network=${NETWORK} \
  -p ${FLASK_PORT}:${FLASK_PORT} \
  -e FLASK_SERVICE_NAME=${FLASK_SERVICE_NAME} \
  -e FLASK_PORT=${FLASK_PORT} \
  -e APM_SERVER_URL=${APM_SERVER_URL} \
  --rm "${FLASK_SERVICE_NAME}" \
  /bin/bash \
  -c "pip install -U ${install_cmd} && python app.py"
