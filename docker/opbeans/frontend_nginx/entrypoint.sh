#!/usr/bin/env bash
echo "******************************************************************************************************************************************"
echo "* You must define ELASTIC_OPBEANS_API_SERVER to reditect all request to http://host:port/api/* (default http://localhost:3000) *"
echo "* You can define ELASTIC_APM_JS_BASE_SERVER_URL to send the APM request (default http://localhost:8200)                                         *"
echo "* You can define ELASTIC_APM_JS_BASE_SERVICE_VERSION to set the service version (default v1.0.0)                                         *"
echo "* You can define ELASTIC_APM_JS_BASE_SERVICE_NAME to set the service name (default opbeans-rum)                                         *"
echo "******************************************************************************************************************************************"

ELASTIC_OPBEANS_API_SERVER=${ELASTIC_OPBEANS_API_SERVER:-"http://localhost:3000"}
ELASTIC_APM_JS_BASE_SERVER_URL=${ELASTIC_APM_JS_BASE_SERVER_URL:-"http://localhost:8200"}
ELASTIC_APM_JS_BASE_SERVICE_NAME=${ELASTIC_APM_JS_BASE_SERVICE_NAME:-"opbeans-rum"}
ELASTIC_APM_JS_BASE_SERVICE_VERSION=${ELASTIC_APM_JS_BASE_SERVICE_VERSION:-"$RANDOM"}

echo "ELASTIC_OPBEANS_API_SERVER=${ELASTIC_OPBEANS_API_SERVER}"
echo "ELASTIC_APM_JS_BASE_SERVER_URL=${ELASTIC_APM_JS_BASE_SERVER_URL}"
echo "ELASTIC_APM_JS_BASE_SERVICE_VERSION=${ELASTIC_APM_JS_BASE_SERVICE_VERSION}"
echo "ELASTIC_APM_JS_BASE_SERVICE_NAME=${ELASTIC_APM_JS_BASE_SERVICE_NAME}"

sed "s@{{ ELASTIC_OPBEANS_API_SERVER }}@${ELASTIC_OPBEANS_API_SERVER}@g" /etc/nginx/conf.d/default.template > /etc/nginx/conf.d/default.conf
sed -e "s@{{ ELASTIC_APM_JS_BASE_SERVER_URL }}@${ELASTIC_APM_JS_BASE_SERVER_URL}@g" \
    -e "s@{{ ELASTIC_APM_JS_BASE_SERVICE_VERSION }}@${ELASTIC_APM_JS_BASE_SERVICE_VERSION}@g" \
    -e "s@{{ ELASTIC_APM_JS_BASE_SERVICE_NAME }}@${ELASTIC_APM_JS_BASE_SERVICE_NAME}@g" \
    /usr/share/nginx/html/rum-config.template > /usr/share/nginx/html/rum-config.js

exec nginx-debug -g 'daemon off;'
