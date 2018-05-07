#!/usr/bin/env bash

set -ex

if [[ -z ${RUBY_AGENT_VERSION} ]] || 
   [[ -z ${RUBY_AGENT_VERSION_STATE} ]] || 
   [[ -z ${RAILS_SERVICE_NAME} ]] ||
   [[ -z ${RAILS_PORT} ]]; then
  echo "RUBY_AGENT_VERSION, RUBY_AGENT_VERSION_STATE, RAILS_SERVICE_NAME and RAILS_PORT expected."
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


echo "RUBY_AGENT_VERSION: ${RUBY_AGENT_VERSION}, ${RUBY_AGENT_VERSION_STATE}"

docker build --pull -t ${RAILS_SERVICE_NAME} -f ./docker/ruby/rails/Dockerfile .

docker run -d \
  --name ${RAILS_SERVICE_NAME} \
  --network=${NETWORK} \
  -p ${RAILS_PORT}:${RAILS_PORT} \
  -e RAILS_SERVICE_NAME=${RAILS_SERVICE_NAME} \
  -e RAILS_PORT=${RAILS_PORT} \
  -e ELASTIC_APM_SERVICE_NAME=${RAILS_SERVICE_NAME} \
  -e ELASTIC_APM_SERVER_URL=${APM_SERVER_URL} \
  -e RUBY_AGENT_VERSION=${RUBY_AGENT_VERSION} \
  -e RUBY_AGENT_VERSION_STATE=${RUBY_AGENT_VERSION_STATE} \
  --rm "${RAILS_SERVICE_NAME}" \
  /bin/bash \
  -c "cd testapp &&\
      bundle install &&\
      rails s -b 0.0.0.0 -p ${RAILS_PORT}"
