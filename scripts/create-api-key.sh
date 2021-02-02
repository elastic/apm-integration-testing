#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC2034
privilege=$(curl -s -u admin:changeme -X PUT "localhost:9200/_security/privilege" -H 'Content-Type: application/json' -d'
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
')

apiKey=$(curl -s -u admin:changeme "localhost:9200/_security/api_key" -H 'Content-Type: application/json' -d'
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

echo -n "${apiKey}" | base64
