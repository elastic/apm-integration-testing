#!/bin/sh
set -xe

## Support to run Agents using an ApiKey
if [ -n "${ELASTIC_APM_API_KEY}" ] ; then
  curl -s -u admin:changeme -X PUT "elasticsearch:9200/_security/privilege" -H 'Content-Type: application/json' -d'
  {
    "properties": {
      "email": {
        "type": "keyword"
      }
    }
  }
  {
  "apm": {
      "write_sourcemap": {
        "actions": [ "sourcemap:write" ]
      },
      "write_event": {
        "actions": [ "event:write" ]
      },
      "read_agent_config": {
        "actions": [ "config_agent:read" ]
      }
    }
  }
  '

  apiKey=$(curl -s -u admin:changeme "elasticsearch:9200/_security/api_key" -H 'Content-Type: application/json' -d'
  {
    "name": "apm-backend",
    "role_descriptors": {
      "apm-backend": {
        "applications": [
          {
            "application": "apm",
            "privileges": ["*"],
            "resources": ["*"]
          }
        ]
      }
    }
  }
  ' | jq '(.id + ":" +.api_key)')

  # shellcheck disable=SC2039
  ELASTIC_APM_API_KEY=$(echo -n "${apiKey}" | base64)

  echo ELASTIC_APM_API_KEY="${ELASTIC_APM_API_KEY}" > /usr/share/.env-api-key
fi

## Notify to the healthcheck.
touch /tmp/ready

## Keep running the container to notify the dependent services.
tail -f /dev/null
