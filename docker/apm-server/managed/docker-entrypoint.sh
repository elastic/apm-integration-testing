#!/bin/bash

set -e

echo ${KIBANA_HOST}

fleet="${KIBANA_HOST}/api/fleet"
pkg_policy_name="apm-integration-testing"

# remove existing apm-integration-testing package policy
pkg_policy_id="$(curl -s -H 'kbn-xsrf: true' -H 'Content-Type: application/json' "${fleet}/package_policies?kuery=ingest-package-policies.name:${pkg_policy_name}" | jq '.items[0].id')"
if [ -n "$pkg_policy_id" ];then
  pkg_policy_ids()
{
  cat <<EOF
  {
  "packagePolicyIds":[${pkg_policy_id}]
  }
EOF
}
  success="$(curl -s -H 'kbn-xsrf: true' -H 'Content-Type: application/json' "${fleet}/package_policies/delete" -d "$(pkg_policy_ids)" | jq '.[0].success')"
  if [ "$success" = false ]; then
    echo "deleting existing package policy failed"
    exit -1
  fi
fi

# fetch the default agent policy
agent_policy_id="$(curl -s "${fleet}/agent_policies?kuery=ingest-agent-policies.is_default:true" | jq '.items[0] .id')"
if [ -z $agent_policy_id ]; then
    echo "no default agent policy found"
    exit -2
fi

# create apm-integration-testing package policy
# and aadd it to the default agent policy
pkg_policy_data()
{
  cat <<EOF
{
  "name":"apm-integration-testing",
  "description":"apm integration testing",
  "namespace":"default",
  "policy_id":${agent_policy_id},
  "enabled":true,
  "output_id":"",
  "inputs":[
    {"type":"apm",
    "enabled":true,
    "streams":[],
    "vars":{
      "enable_rum":{"type":"bool","value":true}
      }
    }
  ],
  "package":{
    "name":"apm",
    "title":"Elastic APM",
    "version":"0.1.0-dev.1"
  }
}    
EOF
}
created_at="$(curl -s -H 'kbn-xsrf: true' -H 'Content-Type: application/json' "${fleet}/package_policies" -d "$(pkg_policy_data)" | jq '.item.created_at')"
if [ -z "$created_at" ]; then
    echo "package policy not created"
    exit -3
fi
echo "apm-integration-testing policy successfully setup"

touch anything
tail -F anything