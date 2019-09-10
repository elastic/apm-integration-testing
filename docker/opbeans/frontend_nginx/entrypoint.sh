#!/usr/bin/env bash
echo "******************************************************************************************************************************************"
echo "* You must define ELASTIC_OPBEANS_API_SERVER to reditect all request to http://host:port/api/* (default http://localhost:3000) *"
echo "* You can define ELASTIC_APM_SERVER_URLS to send the APM request (default http://localhost:8200)                                         *"
echo "******************************************************************************************************************************************"

ELASTIC_OPBEANS_API_SERVER=${ELASTIC_OPBEANS_API_SERVER:-"http://localhost:3000"}
ELASTIC_APM_SERVER_URLS=${APM_SERVE:-"http://localhost:8200"}

echo "ELASTIC_OPBEANS_API_SERVER=${ELASTIC_OPBEANS_API_SERVER}"
echo "ELASTIC_APM_SERVER_URLS=${ELASTIC_APM_SERVER_URLS}"

sed "s@{{ELASTIC_OPBEANS_API_SERVER}}@${ELASTIC_OPBEANS_API_SERVER}@g" /etc/nginx/conf.d/default.template > /etc/nginx/conf.d/default.conf
sed "s@{{ELASTIC_APM_SERVER_URLS}}@${ELASTIC_APM_SERVER_URLS}@g" /usr/share/nginx/html/rum-config.template > /usr/share/nginx/html/rum-config.js

exec nginx-debug -g 'daemon off;'
