#!/usr/bin/env bash

set -ex

if [[ -z ${PYTHON_AGENT_VERSION} ]] || 
   [[ -z ${PYTHON_AGENT_VERSION_STATE} ]]; then
  echo "PYTHON_AGENT_VERSION, PYTHON_AGENT_VERSION_STATE expected."
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

if [[ ${PYTHON_AGENT_VERSION_STATE} == "release" ]]; then
  install_cmd="elastic-apm==${PYTHON_AGENT_VERSION}"
else
  install_cmd="git+https://github.com/elastic/apm-agent-python.git@${PYTHON_AGENT_VERSION}"
fi
if [[ -z ${PY_SERVER} ]]; then
  start_cmd="python app.py"
  app_name=${FLASK_APP_NAME}
  port=${FLASK_PORT}
elif [[ ${PY_SERVER} == "gunicorn" ]]; then
  app_name=${GUNICORN_APP_NAME}
  port=${GUNICORN_PORT}
  start_cmd="gunicorn -w 4 -b 0.0.0.0:${port} app:app"
fi

docker build --pull -t ${app_name} -f ./docker/python/flask/Dockerfile .


docker run -d \
  --name ${app_name} \
  --network=${NETWORK} \
  -p ${port}:${port} \
  -e FLASK_APP_NAME=${app_name} \
  -e FLASK_PORT=${port} \
  -e APM_SERVER_URL=${APM_SERVER_URL} \
  --rm "${app_name}" \
  /bin/bash \
  -c "pip install -U ${install_cmd}
     ${start_cmd}"
